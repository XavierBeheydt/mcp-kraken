"""Shared helpers for tool modules."""

from __future__ import annotations

from typing import Any


def drop_none(d: dict[str, Any]) -> dict[str, Any]:
    """Strip keys whose value is `None`. Kraken expects the field to be
    absent rather than null.
    """
    return {k: v for k, v in d.items() if v is not None}


def csv(values: list[str] | None) -> str | None:
    """Render a list as a comma-separated string, or None for omission."""
    if values is None:
        return None
    return ",".join(values)
