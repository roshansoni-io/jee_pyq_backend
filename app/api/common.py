from __future__ import annotations

from ..serializers import clamp


def limit_offset(query_params, default_size: int, max_size: int) -> tuple[int, int]:
    try:
        limit = int(query_params.get("limit", default_size))
    except (TypeError, ValueError):
        limit = default_size
    try:
        offset = int(query_params.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    return clamp(limit, 0, max_size), max(0, offset)
