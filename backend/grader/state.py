"""Shared state that flows through the Langgraph nodes."""
from __future__ import annotations

from typing import TypedDict, Optional


class GradingState(TypedDict, total=False):
    # Inputs (set at graph entry)
    image_b64: str
    media_type: str
    question: str
    max_marks: float
    criteria: list[dict]

    # Set by Extractor
    transcript: str
    claims: list[dict]
    global_notes: str

    # Set by Scorer (may be overwritten on retry)
    per_criterion: list[dict]
    score: float
    max_score: float

    # Set by Justifier
    justification: str
    flags: list[str]

    # Set by Critic
    critic_passed: bool
    critic_feedback: str

    # Bookkeeping
    retry_count: int
    errors: list[str]
