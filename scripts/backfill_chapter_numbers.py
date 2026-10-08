"""Add/backfill the NCERT-based chapter sequence in an existing database."""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.chapter_order import CHAPTER_NUMBER
from app.config import DATABASE_URL


def main() -> None:
    assignments = [
        (number, chapter_id, subject)
        for (subject, chapter_id), number in CHAPTER_NUMBER.items()
    ]
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("alter table chapters add column if not exists chapter_number integer")
            cur.executemany(
                "update chapters set chapter_number = %s where id = %s and subject_id = %s",
                assignments,
            )
            cur.execute(
                "create unique index if not exists chapters_subject_number_idx "
                "on chapters(subject_id, chapter_number)"
            )
            cur.execute(
                "select subject_id, id from chapters where chapter_number is null order by subject_id, id"
            )
            missing = cur.fetchall()
            if missing:
                raise RuntimeError(f"No NCERT order mapping for chapters: {missing}")
            cur.execute("select count(*) from chapters")
            count = cur.fetchone()[0]
    print(f"Backfilled NCERT-based chapter numbers for {count} chapters.")


if __name__ == "__main__":
    main()
