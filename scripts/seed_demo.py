"""Seed a sample exam and rubric so a fresh install has something to show.

Run once after init_db.py. Idempotent — skips if any exam exists.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import SessionLocal, Exam, Rubric


SAMPLE_RUBRIC_CRITERIA = [
    {
        "name": "Isolate the variable term",
        "points": 5,
        "conditions": "Student subtracts 5 from both sides to obtain 2x = 10.",
        "accept_alternatives": "Equivalent algebraic rearrangements that arrive at 2x = 10.",
        "do_not_deduct_for": "Minor handwriting or notation differences.",
    },
    {
        "name": "Solve for x",
        "points": 5,
        "conditions": "Student divides both sides by 2 and obtains x = 5.",
        "accept_alternatives": "Equivalent forms such as x=5 or x = 5.0.",
        "do_not_deduct_for": "Minor notation differences.",
    },
]

DEFAULT_INSTRUCTIONS = """Base all scoring strictly on evidence visible in the student's handwritten work. If evidence is missing, assign zero — do not guess, infer, or hallucinate.
Award credit for intermediate steps only if explicitly written by the student. Do not infer non-trivial reasoning from a correct final answer except for trivial algebraic simplifications.
If the student's solution does not match the question being asked, assign a score of 0."""


def main():
    db = SessionLocal()
    try:
        if db.query(Exam).count() > 0:
            print("an exam already exists; skipping seed")
            return

        exam = Exam(title="Sample exam")
        db.add(exam); db.commit(); db.refresh(exam)

        rubric = Rubric(
            exam_id=exam.id,
            version="v1",
            title="Linear equation — sample",
            question_text="Solve for x and show all steps:\n\n2x + 5 = 15",
            max_marks=10,
            course_instructions=DEFAULT_INSTRUCTIONS,
            criteria=SAMPLE_RUBRIC_CRITERIA,
        )
        db.add(rubric); db.commit(); db.refresh(rubric)
        print(f"seeded exam #{exam.id} '{exam.title}'")
        print(f"seeded rubric #{rubric.id} '{rubric.title}' ({rubric.version})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
