"""Immutable identity model for one SQLite schema migration."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Migration:
    """One append-only ordered catalog schema revision."""

    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        """Return a stable SHA-256 identity over revision metadata and statements."""
        payload = (
            f"openardp-sqlite-migration-v1\n{self.version}\n{self.name}\n"
            + "\n-- statement --\n".join(self.statements)
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()


__all__ = ["Migration"]
