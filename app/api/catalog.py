from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .common import limit_offset
from ..db import fetch_all, fetch_one
from ..serializers import chapter_payload, humanize, ok, subject_payload

router = APIRouter()

default_chapter_size = 100
max_chapter_size = 500


@router.get("/health")
def health(request: Request):
    conn = request.state.conn
    q = fetch_one(conn, "select count(*) as n from questions")
    c = fetch_one(conn, "select count(*) as n from chapters")
    return ok({"status": "ok", "questions": q["n"], "chapters": c["n"]})


# Cached once found: a process may start before schema.sql creates the view, so
# a negative result is re-checked instead of pinned.
_have_stats_view: bool = False


def _stats_view_available(conn) -> bool:
    global _have_stats_view
    if not _have_stats_view:
        _have_stats_view = (
            fetch_one(conn, "select to_regclass('question_stats') as r")["r"] is not None
        )
    return _have_stats_view


@router.get("/stats")
def stats(request: Request):
    conn = request.state.conn
    if _stats_view_available(conn):
        rows = fetch_all(
            conn,
            "select axis, key, count from question_stats where axis = any(%s)",
            (["subject", "year", "total"],),
        )
        by_subject = [
            {"id": r["key"], "count": int(r["count"])}
            for r in rows
            if r["axis"] == "subject"
        ]
        by_year = [
            {"year": int(r["key"]), "count": int(r["count"])}
            for r in rows
            if r["axis"] == "year"
        ]
        totals = {r["key"]: int(r["count"]) for r in rows if r["axis"] == "total"}
        return ok({
            "total_questions": totals.get("questions", 0),
            "total_subjects": totals.get("subjects", 0),
            "total_chapters": totals.get("chapters", 0),
            "by_subject": sorted(by_subject, key=lambda r: r["id"]),
            "by_year": sorted(by_year, key=lambda r: r["year"]),
        })

    # Fallback: aggregate live when the materialized view is absent.
    by_subject = fetch_all(
        conn,
        "select subject as id, count(*) as count from questions group by subject order by subject",
    )
    by_year = fetch_all(
        conn, "select year, count(*) as count from questions group by year order by year"
    )
    totals = fetch_one(
        conn,
        "select (select count(*) from questions) as total_questions,"
        " (select count(*) from subjects) as total_subjects,"
        " (select count(*) from chapters) as total_chapters",
    )
    return ok({
        "total_questions": totals["total_questions"],
        "total_subjects": totals["total_subjects"],
        "total_chapters": totals["total_chapters"],
        "by_subject": by_subject,
        "by_year": by_year,
    })


@router.get("/subjects")
def list_subjects(request: Request):
    rows = fetch_all(request.state.conn, "select id from subjects order by id")
    return ok([subject_payload(r) for r in rows])


@router.get("/subjects/{subject_id}/chapters")
def list_subject_chapters(request: Request, subject_id: str):
    qp = request.query_params
    limit, offset = limit_offset(qp, default_chapter_size, max_chapter_size)
    conn = request.state.conn
    # Single round trip: the total rides along as a scalar subquery, and the 404
    # check is deferred to the empty-result path.
    rows = fetch_all(
        conn,
        "select c.id, c.chapter_number, c.chapter_group,"
        " coalesce(q.question_count, 0) as question_count,"
        " (select count(*) from chapters where subject_id = %s) as total"
        " from chapters c"
        " left join (select chapter, count(*) as question_count from questions"
        "            where subject = %s group by chapter) q on q.chapter = c.id"
        " where c.subject_id = %s"
        " order by c.chapter_number nulls last, c.id limit %s offset %s",
        (subject_id, subject_id, subject_id, limit, offset),
    )
    if not rows:
        counts = fetch_one(
            conn,
            "select (select count(*) from subjects where id = %s) as subject_rows,"
            " (select count(*) from chapters where subject_id = %s) as total",
            (subject_id, subject_id),
        )
        if counts["subject_rows"] == 0:
            raise HTTPException(404, f"subject '{subject_id}' not found")
        return ok([], meta={
            "subject": subject_id,
            "total": counts["total"],
            "limit": limit,
            "offset": offset,
        })
    total = rows[0]["total"]
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
    chapter = fetch_one(
        conn,
        "select c.id, c.chapter_number, c.chapter_group, count(q.id) as question_count"
        " from chapters c left join questions q on q.chapter = c.id"
        " where c.id = %s group by c.id, c.chapter_number, c.chapter_group",
        (chapter_id,),
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
