"""Deterministic hostile and offline visual interpreter test doubles."""

from __future__ import annotations

import socket

from openardp.domain.evidence import ProviderRecipe
from openardp.domain.visual import VisualInterpretationRequest, VisualInterpretationResult


class FixtureInterpreter:
    """Return configured bounded data or attempt one forbidden network operation."""

    def __init__(
        self,
        *,
        config_digit: str = "1",
        text: str = "synthetic visual data",
        confidence_ppm: int | None = 750_000,
        network_attempt: bool = False,
    ) -> None:
        """Configure deterministic provider facts and one optional hostile behavior."""
        self._provider = ProviderRecipe(
            name="synthetic-visual-provider",
            version="1.0.0",
            profile="offline-fixture",
            profile_version="1.0.0",
            config_hash="sha256:" + config_digit * 64,
        )
        self.text = text
        self.confidence_ppm = confidence_ppm
        self.network_attempt = network_attempt
        self.calls = 0

    @property
    def provider(self) -> ProviderRecipe:
        """Return the exact deterministic fixture recipe."""
        return self._provider

    def interpret(
        self,
        request: VisualInterpretationRequest,
        crop_png: bytes,
    ) -> VisualInterpretationResult:
        """Treat crop bytes as input data and return one configured result."""
        self.calls += 1
        assert crop_png.startswith(b"\x89PNG")
        if self.network_attempt:
            socket.socket()
        return VisualInterpretationResult(
            operation=request.operation,
            text=self.text,
            confidence_ppm=self.confidence_ppm,
            warning_codes=("low_confidence",) if self.confidence_ppm == 1 else (),
        )


__all__ = ["FixtureInterpreter"]
