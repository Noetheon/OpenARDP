"""Ranked profile identity and historical classifier compatibility tests."""

from __future__ import annotations

import pytest

from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.services.context_compiler import context_algorithm_identity
from openardp.services.context_relevance import (
    RANKING_ALGORITHM_NAME,
    RELEVANCE_ALGORITHM_NAME,
)


def test_combined_identity_is_distinct_and_historical_identities_are_frozen() -> None:
    """F027 composes over, rather than silently replacing, the F026 identity."""
    legacy = context_algorithm_identity()
    relevance = context_algorithm_identity(RelevancePolicy())
    ranked = context_algorithm_identity(RelevancePolicy(), LexicalAllocationPolicy())

    assert legacy.name == "openardp.lexical-context"
    assert relevance.name == RELEVANCE_ALGORITHM_NAME
    assert ranked.name == RANKING_ALGORITHM_NAME
    assert len({legacy.config_hash, relevance.config_hash, ranked.config_hash}) == 3


def test_allocation_without_relevance_is_rejected() -> None:
    """Diversification cannot bypass the minimum-relevance safety floor."""
    with pytest.raises(ValueError, match="requires a relevance policy"):
        context_algorithm_identity(None, LexicalAllocationPolicy())
