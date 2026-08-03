"""Security boundaries for provider-free ranking and allocation."""

from __future__ import annotations

from openardp.domain.context_ranking import LexicalAllocationPolicy, allocate_lexical_candidates
from tests.domain.test_context_ranking import _candidate


def test_allocator_emits_only_body_free_reason_codes() -> None:
    """Duplicate and quota decisions do not copy source bodies or host paths."""
    first = _candidate(1, 1, body=9)
    duplicate = _candidate(2, 2, body=9)
    over_quota = _candidate(1, 3, body=3)

    result = allocate_lexical_candidates(
        (first, duplicate, over_quota),
        LexicalAllocationPolicy(max_per_document=1),
    )
    reasons = [reason for _candidate, reason in result.rejected]
    assert reasons == ["duplicate_content_candidate", "source_quota_exceeded"]
    assert all("/" not in reason and "alpha" not in reason for reason in reasons)


def test_allocator_does_not_create_candidates_for_missing_sources() -> None:
    """A single eligible source remains single-source rather than being padded."""
    only = _candidate(1, 1)

    result = allocate_lexical_candidates((only,), LexicalAllocationPolicy())

    assert result.ordered == (only,)
    assert result.rejected == ()
