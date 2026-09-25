"""Pure agent query planning, coverage, snippets and quote matching."""

from __future__ import annotations

import pytest

from openardp.domain.agent_query import (
    MAX_QUERY_TERMS,
    MatchLevel,
    QueryPlan,
    QueryTerm,
    best_snippet,
    closest_similarity,
    fold,
    locate_quote,
    normalize_for_match,
    plan_query,
    quote_fragments,
    stem,
    term_coverage,
)


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("recommendations", ("recommend", True)),
        ("Empfehlungen", ("empfehl", True)),
        ("training", ("train", True)),
        ("data", ("data", False)),
        ("NASA", ("nasa", False)),
        ("2020", ("2020", False)),
        ("strategic", ("strategic", True)),
        ("Überblick", ("uberblick", True)),
    ],
)
def test_stem_keeps_short_words_exact_and_prefixes_inflections(
    word: str,
    expected: tuple[str, bool],
) -> None:
    """Strip one known suffix, keep stems of at least four letters, fold diacritics."""
    assert stem(word) == expected


def test_plan_drops_english_and_german_stop_words() -> None:
    """Reduce questions in either language to content terms."""
    english = plan_query("Why are embeddings optional?")
    assert [term.text for term in english.terms] == ["embedd", "optional"]
    german = plan_query("Welche Empfehlungen gibt es für das Training?")
    assert [term.text for term in german.terms] == ["empfehl", "train"]
    assert english.match_expression() == '"embedd"* OR "optional"*'


def test_plan_keeps_phrases_deduplicates_and_bounds_terms() -> None:
    """Treat quoted text as one phrase and never exceed the term bound."""
    plan = plan_query('"reference weight" weight weights "single"')
    assert plan.terms[0] == QueryTerm("reference weight", phrase=True)
    assert plan.terms[1] == QueryTerm("single")
    assert [term.text for term in plan.terms].count("weight") == 1
    words = " ".join(f"word{index}xyz" for index in range(40))
    assert len(plan_query(words).terms) == MAX_QUERY_TERMS
    assert [term.text for term in plan_query("what is this").terms] == ["what", "is", "this"]
    assert plan_query("?!").terms == ()


def test_fts_terms_escape_quotes() -> None:
    """Render every term as a quoted FTS5 string."""
    assert QueryTerm('say "hi"').fts() == '"say ""hi"""'
    assert QueryPlan(terms=(QueryTerm("ab", prefix=True),)).match_expression() == '"ab"*'


def test_term_coverage_counts_distinct_prefix_exact_and_phrase_terms() -> None:
    """Count each matched term once across prefix, exact and phrase forms."""
    plan = plan_query('train "reference weight" NASA')
    assert term_coverage("Trained staff check the reference weight at NASA.", plan) == 3
    assert term_coverage("The weight reference differs.", plan) == 0
    assert fold("Äpfel") == "apfel"


def test_snippet_centres_on_matches_and_strips_comments() -> None:
    """Return short texts whole and window long texts around the densest matches."""
    plan = plan_query("calibration")
    assert best_snippet("<!-- image --> Short   text", plan) == "Short text"
    long_text = ("filler " * 80) + "The calibration step comes first. " + ("tail " * 80)
    snippet = best_snippet(long_text, plan, max_characters=80)
    assert "calibration" in snippet and snippet.startswith("…") and snippet.endswith("…")
    assert best_snippet("x " * 200, plan, max_characters=40).endswith("…")


def test_normalization_maps_every_character_to_its_source() -> None:
    """Collapse whitespace and unify quotes while keeping a source offset per character."""
    text = "A  “quoted”—text­!"
    normalized, mapping = normalize_for_match(text, loose=False)
    assert normalized == 'A "quoted"-text!'
    assert text[mapping[normalized.index("q")]] == "q"
    loose, _ = normalize_for_match("**Bold** Text, here.", loose=True)
    assert loose == "bold text here"


def test_locate_quote_reports_exact_then_normalized_matches() -> None:
    """Prefer exact matches and flag case, spacing or formatting differences."""
    text = "Intro.\nEngage **humans** further to improve AI training.\nEnd."
    exact = locate_quote(text, "improve AI training.")
    assert exact is not None and exact.level is MatchLevel.EXACT
    assert text[exact.start : exact.end] == "improve AI training."
    normalized = locate_quote(text, "engage humans further")
    assert normalized is not None and normalized.level is MatchLevel.NORMALIZED
    assert locate_quote(text, "humans must decide") is None
    assert locate_quote(text, "  ") is None


def test_locate_quote_follows_ellipsis_fragments_in_order() -> None:
    """Match fragments separated by an ellipsis only in order and within a bound gap."""
    text = "Alpha beta gamma. Delta epsilon. Zeta eta."
    assert quote_fragments("“Alpha beta … Zeta eta”") == ("Alpha beta", "Zeta eta")
    assert locate_quote(text, "Alpha beta ... Zeta eta") is not None
    assert locate_quote(text, "Zeta eta ... Alpha beta") is None
    far = "Alpha beta " + ("x" * 6_000) + " Zeta eta"
    assert locate_quote(far, "Alpha beta [...] Zeta eta") is None


def test_closest_similarity_finds_the_paraphrased_region() -> None:
    """Score a near quote highly and an unrelated quote low."""
    text = "Most participants agreed that AI is a tool to assist human planners."
    near, offset = closest_similarity(text, "AI is a tool that assists human planners")
    far, _ = closest_similarity(text, "Quarterly revenue grew by nine percent")
    assert near > 0.8 > far
    assert offset >= 0
    assert closest_similarity("", "quote") == (0.0, 0)
    assert closest_similarity("tiny", "a much longer quote than text")[0] > 0
