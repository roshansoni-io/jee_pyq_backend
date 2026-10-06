from __future__ import annotations

import json
from typing import Any

_minor_words = frozenset({
    "and", "of", "in", "the", "to", "for",
    "a", "an", "with", "on", "by", "is", "at",
})
_acronyms = frozenset({"jee", "ac", "dc"})


def humanize(slug: Any) -> str:
    words = str(slug).replace("-", " ").split()
    out: list[str] = []
    for index, word in enumerate(words):
        if word in _acronyms:
            out.append(word.upper())
        elif index > 0 and word in _minor_words:
            out.append(word)
        else:
            out.append(word.title())
    return " ".join(out)


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"data": data}
    if meta:
        body["meta"] = meta
    return body


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def _json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


def question_summary(q: dict) -> dict[str, Any]:
    return {
        "id": q["id"],
        "exam": humanize(q["exam"]),
        "exam_group": humanize(q["exam_group"]),
        "subject": q["subject"],
        "chapter": q["chapter"],
        "chapter_group": q["chapter_group"] or None,
        "year": q["year"],
        "paper_title": q["paper_title"],
        "difficulty": q["difficulty"],
        "topic": q["topic"],
        "type": q["type"],
        "exam_date": None if q["exam_date"] is None else str(q["exam_date"]),
        "is_out_of_syllabus": q["is_out_of_syllabus"],
        "is_bonus": q["is_bonus"],
    }


def question_detail(q: dict) -> dict[str, Any]:
    detail = question_summary(q)
    detail.update({
        "question": q["question"],
        "options": _json(q["options"]),
        "correct_options": _json(q["correct_options"]),
        "answer": _json(q["answer"]),
        "explanation": q["explanation"],
        "is_img_question": q["is_img_question"],
        "is_img_explanation": q["is_img_explanation"],
        "is_img_option": _json(q["is_img_option"]),
    })
    return detail


def subject_payload(s: dict) -> dict[str, Any]:
    return {
        "id": s["id"],
        "name": humanize(s["id"]),
        "chapter_count": s["chapter_count"],
        "question_count": s["question_count"],
    }


def chapter_payload(c: dict) -> dict[str, Any]:
    return {
        "id": c["id"],
        "name": humanize(c["id"]),
        "question_count": c["question_count"],
        "topic_count": c["topic_count"],
    }


def topic_payload(t: dict) -> dict[str, Any]:
    return {"id": t["id"], "name": humanize(t["id"]), "question_count": t["question_count"]}
