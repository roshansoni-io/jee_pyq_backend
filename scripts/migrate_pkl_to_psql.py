"""One-off migration: load the cached pkl database into PostgreSQL.

Run:

    python3 scripts/migrate_pkl_to_psql.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OLD = REPO.parent / "jee_pyqs"
sys.path.insert(0, str(OLD))

import psycopg
from tqdm import tqdm

DB_KWARGS = dict(
    user=os.environ.get("PYQ_DB_USER", "u0_a320"),
    dbname=os.environ.get("PYQ_DB_NAME", "pyq"),
    host=os.environ.get("PYQ_DB_HOST", "127.0.0.1"),
    port=int(os.environ.get("PYQ_DB_PORT", "5432")),
)


def _exam_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def main() -> None:
    from jee_data_base import DataBase
    from jee_data_base.core.filter import _get_embeddings_dict

    db = DataBase()
    embeddings = _get_embeddings_dict()

    questions = [q for ch in db.chapters_dict.values() for q in ch.question_dict.values()]
    print(f"questions: {len(questions)}, embeddings: {len(embeddings)}")

    conn = psycopg.connect(**DB_KWARGS)
    try:
        cur = conn.cursor()
        try:
            subjects = {q.subject for q in questions}
            cur.executemany(
                "insert into subjects (id) values (%s) on conflict do nothing",
                tqdm([(s,) for s in sorted(subjects)], desc="subjects"),
            )
            chapters = {}
            topics = set()
            for ch in db.chapters_dict.values():
                parent = ch.question_dict and next(iter(ch.question_dict.values())).subject or ch.parent_subject
                chapters[ch.name] = (ch.name, parent, None, ch.name)
                for q in ch.question_dict.values():
                    chapters[ch.name] = (ch.name, q.subject, q.chpaterGroup or None, ch.name)
                    if q.topic:
                        topics.add((q.chapter, q.topic))
            cur.executemany(
                "insert into chapters (id, subject_id, chapter_group, name) values (%s,%s,%s,%s) on conflict do nothing",
                tqdm(sorted(chapters.values()), desc="chapters"),
            )
            cur.executemany(
                "insert into topics (chapter_id, id) values (%s,%s) on conflict do nothing",
                tqdm(sorted(topics), desc="topics"),
            )
            cur.executemany(
                """insert into questions
                   (id, exam, exam_group, subject, chapter, chapter_group, year,
                    paper_title, difficulty, topic, type, exam_date, answer,
                    question, options, correct_options, explanation,
                    is_out_of_syllabus, is_bonus, is_img_question,
                    is_img_explanation, is_img_option)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict (id) do nothing""",
                tqdm((
                    (
                        q.question_id, q.exam, q.examGroup, q.subject, q.chapter,
                        q.chpaterGroup or None, q.year, q.paperTitle, q.difficulty,
                        q.topic, q.type, _exam_date(q.examDate),
                        json.dumps(q.answer), q.question, json.dumps(q.options),
                        json.dumps(q.correct_options), q.explanation,
                        q.isOutOfSyllabus, q.isBonus, q.isImgQuestion,
                        q.isImgExplanation, json.dumps(q.isImgOption),
                    )
                    for q in questions
                ), desc="questions", total=len(questions)),
            )
            cur.executemany(
                "insert into question_embeddings (question_id, embedding) values (%s, %s::vector) on conflict do nothing",
                tqdm((
                    (qid, "[" + ",".join(map(str, vec)) + "]")
                    for qid, vec in embeddings.items()
                ), desc="embeddings", total=len(embeddings)),
            )
        finally:
            cur.close()
        conn.commit()
    finally:
        conn.close()

    conn = psycopg.connect(**DB_KWARGS)
    try:
        cur = conn.cursor()
        try:
            for table in ("subjects", "chapters", "topics", "questions", "question_embeddings"):
                cur.execute(f"select count(*) from {table}")
                print(table, cur.fetchone()[0])
        finally:
            cur.close()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
