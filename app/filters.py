from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fastapi import HTTPException

sort_orders = ("newest", "oldest", "random")

_FILTER_COLUMNS = {
    "subject": "subject",
    "chapter": "chapter",
    "topic": "topic",
    "difficulty": "difficulty",
    "type": "type",
    "group": "chapter_group",
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class QuestionFilters:
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    type: str | None = None
    group: str | None = None
    year: int | None = None
    q: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def where(self, prefix: str = "") -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []
        for field, col in _FILTER_COLUMNS.items():
            value = getattr(self, field)
            if value is not None:
                clauses.append(f"{prefix}{col} = %s")
                params.append(value)
        if self.year is not None:
            clauses.append(f"{prefix}year = %s")
            params.append(self.year)
        if self.q is not None:
            # The human-readable columns the question bank shows on each row.
            # Escape LIKE wildcards so user input is matched literally.
            searchable = ("chapter", "topic", "paper_title", "exam", "exam_group")
            clauses.append(
                "("
                + " or ".join(f"{prefix}{col} ilike %s escape '\\'" for col in searchable)
                + ")"
            )
            params.extend([f"%{_escape_like(self.q)}%"] * len(searchable))
        return (" where " + " and ".join(clauses)) if clauses else "", params


def parse_filters(qp) -> QuestionFilters:
    def _opt(name: str) -> str | None:
        return qp.get(name) or None

    year = qp.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise HTTPException(400, "year must be an integer") from None
    return QuestionFilters(
        subject=_opt("subject"),
        chapter=_opt("chapter"),
        topic=_opt("topic"),
        difficulty=_opt("difficulty"),
        type=_opt("type"),
        group=_opt("group"),
        year=year,
        q=qp.get("q") or None,
    )


def order_by(order: str) -> str:
    if order == "newest":
        return "order by year desc, exam_date desc nulls last, id desc"
    if order == "oldest":
        return "order by year asc, exam_date asc nulls first, id asc"
    return "order by random()"


def seeded_order_by(seed: str) -> str:
    """Order by `md5(id || seed)`: a fresh shuffle per seed, stable within one."""
    return "order by md5(id::text || %s)"
