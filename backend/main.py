"""FastAPI application: the API surface for the React frontend.

Routes:
  /users        bootstrap instructor + TA users for RBAC
  /exams        CRUD exams
  /rubrics      CRUD rubrics (immutable; updates create new versions)
  /papers       upload PDFs, kick off the full pipeline
  /crops        list crops + image bytes
  /review       review queue (sorted by std-dev DESC) + decision endpoint
  /audit        immutable audit log
  /plagiarism   pair list above threshold
  /stats        override-rate dashboard metrics
  /debug/env    diagnostic — what env vars actually loaded
  /health       liveness probe

Pipeline (kicked off on POST /papers/upload):
  PDF split → answer-region crop → anonymize →
    OCR transcribe → agentic grader 5x in parallel →
    aggregate → plagiarism worker over this exam
"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import settings, _ENV_FILE
from .db import (
    get_db, init_db, User, Exam, Rubric, Paper, Crop,
    Grading, GradingAggregate, Review, PlagiarismFlag, AuditLog,
)
from . import schemas
from .audit import log_event
from .ingestion import split_pdf_to_pages, detect_answer_regions, crop_region, anonymize_crop
from .ocr import transcribe as ocr_transcribe
from .grader import grade_multi_pass, aggregate_scores
from .plagiarism import find_similar_pairs


app = FastAPI(title="GRADEOPS", version="0.1.0")

# Open CORS for the React dev server (Vite defaults to 5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()
    # Seed two default users so RBAC has something to point at.
    from .db import SessionLocal
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all([
                User(email="instructor@gradeops.local", name="Instructor", role="instructor"),
                User(email="ta@gradeops.local", name="TA", role="ta"),
            ])
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health + diagnostics
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "model": settings.grader_model,
        "ocr_backend": settings.ocr_backend,
    }


@app.get("/debug/env")
def debug_env():
    """Diagnostic — shows exactly what the backend loaded.
    Remove or restrict by role in production."""
    def safe(val: str) -> dict:
        return {"len": len(val or ""), "prefix": ((val or "")[:6] + "...") if val else "(empty)"}

    return {
        "cwd": os.getcwd(),
        "project_root": str(_ENV_FILE.parent),
        "env_file_path": str(_ENV_FILE),
        "env_file_exists": _ENV_FILE.exists(),
        "settings_llm_provider": settings.llm_provider,
        "settings_google_api_key": safe(settings.google_api_key),
        "settings_anthropic_api_key": safe(settings.anthropic_api_key),
        "os_environ_GOOGLE_API_KEY": safe(os.environ.get("GOOGLE_API_KEY", "")),
        "os_environ_ANTHROPIC_API_KEY": safe(os.environ.get("ANTHROPIC_API_KEY", "")),
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role}
            for u in db.query(User).all()]


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------
@app.post("/exams", response_model=schemas.ExamOut)
def create_exam(payload: schemas.ExamCreate, db: Session = Depends(get_db)):
    e = Exam(title=payload.title)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@app.get("/exams", response_model=list[schemas.ExamOut])
def list_exams(db: Session = Depends(get_db)):
    return db.query(Exam).order_by(Exam.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Rubrics (immutable, versioned per exam)
# ---------------------------------------------------------------------------
@app.post("/rubrics", response_model=schemas.RubricOut)
def create_rubric(payload: schemas.RubricCreate, db: Session = Depends(get_db)):
    exam = db.get(Exam, payload.exam_id)
    if exam is None:
        raise HTTPException(404, "exam not found")

    existing = db.query(Rubric).filter(Rubric.exam_id == exam.id).count()
    version = f"v{existing + 1}"

    r = Rubric(
        exam_id=exam.id,
        version=version,
        title=payload.title,
        question_text=payload.question_text,
        max_marks=payload.max_marks,
        course_instructions=payload.course_instructions,
        criteria=[c.model_dump() for c in payload.criteria],
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    log_event(db, "rubric", r.id, "create",
              after={"version": version, "title": r.title},
              rubric_version=version)
    db.commit()
    return _rubric_to_out(r)


@app.get("/rubrics", response_model=list[schemas.RubricOut])
def list_rubrics(exam_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Rubric)
    if exam_id is not None:
        q = q.filter(Rubric.exam_id == exam_id)
    return [_rubric_to_out(r) for r in q.order_by(Rubric.created_at.desc()).all()]


@app.get("/rubrics/{rubric_id}", response_model=schemas.RubricOut)
def get_rubric(rubric_id: int, db: Session = Depends(get_db)):
    r = db.get(Rubric, rubric_id)
    if r is None:
        raise HTTPException(404, "rubric not found")
    return _rubric_to_out(r)


def _rubric_to_out(r: Rubric) -> schemas.RubricOut:
    return schemas.RubricOut(
        id=r.id, exam_id=r.exam_id, version=r.version, title=r.title,
        question_text=r.question_text, max_marks=r.max_marks,
        course_instructions=r.course_instructions,
        criteria=[schemas.Criterion(**c) for c in (r.criteria or [])],
        created_at=r.created_at,
    )


# ---------------------------------------------------------------------------
# Papers — upload + run pipeline
# ---------------------------------------------------------------------------
@app.post("/papers/upload")
def upload_papers(
    exam_id: int = Form(...),
    rubric_id: int = Form(...),
    file: UploadFile = File(...),
    student_anon_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Upload one PDF (or one image acting as a single-page PDF).

    Runs the full pipeline synchronously and returns the resulting crop ids.
    In production this should move to a background task; for the demo,
    synchronous keeps the trace easy to follow.
    """
    exam = db.get(Exam, exam_id)
    rubric = db.get(Rubric, rubric_id)
    if exam is None or rubric is None:
        raise HTTPException(404, "exam or rubric not found")

    storage = settings.storage_path
    anon_id = student_anon_id or f"STU-{uuid.uuid4().hex[:6].upper()}"

    # 1. Save uploaded file
    suffix = Path(file.filename or "upload.pdf").suffix.lower() or ".pdf"
    upload_path = storage / "pdfs" / f"{anon_id}_{uuid.uuid4().hex[:8]}{suffix}"
    with upload_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    paper = Paper(exam_id=exam.id, student_anon_id=anon_id, source_pdf_path=str(upload_path))
    db.add(paper)
    db.commit()
    db.refresh(paper)

    # 2. Split into pages
    if suffix == ".pdf":
        page_paths = split_pdf_to_pages(str(upload_path), str(storage / "pages"))
    else:
        page_paths = [str(upload_path)]

    crop_records: list[Crop] = []

    for page_path in page_paths:
        # 3. Detect answer regions (with whole-page fallback)
        regions = detect_answer_regions(page_path)
        for region in regions:
            # 4. Crop + 5. Anonymize
            raw_crop = crop_region(page_path, region["bbox"], str(storage / "crops"))
            anon = anonymize_crop(raw_crop, str(storage / "crops"))

            crop = Crop(
                paper_id=paper.id,
                question_id=region["question_id"],
                rubric_id=rubric.id,
                image_path=raw_crop,
                anonymized_path=anon,
                bbox=region["bbox"],
            )
            db.add(crop)
            db.commit()
            db.refresh(crop)

            # 6. OCR transcribe (canonical transcript for plagiarism + search)
            try:
                transcript = ocr_transcribe(anon)
            except Exception as e:
                transcript = f"[OCR error: {e}]"

            # 7. Run the agentic grader NUM_PASSES times in parallel
            passes = grade_multi_pass(
                anon,
                question=rubric.question_text,
                max_marks=rubric.max_marks,
                criteria=rubric.criteria,
            )

            # 8. Persist gradings + aggregate
            for i, p in enumerate(passes, 1):
                g = Grading(
                    crop_id=crop.id,
                    rubric_id=rubric.id,
                    pass_num=i,
                    score=p["score"],
                    max_score=p["max_score"],
                    per_criterion=p["per_criterion"],
                    justification=p["justification"],
                    transcript=transcript,
                    flags=p["flags"],
                    critic_passed=p["critic_passed"],
                    critic_feedback=p["critic_feedback"],
                    model_version=settings.grader_model,
                    prompt_version=settings.prompt_version,
                )
                db.add(g)

            agg = aggregate_scores(passes)
            db.add(GradingAggregate(
                crop_id=crop.id,
                median=agg["median"],
                max_score=agg["max_score"],
                min_score=agg["min_score"],
                std_dev=agg["std_dev"],
                n_passes=agg["n_passes"],
            ))
            log_event(db, "grading", crop.id, "create",
                      after={"median": agg["median"], "std_dev": agg["std_dev"]},
                      rubric_version=rubric.version)
            db.commit()
            crop_records.append(crop)

    # 9. Plagiarism worker across all crops in this exam
    try:
        _refresh_plagiarism(db, exam_id=exam.id)
    except Exception as e:
        print(f"[plagiarism] failed: {e}")

    return {
        "paper_id": paper.id,
        "student_anon_id": anon_id,
        "crop_ids": [c.id for c in crop_records],
    }


def _refresh_plagiarism(db: Session, exam_id: int) -> None:
    """Recompute similarity pairs across all crops in this exam."""
    rows = (
        db.query(Crop.id, Grading.transcript)
        .join(Grading, Grading.crop_id == Crop.id)
        .join(Paper, Paper.id == Crop.paper_id)
        .filter(Paper.exam_id == exam_id, Grading.pass_num == 1)
        .all()
    )
    transcripts = [(cid, t) for cid, t in rows if t]
    if len(transcripts) < 2:
        return

    pairs = find_similar_pairs(transcripts)
    for a, b, s in pairs:
        existing = db.query(PlagiarismFlag).filter_by(crop_a_id=a, crop_b_id=b).first()
        if existing:
            existing.similarity = s
        else:
            db.add(PlagiarismFlag(crop_a_id=a, crop_b_id=b, similarity=s))
    db.commit()

@app.delete("/papers/{paper_id}", status_code=204)
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    # 1. Find the paper
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "paper not found")

    # 2. Delete the physical files to save storage
    storage = settings.storage_path
    for sub in ("pages", "crops"):
        dir_path = storage / sub / str(paper_id)
        if dir_path.is_dir():
            shutil.rmtree(dir_path, ignore_errors=True)
            
    # Also delete the original PDF using the saved path
    if paper.source_pdf_path:
        pdf_path = Path(paper.source_pdf_path)
        if pdf_path.is_file():
            pdf_path.unlink(missing_ok=True)

    # 3. Delete from the database
    # (Relies on ondelete="CASCADE" in your DB models)
    db.delete(paper)
    db.commit()
    
    return


# ---------------------------------------------------------------------------
# Crops + images
# ---------------------------------------------------------------------------
@app.get("/crops/{crop_id}/image")
def get_crop_image(crop_id: int, db: Session = Depends(get_db)):
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(404, "crop not found")
    path = crop.anonymized_path
    if not Path(path).exists():
        raise HTTPException(404, "image file missing")
    return FileResponse(path)


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------
@app.get("/review/queue", response_model=list[schemas.ReviewQueueItem])
def review_queue(
    exam_id: int | None = None,
    only_pending: bool = True,
    db: Session = Depends(get_db),
):
    """Return crops sorted by std-dev DESC (highest uncertainty first)."""
    q = (
        db.query(Crop, GradingAggregate, Paper, Rubric)
        .join(GradingAggregate, GradingAggregate.crop_id == Crop.id)
        .join(Paper, Paper.id == Crop.paper_id)
        .join(Rubric, Rubric.id == Crop.rubric_id)
    )
    if exam_id is not None:
        q = q.filter(Paper.exam_id == exam_id)

    items: list[schemas.ReviewQueueItem] = []
    for crop, agg, paper, rubric in q.order_by(GradingAggregate.std_dev.desc()).all():
        latest_review = (
            db.query(Review)
            .filter(Review.crop_id == crop.id)
            .order_by(Review.created_at.desc())
            .first()
        )
        if only_pending and latest_review is not None:
            continue

        gradings = (
            db.query(Grading)
            .filter(Grading.crop_id == crop.id)
            .order_by(Grading.pass_num.asc())
            .all()
        )

        flagged = (
            db.query(PlagiarismFlag)
            .filter((PlagiarismFlag.crop_a_id == crop.id) | (PlagiarismFlag.crop_b_id == crop.id))
            .first()
            is not None
        )

        items.append(schemas.ReviewQueueItem(
            crop_id=crop.id,
            paper_id=paper.id,
            student_anon_id=paper.student_anon_id,
            question_id=crop.question_id,
            rubric_id=rubric.id,
            rubric_title=rubric.title,
            image_path=f"/crops/{crop.id}/image",
            aggregate=schemas.AggregateOut(
                crop_id=crop.id,
                median=agg.median,
                max_score=agg.max_score,
                min_score=agg.min_score,
                std_dev=agg.std_dev,
                n_passes=agg.n_passes,
            ),
            gradings=[schemas.GradingOut.model_validate(g) for g in gradings],
            plagiarism_flagged=flagged,
            reviewed=latest_review is not None,
            final_score=latest_review.final_score if latest_review else None,
        ))
    return items


@app.post("/reviews", response_model=schemas.ReviewOut)
def submit_review(payload: schemas.ReviewCreate, db: Session = Depends(get_db)):
    crop = db.get(Crop, payload.crop_id)
    if crop is None:
        raise HTTPException(404, "crop not found")

    agg = db.get(GradingAggregate, payload.crop_id)
    ai_score = agg.median if agg else 0.0
    rubric = db.get(Rubric, crop.rubric_id)

    r = Review(
        crop_id=payload.crop_id,
        reviewer_id=payload.reviewer_id,
        action=payload.action,
        ai_score=ai_score,
        final_score=payload.final_score,
        notes=payload.notes,
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    log_event(
        db, "review", r.id, payload.action,
        actor_id=payload.reviewer_id,
        before={"ai_score": ai_score},
        after={"final_score": payload.final_score, "notes": payload.notes},
        rubric_version=rubric.version if rubric else None,
    )
    db.commit()
    return r


# ---------------------------------------------------------------------------
# Audit + plagiarism views
# ---------------------------------------------------------------------------
@app.get("/audit", response_model=list[schemas.AuditEntry])
def list_audit(limit: int = 200, db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


@app.get("/plagiarism", response_model=list[schemas.PlagiarismPair])
def list_plagiarism(db: Session = Depends(get_db)):
    return db.query(PlagiarismFlag).order_by(PlagiarismFlag.similarity.desc()).all()


# ---------------------------------------------------------------------------
# Stats — surfaces the metrics dashboard
# ---------------------------------------------------------------------------
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_crops = db.query(Crop).count()
    total_reviewed = db.query(Review).count()
    overrides = db.query(Review).filter(Review.action == "override").count()
    flags = db.query(Review).filter(Review.action == "flag").count()
    mean_std = db.query(func.avg(GradingAggregate.std_dev)).scalar() or 0.0

    override_rows = db.query(Review).filter(Review.action == "override").all()
    deltas = [abs(r.final_score - r.ai_score) for r in override_rows]
    mean_delta = sum(deltas) / len(deltas) if deltas else 0.0

    return {
        "total_crops": total_crops,
        "total_reviewed": total_reviewed,
        "override_rate": overrides / total_reviewed if total_reviewed else 0.0,
        "flag_rate": flags / total_reviewed if total_reviewed else 0.0,
        "mean_std_dev": float(mean_std),
        "mean_override_delta": float(mean_delta),
        "plagiarism_pairs": db.query(PlagiarismFlag).count(),
    }

# ---------------------------------------------------------------------------
# Serve the built React frontend (production only)
# ---------------------------------------------------------------------------
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    # /assets/* serves built JS/CSS bundles
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="assets",
    )

    # Everything else falls back to index.html (SPA routing)
    @app.get("/{full_path:path}")
    def _spa_fallback(full_path: str):
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")