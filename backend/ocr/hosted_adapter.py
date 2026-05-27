"""Hosted vision-API OCR adapter — passes through the shared LLM factory.

Uses whichever LLM is configured in settings.llm_provider (Gemini by
default — free tier — or Claude). Runs on any laptop with no GPU.
Throttled through the shared rate limiter so OCR calls cannot blow past
the per-minute quota when followed by grading calls.
"""
from __future__ import annotations

import base64
from pathlib import Path

from langchain_core.messages import HumanMessage

from ..grader.llm import get_llm
from ..grader.rate_limit import wait_turn


TRANSCRIBE_PROMPT = (
    "You are an OCR system specialized in handwritten student exam answers — "
    "math equations, derivations, prose, diagrams.\n\n"
    "Transcribe the handwritten content in the image LITERALLY. Do not correct "
    "mistakes. Do not interpret intent. Preserve line breaks. Use LaTeX for "
    "math expressions. Mark illegible segments as [illegible].\n\n"
    "Output the transcript only — no preamble, no commentary, no markdown fences."
)


def transcribe(image_path: str) -> str:
    """Transcribe handwritten content via the configured chat model."""
    wait_turn()
    img_bytes = Path(image_path).read_bytes()
    img_b64 = base64.b64encode(img_bytes).decode("ascii")
    suffix = Path(image_path).suffix.lower().lstrip(".")
    media_type = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix or 'jpeg'}"
    data_url = f"data:{media_type};base64,{img_b64}"

    llm = get_llm()
    msg = HumanMessage(content=[
        {"type": "image_url", "image_url": {"url": data_url}},
        {"type": "text", "text": TRANSCRIBE_PROMPT},
    ])
    response = llm.invoke([msg])
    content = response.content
    return content if isinstance(content, str) else str(content)
