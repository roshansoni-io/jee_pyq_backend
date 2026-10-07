from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from . import clustering
from .db import fetch_all, fetch_one
from .filters import parse_filters, order_by, seeded_order_by, sort_orders
from .serializers import (
    chapter_payload,
    clamp,
    ok,
    question_detail,
    question_summary,
    subject_payload,
    topic_payload,
)

router = APIRouter(prefix="/api/v1")

default_page_size = 50
max_page_size = 500
default_chapter_size = 100
max_chapter_size = 500
default_practice_size = 10
max_practice_size = 500
default_cluster_threshold = 0.6
default_cluster_max_questions = 2_000
max_cluster_questions = 20_000

# List-response columns; QUESTION_DETAIL_COLS appends the body fields.
QUESTION_SUMMARY_COLS = (
    "id, exam, exam_group, subject, chapter, year, paper_title,"
    " difficulty, topic, type"
)
QUESTION_DETAIL_COLS = QUESTION_SUMMARY_COLS + (
    ", is_bonus, question, options, correct_options, answer, explanation"
)


def _limit_offset(qp, default_size: int, max_size: int) -> tuple[int, int]:
    try:
        limit = int(qp.get("limit", default_size))
    except (TypeError, ValueError):
        limit = default_size
    try:
        offset = int(qp.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    return clamp(limit, 0, max_size), max(0, offset)


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
    limit, offset = _limit_offset(qp, default_chapter_size, max_chapter_size)
    conn = request.state.conn
    # Single round trip: the total rides along as a scalar subquery, and the 404
    # check is deferred to the empty-result path.
    rows = fetch_all(
        conn,
        "select c.id, coalesce(q.question_count, 0) as question_count,"
        " (select count(*) from chapters where subject_id = %s) as total"
        " from chapters c"
        " left join (select chapter, count(*) as question_count from questions"
        "            where subject = %s group by chapter) q on q.chapter = c.id"
        " where c.subject_id = %s"
        " order by c.chapter_group, c.id limit %s offset %s",
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
            "has_more": False,
        })
    total = rows[0]["total"]
    return ok(
        [chapter_payload(r) for r in rows],
        meta={
            "subject": subject_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(rows) < total,
        },
    )


@router.get("/chapters/{chapter_id}/topics")
def list_chapter_topics(request: Request, chapter_id: str):
    conn = request.state.conn
    exists = fetch_one(conn, "select 1 as x from chapters where id = %s", (chapter_id,))
    if exists is None:
        raise HTTPException(404, f"chapter '{chapter_id}' not found")
    rows = fetch_all(
        conn,
        "select topic as id, count(*) as question_count from questions"
        " where chapter = %s and topic <> '' group by topic order by topic",
        (chapter_id,),
    )
    return ok([topic_payload(r) for r in rows], meta={"chapter": chapter_id})


def _page(
    conn,
    cols: str,
    where: str,
    params: tuple,
    clause: str,
    extra: tuple,
    limit: int,
    offset: int,
) -> list[dict]:
    """Fetch one page in the requested order.

    A random order under 250 rows samples ids first, then reloads them by primary
    key: sorting wide detail rows for `order by random()` costs ~2x (61 ms vs
    29 ms) because each comparison drags `options`/`explanation` jsonb along.
    Larger pages take the single-query path, where the id list stops being small.
    """
    if clause.strip() != "order by random()" or limit > 250:
        return fetch_all(
            conn,
            f"select {cols} from questions{where} {clause} limit %s offset %s",
            (*params, *extra, limit, offset),
        )

    sampled = fetch_all(
        conn,
        f"select id from questions{where} {clause} limit %s offset %s",
        (*params, *extra, limit, offset),
    )
    ids = [r["id"] for r in sampled]
    if not ids:
        return []
    rows = fetch_all(conn, f"select {cols} from questions where id = any(%s)", (ids,))
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


@router.get("/questions")
def list_questions(request: Request):
    qp = request.query_params
    limit, offset = _limit_offset(qp, default_page_size, max_page_size)
    sort_order = qp.get("sort", "newest")
    if sort_order not in sort_orders:
        raise HTTPException(400, f"invalid sort '{sort_order}', expected one of {sort_orders}")
    filters = parse_filters(qp)
    where, params = filters.where()
    # A seed pins the random order across pages.
    if sort_order == "random" and qp.get("seed"):
        clause = seeded_order_by("")
        extra = (qp["seed"],)
    else:
        clause = order_by(sort_order)
        extra = ()
    conn = request.state.conn
    total = fetch_one(conn, f"select count(*) as n from questions{where}", params)["n"]
    rows = _page(conn, QUESTION_SUMMARY_COLS, where, tuple(params), clause, extra, limit, offset)
    return ok(
        [question_summary(r) for r in rows],
        meta={
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
            "sort": sort_order,
            "filters": filters.as_dict(),
        },
    )


@router.get("/questions/{question_id}")
def get_question(request: Request, question_id: str):
    row = fetch_one(
        request.state.conn,
        f"select {QUESTION_DETAIL_COLS} from questions where id = %s",
        (question_id,),
    )
    if row is None:
        raise HTTPException(404, "question not found")
    return ok(question_detail(row))


@router.get("/practice")
def practice(request: Request):
    qp = request.query_params
    limit, offset = _limit_offset(qp, default_practice_size, max_practice_size)
    filters = parse_filters(qp)
    where, params = filters.where()
    # Random by default; a seed pins the shuffle so paging stays consistent.
    sort_order = qp.get("order", "random")
    if sort_order not in sort_orders:
        sort_order = "random"
    if sort_order == "random" and qp.get("seed"):
        clause = seeded_order_by("")
        extra = (qp["seed"],)
    else:
        clause = order_by(sort_order)
        extra = ()
    conn = request.state.conn

    # `question=<id>` returns that question first, then fills the page with
    # siblings. The lookup carries the filters, so an anchor from another chapter
    # falls through to the ordinary page below.
    anchor = qp.get("question")
    if anchor:
        anchor_where = f"{where} and id = %s" if where else " where id = %s"
        target = fetch_one(
            conn, f"select {QUESTION_DETAIL_COLS} from questions{anchor_where}", (*params, anchor)
        )
        if target is not None:
            # The page sequence is the anchor at position 0, then siblings excluding
            # it, so offset >= 1 addresses siblings at offset - 1.
            exclude = f"{where} and id <> %s" if where else " where id <> %s"
            available = fetch_one(
                conn, f"select count(*) as n from questions{where}", tuple(params)
            )["n"]
            if offset == 0:
                siblings = _page(
                    conn,
                    QUESTION_DETAIL_COLS,
                    exclude,
                    (*params, anchor),
                    clause,
                    extra,
                    max(limit - 1, 0),
                    0,
                )
                rows = [target, *siblings] if limit else []
            else:
                rows = _page(
                    conn,
                    QUESTION_DETAIL_COLS,
                    exclude,
                    (*params, anchor),
                    clause,
                    extra,
                    limit,
                    offset - 1,
                )
            return ok(
                [question_detail(r) for r in rows],
                meta={
                    "total": len(rows),
                    "available": available,
                    "offset": offset,
                    "has_more": offset + len(rows) < available,
                    "order": sort_order,
                    "anchored": True,
                    "filters": filters.as_dict(),
                },
            )

    rows = _page(conn, QUESTION_DETAIL_COLS, where, tuple(params), clause, extra, limit, offset)
    available = fetch_one(conn, f"select count(*) as n from questions{where}", tuple(params))["n"]
    return ok(
        [question_detail(r) for r in rows],
        meta={
            "total": len(rows),
            "available": available,
            "offset": offset,
            "has_more": offset + len(rows) < available,
            "order": sort_order,
            "filters": filters.as_dict(),
        },
    )


@router.get("/cluster")
def cluster_questions(request: Request):
    qp = request.query_params
    filters = parse_filters(qp)
    try:
        threshold = float(qp.get("threshold", default_cluster_threshold))
    except (TypeError, ValueError):
        threshold = default_cluster_threshold
    try:
        max_questions = int(qp.get("max_questions", default_cluster_max_questions))
    except (TypeError, ValueError):
        max_questions = default_cluster_max_questions
    max_questions = clamp(max_questions, 0, max_cluster_questions)

    where, params = filters.where("q.")
    rows = fetch_all(
        request.state.conn,
        "select q.id as id, e.embedding::text as embedding from questions q"
        " left join question_embeddings e on e.question_id = q.id"
        f"{where} "
        "order by q.id limit %s",
        (*params, max_questions),
    )
    questions_present: list[str] = []
    vectors: list[list[float]] = []
    missing: list[str] = []
    for r in rows:
        if r["embedding"] is None:
            missing.append(r["id"])
        else:
            questions_present.append(r["id"])
            text = r["embedding"].strip().strip("[]")
            vectors.append([float(x) for x in text.split(",")])

    clusters = clustering.cluster_members(questions_present, vectors, threshold)
    cluster_list = [
        {
            "cluster_id": cid,
            "size": len(members),
            "representative_question_id": members[0] if members else None,
            "question_ids": members,
        }
        for cid, members in sorted(clusters.items())
    ]
    return ok(
        {"clusters": cluster_list, "missing_embedding": missing},
        meta={
            "num_clusters": len(cluster_list),
            "threshold": threshold,
            "filters": filters.as_dict(),
        },
    )
