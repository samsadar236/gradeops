"""Process-wide rate limiter for all LLM calls.

Every call to the Gemini/Claude API — from the agentic grader nodes AND
from the OCR transcriber — passes through `wait_turn()`. We enforce a
minimum gap between calls (default 4.5s, configurable via .env), which
keeps us comfortably under the Gemini free-tier 15 RPM cap even when
several uploads land back-to-back.

This is deliberately a hard, global throttle rather than per-thread:
running 5 parallel grading passes would otherwise blow the per-minute
budget within a second.
"""
from __future__ import annotations

import threading
import time

from ..config import settings


_lock = threading.Lock()
_last_call_ts: float = 0.0


def wait_turn() -> None:
    """Block until the configured minimum gap has elapsed since the last call."""
    global _last_call_ts
    gap = float(settings.llm_min_gap_seconds or 0.0)
    if gap <= 0:
        return
    with _lock:
        elapsed = time.monotonic() - _last_call_ts
        if elapsed < gap:
            time.sleep(gap - elapsed)
        _last_call_ts = time.monotonic()
