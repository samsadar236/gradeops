"""The four agentic nodes wired together by graph.py.

Architecture: Extractor sees the image, Scorer sees only the extracted claims.
This separation is the structural defense against the LLM "fixing" or
hallucinating intermediate steps that aren't on the page.

LLM calls go through `backend.grader.llm.get_llm()`, which returns
Gemini or Claude depending on settings.llm_provider. The node code does
not know or care which provider is in use.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import settings
from . import prompts
from .llm import get_llm
from .rate_limit import wait_turn
from .state import GradingState


# LLM is obtained from .llm.get_llm() (provider-agnostic factory).


# ---------------------------------------------------------------------------
# JSON helpers — every node returns strict JSON, so a robust parser earns
# its keep when the model occasionally wraps in fences.
# ---------------------------------------------------------------------------
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_json(raw: str) -> dict | None:
    if not raw:
        return None
    cleaned = _FENCE_RE.sub("", raw.strip()).strip()
    # If the model added prose around the JSON, try to grab the outermost {...}
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


def _invoke_text(system: str, user_content: list[dict] | str) -> str:
    """Call the LLM with a text-only or multimodal user message."""
    wait_turn()
    llm = get_llm()
    if isinstance(user_content, str):
        msgs = [SystemMessage(content=system), HumanMessage(content=user_content)]
    else:
        msgs = [SystemMessage(content=system), HumanMessage(content=user_content)]
    response = llm.invoke(msgs)
    return response.content if isinstance(response.content, str) else str(response.content)


# ===========================================================================
# Node 1: Extractor — sees the IMAGE, produces transcript + claims
# ===========================================================================
def extractor_node(state: GradingState) -> dict:
    user = prompts.EXTRACTOR_USER.format(question=state["question"])
    content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{state.get('media_type', 'image/jpeg')};base64,{state['image_b64']}"},
        },
        {"type": "text", "text": user},
    ]
    raw = _invoke_text(prompts.EXTRACTOR_SYSTEM, content)
    parsed = parse_json(raw) or {}
    return {
        "transcript": parsed.get("transcript", ""),
        "claims": parsed.get("claims", []) or [],
        "global_notes": parsed.get("global_notes", ""),
    }


# ===========================================================================
# Node 2: Scorer — sees ONLY the extracted claims, not the image
# ===========================================================================
def scorer_node(state: GradingState) -> dict:
    user = prompts.SCORER_USER.format(
        question=state["question"],
        max_marks=state["max_marks"],
        criteria_block=prompts.format_criteria(state["criteria"]),
        claims_block=prompts.format_claims(state.get("claims", [])),
        critic_feedback=state.get("critic_feedback") or "(none — this is the first attempt)",
    )
    raw = _invoke_text(prompts.SCORER_SYSTEM, user)
    parsed = parse_json(raw) or {}
    per_criterion = parsed.get("per_criterion", []) or []
    # Defensive: clamp awarded values inside [0, max]
    for pc in per_criterion:
        try:
            pc["awarded"] = max(0.0, min(float(pc.get("awarded", 0)), float(pc.get("max", 0))))
            pc["max"] = float(pc.get("max", 0))
        except (TypeError, ValueError):
            pc["awarded"] = 0.0
    total = sum(pc.get("awarded", 0) for pc in per_criterion)
    return {
        "per_criterion": per_criterion,
        "score": total,
        "max_score": float(parsed.get("max_score") or state["max_marks"]),
    }


# ===========================================================================
# Node 3: Justifier — writes the natural-language explanation for TAs
# ===========================================================================
def justifier_node(state: GradingState) -> dict:
    user = prompts.JUSTIFIER_USER.format(
        question=state["question"],
        claims_block=prompts.format_claims(state.get("claims", [])),
        scoring_block=prompts.format_scoring(state.get("per_criterion", [])),
    )
    raw = _invoke_text(prompts.JUSTIFIER_SYSTEM, user)
    parsed = parse_json(raw) or {}
    return {
        "justification": parsed.get("justification", "(no justification generated)"),
        "flags": parsed.get("flags", []) or [],
    }


# ===========================================================================
# Node 4: Critic — audits whether awarded points are claim-supported
# ===========================================================================
def critic_node(state: GradingState) -> dict:
    user = prompts.CRITIC_USER.format(
        question=state["question"],
        claims_block=prompts.format_claims(state.get("claims", [])),
        scoring_block=prompts.format_scoring(state.get("per_criterion", [])),
        justification=state.get("justification", ""),
    )
    raw = _invoke_text(prompts.CRITIC_SYSTEM, user)
    parsed = parse_json(raw) or {}
    passed = bool(parsed.get("passed", True))
    feedback = parsed.get("feedback", "") if not passed else ""
    return {
        "critic_passed": passed,
        "critic_feedback": feedback,
        "retry_count": state.get("retry_count", 0) + (0 if passed else 1),
    }


# ===========================================================================
# Conditional router — decides whether to retry the Scorer
# ===========================================================================
def critic_router(state: GradingState) -> str:
    """Return the name of the next node to run, or '__end__' to finish."""
    from langgraph.graph import END

    if state.get("critic_passed", True):
        return END
    if state.get("retry_count", 0) > settings.grader_critic_retry:
        # Bail out after configured retries so we never loop forever
        return END
    return "scorer"
