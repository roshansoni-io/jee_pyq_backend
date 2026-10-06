from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

sort_orders = ("newest", "oldest", "random")

_FILTER_COLUMNS = {
    "subject": "subject",
    "chapter": "chapter",
    "topic": "topic",
    "difficulty": "difficulty",
    "type": "type",
    "group": "chapter_group",
}


@dataclass(frozen=True)
class QuestionFilters:
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    type: str | None = None
    group: str | None = None
    year: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def where(self) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []
        for field, col in _FILTER_COLUMNS.items():
            value = getattr(self, field)
            if value is not None:
                clauses.append(f"{col} = %s")
                params.append(value)
        if self.year is not None:
            clauses.append("year = %s")
            params.append(self.year)
        return (" where " + " and ".join(clauses)) if clauses else "", params


def parse_filters(qp) -> QuestionFilters:
    return QuestionFilters(
        subject=qp.get("subject"),
        chapter=qp.get("chapter"),
        topic=qp.get("topic"),
        difficulty=qp.get("difficulty"),
        type=qp.get("type"),
        group=qp.get("group"),
        year=int(qp["year"]) if qp.get("year") is not None else None,
    )


def order_by(order: str) -> str:
    if order == "newest":
        return "order by year desc, exam_date desc nulls last, id desc"
    if order == "oldest":
        return "order by year asc, exam_date asc nulls first, id asc"
    return "order by random()"
