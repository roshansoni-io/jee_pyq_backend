from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from . import clustering
from .db import fetch_all, fetch_one
from .filters import parse_filters, order_by, sort_orders
from .serializers import (
    chapter_payload,
    clamp,
    humanize,
    ok,
    question_detail,
    question_summary,
    subject_payload,
    topic_payload,
)

router = APIRouter(prefix="/api/v1")

default_page_size = 50
max_page_size = 500
default_practice_size = 10
max_practice_size = 50
default_cluster_threshold = 0.6
default_cluster_max_questions = 2_000
max_cluster_questions = 20_000

QUESTION_COLS = (
    "id, exam, exam_group, subject, chapter, chapter_group, year, paper_title,"
    " difficulty, topic, type, exam_date, is_out_of_syllabus, is_bonus"
)
QUESTION_DETAIL_COLS = QUESTION_COLS + (
    ", question, options, correct_options, answer, explanation,"
    " is_img_question, is_img_explanation, is_img_option"
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


@router.get("/stats")
def stats(request: Request):
    conn = request.state.conn
    by_subject = fetch_all(
        conn,
        "select subject as id, count(*) as count from questions group by subject order by subject",
    )
    by_year = fetch_all(
        conn, "select year, count(*) as count from questions group by year order by year"
    )
    totals = fetch_one(
        conn,
        "select count(*) as total_questions,"
        " count(distinct subject) as total_subjects,"
        " count(distinct chapter) as total_chapters from questions",
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
    rows = fetch_all(
        request.state.conn,
        "select subject as id, count(distinct chapter) as chapter_count, count(*) as question_count"
        " from questions group by subject order by subject",
    )
    return ok([subject_payload(r) for r in rows])


@router.get("/subjects/{subject_id}/groups")
def list_subject_groups(request: Request, subject_id: str):
    conn = request.state.conn
    exists = fetch_one(conn, "select 1 as x from subjects where id = %s", (subject_id,))
    if exists is None:
        raise HTTPException(404, f"subject '{subject_id}' not found")
    rows = fetch_all(
        conn,
        "select chapter_group as id, count(*) as question_count from questions"
        " where subject = %s and chapter_group is not null and chapter_group <> ''"
        " group by chapter_group order by chapter_group",
        (subject_id,),
    )
    groups = [
        {"id": r["id"], "name": humanize(r["id"]), "question_count": r["question_count"]}
        for r in rows
    ]
    return ok(groups, meta={"subject": subject_id})


@router.get("/subjects/{subject_id}/chapters")
def list_subject_chapters(request: Request, subject_id: str):
    conn = request.state.conn
    exists = fetch_one(conn, "select 1 as x from subjects where id = %s", (subject_id,))
    if exists is None:
        raise HTTPException(404, f"subject '{subject_id}' not found")
    rows = fetch_all(
        conn,
        "select chapter as id, count(*) as question_count,"
        " count(distinct topic) filter (where topic <> '') as topic_count"
        " from questions where subject = %s group by chapter order by chapter",
        (subject_id,),
    )
    return ok([chapter_payload(r) for r in rows], meta={"subject": subject_id})


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


@router.get("/questions")
def list_questions(request: Request):
    qp = request.query_params
    limit, offset = _limit_offset(qp, default_page_size, max_page_size)
    sort_order = qp.get("sort", "newest")
    if sort_order not in sort_orders:
        raise HTTPException(400, f"invalid sort '{sort_order}', expected one of {sort_orders}")
    filters = parse_filters(qp)
    where, params = filters.where()
    total = fetch_one(request.state.conn, f"select count(*) as n from questions{where}", params)["n"]
    rows = fetch_all(
        request.state.conn,
        f"select {QUESTION_COLS} from questions{where} {order_by(sort_order)} limit %s offset %s",
        (*params, limit, offset),
    )
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
    limit, _ = _limit_offset(qp, default_practice_size, max_practice_size)
    filters = parse_filters(qp)
    where, params = filters.where()
    rows = fetch_all(
        request.state.conn,
        f"select {QUESTION_DETAIL_COLS} from questions{where} order by random() limit %s",
        (*params, limit),
    )
    return ok(
        [question_detail(r) for r in rows],
        meta={"total": len(rows), "filters": filters.as_dict()},
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

    where, params = filters.where()
    rows = fetch_all(
        request.state.conn,
        "select q.id as id, e.embedding::text as embedding from questions q"
        " left join question_embeddings e on e.question_id = q.id"
        f"{_where_q_prefixed(where)} "
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


def _where_q_prefixed(where: str) -> str:
    if not where:
        return ""
    clauses = where[len(" where "):].split(" and ")
    return " where " + " and ".join(f"q.{c}" for c in clauses)
