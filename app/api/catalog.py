from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .common import limit_offset
from ..db import fetch_all, fetch_one
from ..serializers import chapter_payload, humanize, ok, subject_payload

router = APIRouter()

DEFAULT_CHAPTER_SIZE = 100
MAX_CHAPTER_SIZE = 500


@router.get("/health")
def health(request: Request):
    # Single round trip: both counts come back in one row.
    row = fetch_one(
        request.state.conn,
        "select"
        " (select count(*) from questions) as questions,"
        " (select count(*) from chapters) as chapters",
    )
    return ok(
        {
            "status": "ok",
            "questions": row["questions"],
            "chapters": row["chapters"],
        }
    )


# The schema may be created after the process starts, so a negative result is
# re-checked on every request instead of being pinned.
_have_stats_view = False


def _stats_view_available(conn) -> bool:
    global _have_stats_view
    if not _have_stats_view:
        row = fetch_one(conn, "select to_regclass('question_stats') as r")
        _have_stats_view = row["r"] is not None
    return _have_stats_view


def _stats_from_view(conn) -> dict:
    rows = fetch_all(
        conn,
        "select axis, key, count from question_stats where axis = any(%s)",
        (["subject", "year", "total"],),
    )
    totals = {r["key"]: int(r["count"]) for r in rows if r["axis"] == "total"}
    return {
        "total_questions": totals.get("questions", 0),
        "total_subjects": totals.get("subjects", 0),
        "total_chapters": totals.get("chapters", 0),
        "by_subject": sorted(
            (
                {"id": r["key"], "count": int(r["count"])}
                for r in rows
                if r["axis"] == "subject"
            ),
            key=lambda r: r["id"],
        ),
        "by_year": sorted(
            (
                {"year": int(r["key"]), "count": int(r["count"])}
                for r in rows
                if r["axis"] == "year"
            ),
            key=lambda r: r["year"],
        ),
    }


def _stats_from_live_tables(conn) -> dict:
    totals = fetch_one(
        conn,
        "select (select count(*) from questions) as total_questions,"
        " (select count(*) from subjects) as total_subjects,"
        " (select count(*) from chapters) as total_chapters",
    )
    return {
        "total_questions": totals["total_questions"],
        "total_subjects": totals["total_subjects"],
        "total_chapters": totals["total_chapters"],
        "by_subject": fetch_all(
            conn,
            "select subject as id, count(*) as count from questions"
            " group by subject order by subject",
        ),
        "by_year": fetch_all(
            conn,
            "select year, count(*) as count from questions group by year order by year",
        ),
    }


@router.get("/stats")
def stats(request: Request):
    conn = request.state.conn
    if _stats_view_available(conn):
        return ok(_stats_from_view(conn))
    return ok(_stats_from_live_tables(conn))


@router.get("/subjects")
def list_subjects(request: Request):
    rows = fetch_all(request.state.conn, "select id from subjects order by id")
    return ok([subject_payload(r) for r in rows])


@router.get("/subjects/{subject_id}/chapters")
def list_subject_chapters(request: Request, subject_id: str):
    limit, offset = limit_offset(
        request.query_params, DEFAULT_CHAPTER_SIZE, MAX_CHAPTER_SIZE
    )
    conn = request.state.conn

    rows = fetch_all(
        conn,
        "with subject_chapters as ("
        "    select id,"
        "           min(chapter_number) as chapter_number,"
        "           min(chapter_group)  as chapter_group"
        "    from chapters"
        "    where subject_id = %s"
        "    group by id"
        ")"
        " select c.id, c.chapter_number, c.chapter_group,"
        "        coalesce(q.question_count, 0) as question_count,"
        "        count(*) over () as total"
        " from subject_chapters c"
        " left join ("
        "     select chapter, count(*) as question_count"
        "     from questions"
        "     where subject = %s"
        "     group by chapter"
        " ) q on q.chapter = c.id"
        " order by c.chapter_number nulls last, c.id"
        " limit %s offset %s",
        (subject_id, subject_id, limit, offset),
    )

    if rows:
        total = rows[0]["total"]
    else:
        # Empty page: distinguish "subject missing" from "offset past the end".
        counts = fetch_one(
            conn,
            "select"
            " (select count(*) from subjects where id = %s) as subject_rows,"
            " (select count(distinct id) from chapters where subject_id = %s) as total",
            (subject_id, subject_id),
        )
        if counts["subject_rows"] == 0:
            raise HTTPException(404, f"subject '{subject_id}' not found")
        total = counts["total"]

    return ok(
        [chapter_payload(r) for r in rows],
        meta={
            "subject": subject_id,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get("/chapters/{chapter_id}")
def get_chapter(request: Request, chapter_id: str):
    conn = request.state.conn

    # Same dedup pattern: collapse duplicate chapter rows first, then attach
    # the pre-aggregated question count. The old version joined questions
    # directly, so duplicate chapters multiplied the question count.
    chapter = fetch_one(
        conn,
        "with target as ("
        "    select id,"
        "           min(chapter_number) as chapter_number,"
        "           min(chapter_group)  as chapter_group"
        "    from chapters"
        "    where id = %s"
        "    group by id"
        ")"
        " select c.id, c.chapter_number, c.chapter_group,"
        "        coalesce(q.question_count, 0) as question_count"
        " from target c"
        " left join ("
        "     select chapter, count(*) as question_count"
        "     from questions"
        "     where chapter = %s"
        "     group by chapter"
        " ) q on q.chapter = c.id",
        (chapter_id, chapter_id),
    )

    if chapter is None:
        raise HTTPException(404, f"chapter '{chapter_id}' not found")

    topic_rows = fetch_all(
        conn,
        "select id from topics where chapter_id = %s and id <> '' order by id",
        (chapter_id,),
    )
    topics = [{"id": row["id"], "name": humanize(row["id"])} for row in topic_rows]
    return ok({**chapter_payload(chapter), "topics": topics})
