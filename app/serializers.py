from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

_minor_words = frozenset({
    "and", "of", "in", "the", "to", "for",
    "a", "an", "with", "on", "by", "is", "at",
})
_acronyms = frozenset({"jee", "ac", "dc"})


@lru_cache(maxsize=2048)
def _humanize_str(slug: str) -> str:
    words = slug.replace("-", " ").split()
    out: list[str] = []
    for index, word in enumerate(words):
        if word in _acronyms:
            out.append(word.upper())
        elif index > 0 and word in _minor_words:
            out.append(word)
        else:
            out.append(word.title())
    return " ".join(out)


def humanize(slug: Any) -> str:
    """Title-case a slug, memoised on the input string."""
    return _humanize_str(str(slug))


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
        "year": q["year"],
        "exam_date": q["exam_date"].isoformat() if q["exam_date"] else None,
        "shift": q["shift"],
        "paper_title": q["paper_title"],
        "difficulty": q["difficulty"],
        "topic": topic_payload(q["topic"]),
        "type": q["type"],
    }


def question_detail(q: dict) -> dict[str, Any]:
    detail = question_summary(q)
    detail.update({
        "is_bonus": q["is_bonus"],
        "question": q["question"],
        "options": _json(q["options"]),
        "correct_options": _json(q["correct_options"]),
        "answer": _json(q["answer"]),
        "explanation": q["explanation"],
    })
    return detail


def subject_payload(s: dict) -> dict[str, Any]:
    return {"id": s["id"], "name": humanize(s["id"])}


def chapter_payload(c: dict) -> dict[str, Any]:
    return {
        "id": c["id"],
        "name": humanize(c["id"]),
        "chapter_number": c["chapter_number"],
        "group": humanize(c["chapter_group"]) if c["chapter_group"] else None,
        "question_count": c["question_count"],
    }


def topic_payload(topic_id: str | None) -> dict[str, str] | None:
    if not topic_id:
        return None
    return {"id": topic_id, "name": humanize(topic_id)}
