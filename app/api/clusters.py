from __future__ import annotations

import math

from fastapi import APIRouter, HTTPException, Request

from .. import clustering
from ..db import fetch_all
from ..filters import parse_filters
from ..serializers import clamp, ok

router = APIRouter()

default_cluster_threshold = 0.6
default_cluster_max_questions = 2_000
max_cluster_questions = 20_000


@router.get("/cluster")
def cluster_questions(request: Request):
    qp = request.query_params
    filters = parse_filters(qp)
    try:
        threshold = float(qp.get("threshold", default_cluster_threshold))
    except (TypeError, ValueError):
        raise HTTPException(
            400, "threshold must be a finite number between -1 and 1"
        ) from None
    if not math.isfinite(threshold) or not -1 <= threshold <= 1:
        raise HTTPException(400, "threshold must be a finite number between -1 and 1")
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
