from __future__ import annotations

import logging
from pathlib import Path

import psycopg

from . import config

logger = logging.getLogger("pyq.migrations")
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_LOCK_KEY = 0x505951  # "PYQ"


def _statements(script: str) -> list[str]:
    """Split the repository's plain SQL migrations at statement terminators."""
    # Migration files intentionally use ordinary SQL statements only. Avoid
    # sending a whole file as one query: CREATE INDEX CONCURRENTLY must run
    # outside a transaction block.
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def _already_applied(conn: psycopg.Connection, version: str) -> bool:
    """Adopt manually applied historical migrations on first runner startup."""
    if version == "001":
        row = conn.execute(
            "select"
            " exists (select 1 from pg_constraint where conrelid = to_regclass('chapters')"
            "   and conname = 'chapters_subject_id_id_key') as chapter_key,"
            " exists (select 1 from pg_constraint where conrelid = to_regclass('questions')"
            "   and conname = 'questions_subject_chapter_fk') as subject_chapter_fk,"
            " exists (select 1 from pg_constraint where conrelid = to_regclass('questions')"
            "   and conname = 'questions_chapter_topic_fk') as chapter_topic_fk"
        ).fetchone()
        return all(row)
    if version == "002":
        row = conn.execute(
            "select count(*) = 2 from information_schema.columns"
            " where table_schema = current_schema() and table_name = 'questions'"
            " and column_name = any(%s)",
            (["shift", "exam_date"],),
        ).fetchone()
        return bool(row[0])
    if version == "003":
        row = conn.execute(
            "select count(*) = 5 from pg_indexes where schemaname = current_schema()"
            " and indexname = any(%s)",
            ([
                "questions_chapter_trgm_idx",
                "questions_topic_trgm_idx",
                "questions_paper_title_trgm_idx",
                "questions_exam_trgm_idx",
                "questions_exam_group_trgm_idx",
            ],),
        ).fetchone()
        return bool(row[0])
    if version == "004":
        row = conn.execute(
            "select to_regclass('questions_id_unique_idx') is not null or exists ("
            " select 1 from pg_constraint where conrelid = to_regclass('questions')"
            " and contype = 'p')"
        ).fetchone()
        return bool(row[0])
    if version == "005":
        row = conn.execute(
            "select count(*) = 9 from pg_indexes where schemaname = current_schema()"
            " and indexname = any(%s)",
            ([
                "questions_subject_idx",
                "questions_chapter_idx",
                "questions_topic_idx",
                "questions_year_idx",
                "questions_difficulty_idx",
                "questions_type_idx",
                "questions_chapter_group_idx",
                "questions_subject_chapter_idx",
                "questions_year_date_id_idx",
            ],),
        ).fetchone()
        return bool(row[0])
    if version == "006":
        row = conn.execute(
            "select to_regclass('chapters_id_unique_idx') is not null and"
            " to_regclass('question_embeddings_question_id_unique_idx') is not null and"
            " to_regclass('topics_chapter_id_id_unique_idx') is not null"
        ).fetchone()
        return bool(row[0])
    return False


def _blocking_reason(conn: psycopg.Connection, version: str) -> str | None:
    if version == "001":
        row = conn.execute(
            "select count(*) from ("
            " select subject_id, id from chapters"
            " group by subject_id, id having count(*) > 1"
            ") duplicates"
        ).fetchone()
        if row[0]:
            return (
                f"{row[0]} duplicate (subject_id, id) chapter keys prevent "
                "the taxonomy uniqueness and foreign-key constraints"
            )
    return None


def apply_migrations() -> None:
    """Apply unapplied SQL migrations under a database-wide advisory lock."""
    migration_files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute("select pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            conn.execute(
                "create table if not exists public.pyq_schema_migrations ("
                "version text primary key, applied_at timestamptz not null default now())"
            )
            while True:
                progressed = False
                for path in migration_files:
                    version = path.name[:3]
                    applied = conn.execute(
                        "select 1 from public.pyq_schema_migrations where version = %s",
                        (version,),
                    ).fetchone()
                    if applied:
                        continue

                    if _already_applied(conn, version):
                        conn.execute(
                            "insert into public.pyq_schema_migrations(version) values (%s)"
                            " on conflict do nothing",
                            (version,),
                        )
                        logger.info("adopted existing database migration %s", path.name)
                        progressed = True
                        continue

                    blocker = _blocking_reason(conn, version)
                    if blocker:
                        logger.warning("leaving migration %s pending: %s", path.name, blocker)
                        continue

                    logger.info("applying database migration %s", path.name)
                    try:
                        for statement in _statements(path.read_text(encoding="utf-8")):
                            if version == "001":
                                lower = statement.lower()
                                constraint = None
                                table = None
                                for candidate_table, candidate_constraint in (
                                    ("chapters", "chapters_subject_id_id_key"),
                                    ("questions", "questions_subject_chapter_fk"),
                                    ("questions", "questions_chapter_topic_fk"),
                                ):
                                    if f"add constraint {candidate_constraint}" in lower:
                                        table, constraint = candidate_table, candidate_constraint
                                        break
                                if constraint and conn.execute(
                                    "select exists (select 1 from pg_constraint"
                                    " where conrelid = to_regclass(%s) and conname = %s)",
                                    (table, constraint),
                                ).fetchone()[0]:
                                    continue
                            conn.execute(statement, prepare=False)
                    except Exception:
                        conn.rollback()
                        raise
                    conn.execute(
                        "insert into public.pyq_schema_migrations(version) values (%s)",
                        (version,),
                    )
                    progressed = True
                if not progressed:
                    break
        finally:
            conn.execute("select pg_advisory_unlock(%s)", (_LOCK_KEY,))
