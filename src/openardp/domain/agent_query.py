"""Pure query planning, lexical coverage, snippets and quote matching for agent access.

Questions are reduced to content terms: English and German stop words are dropped and
inflected words become prefix terms of a light suffix-stripping stem. Quote matching
tolerates typographic quotes, dashes, whitespace and Markdown emphasis, and reports how
much normalization a match needed so that callers never overstate exactness.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum

MAX_QUERY_TERMS = 16
MIN_PREFIX_STEM = 4
MAX_QUOTE_CHARACTERS = 4_000
MAX_FRAGMENT_GAP = 5_000
DEFAULT_SNIPPET_CHARACTERS = 240

_WORD = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*", re.UNICODE)
_PHRASE = re.compile(r'"([^"]{1,512})"')
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…|\[\s*(?:\.\.\.|…)\s*\])\s*")
_QUOTE_CHARACTERS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2032": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u00ab": '"',
    "\u00bb": '"',
    "\u2039": "'",
    "\u203a": "'",
    "\u2033": '"',
}
_DASHES = frozenset("\u2010\u2011\u2012\u2013\u2014\u2015\u2212")
_INVISIBLE = frozenset("\u00ad\u200b\u200c\u200d\u2060\ufeff")
_MARKUP = frozenset("*_#|>`~")

_ENGLISH_WORDS = """
    a about above after again against all also am an and any are as at be because been
    before being below between both but by can could did do does doing down during each few
    for from further had has have having he her here hers herself him himself his how i if
    in into is it its itself just me more most my myself no nor not now of off on once only
    or other our ours ourselves out over own same she should so some such than that the their
    theirs them themselves then there these they this those through to too under until up
    very was we were what when where which while who whom why will with would you your yours
    yourself yourselves document documents show tell find give list please does describe
    explain mentioned mention say says said according must shall should may might often"""
_GERMAN_WORDS = """
    aber alle allem allen aller alles als also am an ander andere anderem anderen anderer
    anderes auch auf aus bei bin bis bist da damit dann das dass dein deine dem den der des
    dessen dich die dies diese diesem diesen dieser dieses dir doch dort du durch ein eine
    einem einen einer eines er es etwas euch euer eure für gegen gewesen hab habe haben hat
    hatte hier hin hinter ich ihm ihn ihnen ihr ihre im in indem ins ist jede jedem jeden
    jeder jedes jene jetzt kann kein keine können könnte machen man mein meine mich mir mit
    muss musste nach nicht nichts noch nun nur ob oder ohne sehr sein seine sich sie sind so
    solche soll sollte sondern sonst über um und uns unser unter viel vom von vor war waren
    warum was weil welche welchem welchen welcher welches wenn wer werde werden wie wieder
    will wir wird wo wollen worden würde zu zum zur zwar zwischen dokument dokumente zeige
    nenne gibt gib steht stehen laut oft wann wieso weshalb wofür darf dürfen sollen"""


_QUESTION_WORDS = frozenset(
    [
        "how",
        "what",
        "why",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "whose",
        "wie",
        "was",
        "warum",
        "wann",
        "wo",
        "welche",
        "welcher",
        "welches",
        "wer",
        "wieso",
        "weshalb",
    ]
)


def is_question(query: str) -> bool:
    """Return whether a query reads as a natural-language question."""
    words = _WORD.findall(query)
    return query.rstrip().endswith("?") or bool(words and words[0].casefold() in _QUESTION_WORDS)


def fold(text: str) -> str:
    """Case-fold and strip diacritics for tolerant lexical comparison."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return stripped.casefold()


STOPWORDS = frozenset(fold(word) for word in (_ENGLISH_WORDS + _GERMAN_WORDS).split())

# Longest suffix first; stems shorter than MIN_PREFIX_STEM keep the whole word.
_SUFFIXES = (
    "ationen",
    "ations",
    "keiten",
    "heiten",
    "ungen",
    "ation",
    "ments",
    "ities",
    "ingen",
    "ische",
    "ment",
    "ness",
    "ings",
    "keit",
    "heit",
    "lich",
    "isch",
    "ung",
    "ing",
    "ies",
    "ied",
    "ity",
    "ers",
    "ern",
    "ens",
    "ed",
    "es",
    "en",
    "er",
    "ly",
    "s",
    "e",
    "n",
)


class MatchLevel(StrEnum):
    """How much normalization a verified quote needed."""

    EXACT = "exact"
    NORMALIZED = "normalized"


@dataclass(frozen=True, slots=True)
class QueryTerm:
    """One folded search term, prefix-expanded or an exact phrase."""

    text: str
    prefix: bool = False
    phrase: bool = False

    def fts(self) -> str:
        """Render this term as one quoted FTS5 string, optionally prefix-marked."""
        escaped = self.text.replace('"', '""')
        return f'"{escaped}"*' if self.prefix else f'"{escaped}"'


@dataclass(frozen=True, slots=True)
class QueryPlan:
    """Deterministic content terms of one agent question or keyword query."""

    terms: tuple[QueryTerm, ...]

    def match_expression(self) -> str:
        """Return one disjunctive FTS5 expression suitable as a bound parameter."""
        return " OR ".join(term.fts() for term in self.terms)


@dataclass(frozen=True, slots=True)
class QuoteLocation:
    """Character span of a verified quote inside the searched text."""

    start: int
    end: int
    level: MatchLevel


def stem(word: str) -> tuple[str, bool]:
    """Return a folded stem and whether it should be matched as a prefix."""
    folded = fold(word)
    if any(char.isdigit() for char in folded) or len(folded) < MIN_PREFIX_STEM + 1:
        return folded, False
    for suffix in _SUFFIXES:
        if folded.endswith(suffix) and len(folded) - len(suffix) >= MIN_PREFIX_STEM:
            return folded[: -len(suffix)], True
    return folded, True


def plan_query(query: str) -> QueryPlan:
    """Reduce a question or keyword query to bounded deterministic content terms."""
    terms: list[QueryTerm] = []
    seen: set[tuple[str, bool, bool]] = set()

    def add(term: QueryTerm) -> None:
        key = (term.text, term.prefix, term.phrase)
        if term.text and key not in seen and len(terms) < MAX_QUERY_TERMS:
            seen.add(key)
            terms.append(term)

    for phrase in _PHRASE.findall(query):
        words = [fold(word) for word in _WORD.findall(phrase)]
        if len(words) == 1:
            add(QueryTerm(words[0]))
        elif words:
            add(QueryTerm(" ".join(words), phrase=True))
    remainder = _PHRASE.sub(" ", query)
    words = _WORD.findall(remainder)
    content = [word for word in words if fold(word) not in STOPWORDS]
    for word in content or words:
        text, prefix = stem(word)
        add(QueryTerm(text, prefix=prefix))
    return QueryPlan(terms=tuple(terms))


def _folded_words(text: str) -> list[str]:
    return [fold(word) for word in _WORD.findall(text)]


def _term_positions(folded_words: Sequence[str], term: QueryTerm) -> list[int]:
    if term.phrase:
        parts = term.text.split(" ")
        width = len(parts)
        return [
            index
            for index in range(len(folded_words) - width + 1)
            if list(folded_words[index : index + width]) == parts
        ]
    if term.prefix:
        return [index for index, word in enumerate(folded_words) if word.startswith(term.text)]
    return [index for index, word in enumerate(folded_words) if word == term.text]


def term_coverage(text: str, plan: QueryPlan) -> int:
    """Count how many distinct plan terms occur in one text."""
    words = _folded_words(text)
    return sum(1 for term in plan.terms if _term_positions(words, term))


def best_snippet(
    text: str,
    plan: QueryPlan,
    *,
    max_characters: int = DEFAULT_SNIPPET_CHARACTERS,
) -> str:
    """Return a compact single-line window around the densest run of matched terms."""
    flat = " ".join(_COMMENT.sub(" ", text).split())
    if len(flat) <= max_characters:
        return flat
    spans = [match.span() for match in _WORD.finditer(flat)]
    words = [fold(flat[start:end]) for start, end in spans]
    hits = sorted({position for term in plan.terms for position in _term_positions(words, term)})
    if not hits:
        return _clip(flat, 0, max_characters)
    best_start = spans[hits[0]][0]
    best_count = 0
    for index, position in enumerate(hits):
        start = spans[position][0]
        count = sum(1 for other in hits[index:] if spans[other][0] < start + max_characters)
        if count > best_count:
            best_start, best_count = start, count
    start = max(0, best_start - max_characters // 5)
    return _clip(flat, start, start + max_characters)


def _clip(text: str, start: int, end: int) -> str:
    end = min(len(text), end)
    if start > 0:
        space = text.find(" ", start)
        start = space + 1 if 0 <= space < start + 20 else start
    if end < len(text):
        space = text.rfind(" ", start, end)
        end = space if space > start + 20 else end
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def normalize_for_match(text: str, *, loose: bool) -> tuple[str, list[int]]:
    """Normalize text for quote matching and map each output character to its source."""
    output: list[str] = []
    mapping: list[int] = []
    pending_space: int | None = None
    for index, char in enumerate(text):
        for piece in _normalized_pieces(char, loose=loose):
            if piece.isspace():
                if output and pending_space is None:
                    pending_space = index
                continue
            if pending_space is not None:
                output.append(" ")
                mapping.append(pending_space)
                pending_space = None
            output.append(piece)
            mapping.append(index)
    return "".join(output), mapping


def _normalized_pieces(char: str, *, loose: bool) -> str:
    if char in _INVISIBLE:
        return ""
    if char in _QUOTE_CHARACTERS:
        char = _QUOTE_CHARACTERS[char]
    elif char in _DASHES:
        char = "-"
    elif char == "…":
        char = "..."
    else:
        char = unicodedata.normalize("NFKC", char)
    if not loose:
        return char
    pieces: list[str] = []
    for piece in fold(char):
        if piece in _MARKUP or unicodedata.category(piece).startswith("P"):
            pieces.append(" ")
        else:
            pieces.append(piece)
    return "".join(pieces)


def quote_fragments(quote: str) -> tuple[str, ...]:
    """Split a quote on ellipses into ordered non-empty fragments."""
    trimmed = quote.strip().strip("\"'\u201c\u201d\u201e\u2018\u2019\u00ab\u00bb").strip()
    return tuple(part.strip() for part in _ELLIPSIS.split(trimmed) if part.strip())


def locate_quote(text: str, quote: str) -> QuoteLocation | None:
    """Find a quote, including ellipsis gaps, first exactly, then normalized."""
    fragments = quote_fragments(quote)
    if not fragments:
        return None
    for level in (MatchLevel.EXACT, MatchLevel.NORMALIZED):
        located = _locate_fragments(text, fragments, loose=level is MatchLevel.NORMALIZED)
        if located is not None:
            return QuoteLocation(start=located[0], end=located[1], level=level)
    return None


def _locate_fragments(
    text: str,
    fragments: Sequence[str],
    *,
    loose: bool,
) -> tuple[int, int] | None:
    haystack, mapping = normalize_for_match(text, loose=loose)
    needles = [normalize_for_match(fragment, loose=loose)[0].strip() for fragment in fragments]
    if not all(needles):
        return None
    start_at = 0
    while True:
        first = haystack.find(needles[0], start_at)
        if first < 0:
            return None
        cursor = first + len(needles[0])
        complete = True
        for needle in needles[1:]:
            found = haystack.find(needle, cursor)
            if found < 0 or found - cursor > MAX_FRAGMENT_GAP:
                complete = False
                break
            cursor = found + len(needle)
        if complete:
            return mapping[first], mapping[cursor - 1] + 1
        start_at = first + 1


def closest_similarity(text: str, quote: str) -> tuple[float, int]:
    """Return the best loose similarity of a quote against windows of one text."""
    needle = normalize_for_match(" ".join(quote_fragments(quote)), loose=True)[0].strip()
    haystack, mapping = normalize_for_match(text, loose=True)
    if not needle or not haystack:
        return 0.0, 0
    width = len(needle)
    if len(haystack) <= width:
        return SequenceMatcher(None, needle, haystack).ratio(), 0
    step = max(1, width // 4)
    best = (0.0, 0)
    for start in range(0, len(haystack) - width + step, step):
        window = haystack[start : start + width]
        ratio = SequenceMatcher(None, needle, window).ratio()
        if ratio > best[0]:
            best = (ratio, mapping[min(start, len(mapping) - 1)])
    return best


__all__ = [
    "DEFAULT_SNIPPET_CHARACTERS",
    "MAX_QUERY_TERMS",
    "MAX_QUOTE_CHARACTERS",
    "STOPWORDS",
    "MatchLevel",
    "QueryPlan",
    "QueryTerm",
    "QuoteLocation",
    "best_snippet",
    "closest_similarity",
    "fold",
    "is_question",
    "locate_quote",
    "normalize_for_match",
    "plan_query",
    "quote_fragments",
    "stem",
    "term_coverage",
]
