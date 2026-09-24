"""Helpers for comparing sanitized CLI error envelopes independent of fixed hints."""

from __future__ import annotations

from typing import Any


def without_hint(error: Any) -> Any:
    """Return an error body without its optional fixed operator hint."""
    if isinstance(error, dict):
        return {key: value for key, value in error.items() if key != "hint"}
    return error
