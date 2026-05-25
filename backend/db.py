"""SQLAlchemy ORM models matching the architecture diagram.

Tables:
  users              instructor / TA accounts (simple RBAC)
  exams              one row per exam instance
  rubrics            versioned per exam (immutable; updates create new rows)
  papers             one row per uploaded student PDF
  crops              one row per cropped answer region
  gradings           one row per grading pass (5 per crop)
  grading_aggregates median / max / std-dev per crop
  reviews            TA decisions (approve / override / flag)
  plagiarism_flags   pairs of crops above similarity threshold
  audit_log          immutable decision trail with model + prompt + rubric versions
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, JSON, Text, Boolean, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from .config import settings


# Engine + session ------------------------------------------------------------
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db() -> Session:
    """FastAPI dependency that yields a database session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Idempotent — safe to call on every boot."""
    Base.metadata.create_all(bind=engine)


# Tables ---------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'instructor' | 'ta'
    created_at = Column(DateTime, default=datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rubrics = relationship("Rubric", back_populates="exam", cascade="all, delete-orphan")
    papers = relationship("Paper", back_populates="exam", cascade="all, delete-orphan")


class Rubric(Base):
    __tablename__ = "rubrics"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    version = Column(String, nullable=False)        # e.g. 'v1', 'v2'
    title = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    max_marks = Column(Float, nullable=False)
    course_instructions = Column(Text, nullable=False)
    criteria = Column(JSON, nullable=False)         # list of dicts; see schemas.py
    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="rubrics")


class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_anon_id = Column(String, nullable=False)  # e.g. 'STU-0001'; never the real ID
    source_pdf_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="papers")
    crops = relationship("Crop", back_populates="paper", cascade="all, delete-orphan")


class Crop(Base):
    __tablename__ = "crops"
    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    question_id = Column(String, nullable=False)        # e.g. 'Q1', 'Q2a'
    rubric_id = Column(Integer, ForeignKey("rubrics.id"), nullable=False)
    image_path = Column(String, nullable=False)         # raw crop
    anonymized_path = Column(String, nullable=False)    # post-anonymization
    bbox = Column(JSON, nullable=True)                  # {x,y,w,h} on source page
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="crops")
    gradings = relationship("Grading", back_populates="crop", cascade="all, delete-orphan")


class Grading(Base):
    """One row per LLM grading pass. NUM_PASSES rows expected per crop."""
    __tablename__ = "gradings"
    id = Column(Integer, primary_key=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    rubric_id = Column(Integer, ForeignKey("rubrics.id"), nullable=False)
    pass_num = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    per_criterion = Column(JSON, nullable=False)        # list[{name, awarded, max, reasoning}]
    justification = Column(Text, nullable=False)
    transcript = Column(Text, nullable=False)
    flags = Column(JSON, nullable=False, default=list)
    critic_passed = Column(Boolean, nullable=False, default=True)
    critic_feedback = Column(Text, nullable=True)
    model_version = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    crop = relationship("Crop", back_populates="gradings")


class GradingAggregate(Base):
    """Aggregated scores across passes; one row per crop."""
    __tablename__ = "grading_aggregates"
    crop_id = Column(Integer, ForeignKey("crops.id"), primary_key=True)
    median = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    min_score = Column(Float, nullable=False)
    std_dev = Column(Float, nullable=False)
    n_passes = Column(Integer, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)             # approve | override | flag
    ai_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PlagiarismFlag(Base):
    __tablename__ = "plagiarism_flags"
    id = Column(Integer, primary_key=True)
    crop_a_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    crop_b_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    similarity = Column(Float, nullable=False)
    flagged_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("crop_a_id", "crop_b_id", name="uniq_pair"),)


class AuditLog(Base):
    """Immutable trail of every state change. Append-only."""
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String, nullable=False)        # 'grading', 'review', etc
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    rubric_version = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
