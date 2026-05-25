"""Command-line walkthrough of the full grading pipeline.

Usage:
    python scripts/run_demo.py path/to/answer.jpg
    python scripts/run_demo.py path/to/exam.pdf

Prints a step-by-step trace of every phase: ingest → OCR → agentic grade
→ aggregate. The trace is useful for showing the system working without
the UI in the loop.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.ingestion import (
    split_pdf_to_pages, detect_answer_regions, crop_region, anonymize_crop,
)
from backend.ocr import transcribe as ocr_transcribe
from backend.grader import grade_multi_pass, aggregate_scores


SAMPLE_RUBRIC = {
    "question_text": "Solve for x and show all steps:\n2x + 5 = 15",
    "max_marks": 10,
    "criteria": [
        {"name": "Isolate the variable term", "points": 5,
         "conditions": "Student writes 2x = 10.",
         "accept_alternatives": "Equivalent rearrangements arriving at 2x = 10.",
         "do_not_deduct_for": "Minor notation differences."},
        {"name": "Solve for x", "points": 5,
         "conditions": "Student writes x = 5.",
         "accept_alternatives": "Equivalent forms.",
         "do_not_deduct_for": "Minor notation differences."},
    ],
}


def banner(text: str) -> None:
    line = "─" * 70
    print(f"\n{line}\n {text}\n{line}")


def run(image_or_pdf: Path) -> None:
    storage = settings.storage_path
    banner(f"GradeOps demo · model={settings.grader_model} · OCR={settings.ocr_backend}")
    print(f"input: {image_or_pdf}")

    banner("Step 1 · Ingest")
    if image_or_pdf.suffix.lower() == ".pdf":
        pages = split_pdf_to_pages(str(image_or_pdf), str(storage / "pages"))
        print(f"  split into {len(pages)} page(s)")
    else:
        pages = [str(image_or_pdf)]
        print("  single image — no PDF split needed")

    all_crops = []
    for p in pages:
        regions = detect_answer_regions(p)
        print(f"  {Path(p).name}: detected {len(regions)} answer region(s)")
        for r in regions:
            raw = crop_region(p, r["bbox"], str(storage / "crops"))
            anon = anonymize_crop(raw, str(storage / "crops"))
            all_crops.append(anon)
            print(f"    cropped → {Path(anon).name}")

    banner("Step 2 · OCR")
    for c in all_crops:
        try:
            t = ocr_transcribe(c)
        except Exception as e:
            t = f"[OCR failed: {e}]"
        print(f"  {Path(c).name}:")
        for line in t.splitlines()[:8]:
            print(f"    | {line}")
        if len(t.splitlines()) > 8:
            print(f"    | ... [{len(t.splitlines()) - 8} more lines]")

    banner(f"Step 3 · Agentic grading · {settings.grader_num_passes} pass(es)")
    for c in all_crops:
        print(f"\n  crop: {Path(c).name}")
        passes = grade_multi_pass(
            c,
            question=SAMPLE_RUBRIC["question_text"],
            max_marks=SAMPLE_RUBRIC["max_marks"],
            criteria=SAMPLE_RUBRIC["criteria"],
        )
        for i, p in enumerate(passes, 1):
            print(f"    pass {i}: {p['score']:.1f}/{p['max_score']:.0f}")
        agg = aggregate_scores(passes)
        print(f"    → median {agg['median']} · max {agg['max_score']} · min {agg['min_score']} · σ {agg['std_dev']:.2f}")
        med = min(passes, key=lambda p: abs(p["score"] - agg["median"]))
        print(f"    justification: {med['justification']}")

    banner("done")


def main():
    if len(sys.argv) > 1:
        target = Path(sys.argv[1]).expanduser().resolve()
        if not target.exists():
            print(f"file not found: {target}")
            sys.exit(2)
    else:
        samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples"
        candidates = (
            sorted(samples_dir.glob("*.png")) + sorted(samples_dir.glob("*.jpg")) +
            sorted(samples_dir.glob("*.jpeg")) + sorted(samples_dir.glob("*.pdf"))
        )
        if not candidates:
            print("Usage: python scripts/run_demo.py path/to/answer.{jpg,pdf}")
            sys.exit(1)
        target = candidates[0]

    if not settings.google_api_key and not settings.anthropic_api_key:
        print("ERROR: No API key configured. Set GOOGLE_API_KEY (or ANTHROPIC_API_KEY) in .env.")
        sys.exit(3)

    run(target)


if __name__ == "__main__":
    main()
