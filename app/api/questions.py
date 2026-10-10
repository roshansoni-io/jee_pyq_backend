from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .common import limit_offset
from ..db import fetch_all, fetch_one
from ..filters import order_by, parse_filters, seeded_order_by, sort_orders
from ..serializers import ok, question_detail, question_summary

router = APIRouter()

default_page_size = 50
max_page_size = 500

# List-response columns; detail queries append body fields.
QUESTION_SUMMARY_COLS = (
    "id, exam, exam_group, subject, chapter, year, paper_title,"
    " exam_date, shift, difficulty, topic, type"
)
QUESTION_DETAIL_COLS = QUESTION_SUMMARY_COLS + (
    ", is_bonus, question, options, correct_options, answer, explanation"
)


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
    """Fetch one page in the requested order."""
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
    marks = ", ".join("%s" for _ in ids)
    rows = fetch_all(conn, f"select {cols} from questions where id in ({marks})", tuple(ids))
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


@router.get("/questions")
def list_questions(request: Request):
    qp = request.query_params
    limit, offset = limit_offset(qp, default_page_size, max_page_size)
    sort_order = qp.get("sort", "newest")
    if sort_order not in sort_orders:
        raise HTTPException(
            400, f"invalid sort '{sort_order}', expected one of {sort_orders}"
        )
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
    rows = _page(
        conn, QUESTION_SUMMARY_COLS, where, tuple(params), clause, extra, limit, offset
    )
    return ok(
        [question_summary(r) for r in rows],
        meta={
            "total": total,
            "limit": limit,
            "offset": offset,
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
