"""Initialize the database. Idempotent. Run once after install."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import init_db, SessionLocal, User


def main():
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all([
                User(email="instructor@gradeops.local", name="Instructor", role="instructor"),
                User(email="ta@gradeops.local", name="TA", role="ta"),
            ])
            db.commit()
            print("seeded default users (instructor + ta)")
        else:
            print(f"db already has {db.query(User).count()} user(s); skipping seed")
    finally:
        db.close()
    print("db ready")


if __name__ == "__main__":
    main()
