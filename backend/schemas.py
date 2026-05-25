"""Pydantic schemas — the contract between frontend, API, and grader.

The Criterion / Rubric schemas implement the design principles from
Vanhoyweghen et al. (2026): fine-grained criteria with explicit alternatives
and explicit do-not-deduct conditions, so the LLM has no room to invent
its own interpretation.
"""
from __future__ import annotations

from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# --- Rubric ----------------------------------------------------------------
class Criterion(BaseModel):
    name: str
    points: float = Field(..., ge=0)
    conditions: str = Field(..., description="What must be present in the answer to earn these points.")
    accept_alternatives: str = Field("", description="Equivalent forms to also accept.")
    do_not_deduct_for: str = Field("", description="Surface issues to ignore.")


class RubricCreate(BaseModel):
    exam_id: int
    title: str
    question_text: str
    max_marks: float
    course_instructions: str
    criteria: list[Criterion]


class RubricOut(BaseModel):
    id: int
    exam_id: int
    version: str
    title: str
    question_text: str
    max_marks: float
    course_instructions: str
    criteria: list[Criterion]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Exam ------------------------------------------------------------------
class ExamCreate(BaseModel):
    title: str


class ExamOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Paper / Crop ----------------------------------------------------------
class CropOut(BaseModel):
    id: int
    paper_id: int
    question_id: str
    rubric_id: int
    image_path: str
    anonymized_path: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Grading ---------------------------------------------------------------
class PerCriterionScore(BaseModel):
    name: str
    awarded: float
    max: float
    reasoning: str


class GradingOut(BaseModel):
    id: int
    crop_id: int
    pass_num: int
    score: float
    max_score: float
    per_criterion: list[PerCriterionScore]
    justification: str
    transcript: str
    flags: list[str]
    critic_passed: bool
    critic_feedback: str | None
    model_version: str
    prompt_version: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AggregateOut(BaseModel):
    crop_id: int
    median: float
    max_score: float
    min_score: float
    std_dev: float
    n_passes: int
    model_config = ConfigDict(from_attributes=True)


# --- Review queue item -----------------------------------------------------
class ReviewQueueItem(BaseModel):
    """One row in the TA review dashboard."""
    crop_id: int
    paper_id: int
    student_anon_id: str
    question_id: str
    rubric_id: int
    rubric_title: str
    image_path: str
    aggregate: AggregateOut
    gradings: list[GradingOut]
    plagiarism_flagged: bool = False
    reviewed: bool = False
    final_score: float | None = None


# --- Review action ---------------------------------------------------------
class ReviewCreate(BaseModel):
    crop_id: int
    action: str  # 'approve' | 'override' | 'flag'
    final_score: float
    notes: str = ""
    reviewer_id: int | None = None


class ReviewOut(BaseModel):
    id: int
    crop_id: int
    action: str
    ai_score: float
    final_score: float
    notes: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Plagiarism ------------------------------------------------------------
class PlagiarismPair(BaseModel):
    crop_a_id: int
    crop_b_id: int
    similarity: float
    flagged_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Audit log -------------------------------------------------------------
class AuditEntry(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    before: dict | None = None
    after: dict | None = None
    rubric_version: str | None = None
    prompt_version: str | None = None
    model_version: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
