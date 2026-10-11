"""Shared bounded pagination helpers for database backed list endpoints."""


def page_args(values, default_size=50, max_size=100):
    try:
        page = max(1, int(values.get("page", 1)))
        size = min(max_size, max(1, int(values.get("per_page", default_size))))
    except (TypeError, ValueError):
        page, size = 1, default_size
    return page, size, (page - 1) * size
