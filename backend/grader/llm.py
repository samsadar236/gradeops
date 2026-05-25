"""Provider-abstracted LLM factory.

Returns a langchain ChatModel for whichever provider is configured. Both
the agentic grader nodes and the OCR transcriber import from here, so
flipping `LLM_PROVIDER` in .env swaps the entire LLM backend in one place.

Supported providers:
  - 'google'    → Gemini via langchain-google-genai (FREE tier; recommended)
  - 'anthropic' → Claude via langchain-anthropic   (paid)

Key resolution is belt-and-braces:
  - First consults `settings.<provider>_api_key` (loaded by pydantic-settings
    from .env)
  - Falls back directly to os.environ, so a manually-set shell variable
    works even if pydantic-settings missed the file
"""
from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel

from ..config import settings


_llm: BaseChatModel | None = None


def _resolve_key(field_value: str, env_var: str) -> str:
    """Settings field first, then os.environ. Returns '' if neither has it."""
    if field_value:
        return field_value
    return os.environ.get(env_var, "") or ""


def get_llm() -> BaseChatModel:
    """Construct (and cache) the chat model for the configured provider."""
    global _llm
    if _llm is not None:
        return _llm

    provider = (settings.llm_provider or "google").lower()

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = _resolve_key(settings.google_api_key, "GOOGLE_API_KEY")
        if not key:
            raise RuntimeError(
                "LLM_PROVIDER=google but GOOGLE_API_KEY is empty.\n"
                "Get a free key at https://aistudio.google.com/app/apikey "
                "and set GOOGLE_API_KEY in your .env file (or shell env var).\n"
                "Hit GET /debug/env to see what the backend is loading."
            )
        _llm = ChatGoogleGenerativeAI(
            model=settings.grader_model_google,
            google_api_key=key,
            max_output_tokens=2048,
            timeout=120,
            # Free tier is 15 RPM — we use 5 parallel passes per crop.
            max_retries=3,
        )
        return _llm

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        key = _resolve_key(settings.anthropic_api_key, "ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty. "
                "Set it in .env or switch LLM_PROVIDER=google for the free tier."
            )
        _llm = ChatAnthropic(
            model=settings.grader_model_anthropic,
            max_tokens=2000,
            api_key=key,
            timeout=120,
        )
        return _llm

    raise RuntimeError(
        f"Unknown LLM_PROVIDER: {provider!r}. Use 'google' or 'anthropic'."
    )


def reset_llm() -> None:
    """Clear the cached LLM instance (used by tests when settings change)."""
    global _llm
    _llm = None
