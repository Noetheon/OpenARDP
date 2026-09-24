"""Compact, token-efficient text renderings of agent results for CLI and MCP.

Renderings name files, pages and lines instead of hashes; identifiers appear once as
short handles. Document text is shown verbatim inside fences or as indented snippets and
remains untrusted data. Terminal control characters are escaped.
"""

from __future__ import annotations

import re

from openardp.domain.agent_query import MatchLevel
from openardp.domain.agent_results import (
    AddReport,
    AddStatus,
    DocsResult,
    DocumentRef,
    ExportReport,
    FindResult,
    Freshness,
    OutlineResult,
    ReadResult,
    VerifyResult,
    VerifyStatus,
)
from openardp.domain.agent_text import PageLabel
from openardp.services.agent_texts import media_kind

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f‪-‮⁦-⁩]")
_BACKTICKS = re.compile(r"`{3,}")

CHANGED_NOTICE = (
    "Warning: the source file changed after import; results show the imported version. "
    "Run `openardp add <path>` to update."
)
MISSING_NOTICE = "Warning: the source file is missing; results show the imported version."


def safe(text: str) -> str:
    """Escape terminal control characters while keeping newlines and tabs."""
    return _CONTROL.sub(lambda match: f"\\u{ord(match.group(0)):04x}", text)


def tokens(count: int) -> str:
    """Format an approximate token count compactly."""
    if count >= 1_000_000:
        return f"≈{count / 1_000_000:.1f}M"
    if count >= 10_000:
        return f"≈{count / 1_000:.0f}k"
    if count >= 1_000:
        return f"≈{count / 1_000:.1f}k"
    return f"≈{count}"


def short_version(version_id: str) -> str:
    """Return the first eight hex digits of a SHA-256 version identifier."""
    return version_id.removeprefix("sha256:")[:8]


def location(document: DocumentRef, line_start: int, line_end: int, page: int | None) -> str:
    """Render one citable location: ``file:12-14`` or ``file p.3 (L40-52)``."""
    lines = f"{line_start}" if line_start == line_end else f"{line_start}-{line_end}"
    if page is None:
        return f"{safe(document.label)}:{lines}"
    page_text = f"slide {page}" if document.page_label is PageLabel.SLIDE else f"p.{page}"
    return f"{safe(document.label)} {page_text} (L{lines})"


def short_heading(path: str, *, levels: int = 2) -> str:
    """Keep the innermost heading levels of a ``A > B > C`` path."""
    parts = path.split(" > ")
    return " > ".join(parts[-levels:])


def render_docs(result: DocsResult) -> str:
    """Render the prepared document list, one compact line per document."""
    if not result.documents and not result.pending:
        return "No documents yet. Add some with: openardp add <files or folders>"
    lines = [f"{len(result.documents)} documents, {tokens(result.total_tokens)} tokens total."]
    for entry in result.documents:
        size = (
            f"{entry.page_count} {'slides' if entry.page_label is PageLabel.SLIDE else 'pages'}"
            if entry.page_count
            else f"{entry.line_count} lines"
        )
        line = (
            f"[{entry.short_id}] {safe(entry.label)} — {media_kind(entry.media_type)}, {size}, "
            f"{tokens(entry.token_estimate)} tokens"
        )
        if entry.freshness is Freshness.CHANGED:
            line += " — source changed since import"
        elif entry.freshness is Freshness.MISSING:
            line += " — source file missing"
        lines.append(line)
    if result.pending:
        names = ", ".join(safe(item.label) for item in result.pending[:10])
        more = f" and {len(result.pending) - 10} more" if len(result.pending) > 10 else ""
        lines.append(
            f"Not prepared ({len(result.pending)}): {names}{more}. Run: openardp add <path>"
        )
    return "\n".join(lines)


def render_find(result: FindResult) -> str:
    """Render ranked hits as citable locations with indented snippets."""
    if not result.query_terms:
        return "The query has no searchable words."
    terms = ", ".join(result.query_terms)
    if not result.hits:
        return (
            f"No passages match {terms}. Try other or fewer keywords, synonyms, "
            "or the document's language."
        )
    lines = [f"{len(result.hits)} of {result.candidates} matching passages for {terms}:"]
    for position, hit in enumerate(result.hits, start=1):
        heading = f" — § {safe(short_heading(hit.heading))}" if hit.heading else ""
        lines.append(
            f"{position}. {location(hit.document, hit.line_start, hit.line_end, hit.page)}"
            f" [{hit.document.short_id}] {tokens(hit.token_estimate)} tok{heading}"
        )
        lines.append(f"   {safe(hit.snippet)}")
    if result.changed_sources:
        lines.append(
            "Changed since import: " + ", ".join(safe(label) for label in result.changed_sources)
        )
    lines.append("Next: read a hit's lines or page for full text; verify quotes before citing.")
    return "\n".join(lines)


def render_read(result: ReadResult, *, line_numbers: bool = True) -> str:
    """Render one excerpt with a one-line header and a fenced, numbered body."""
    unit = "slide" if result.document.page_label is PageLabel.SLIDE else "page"
    page_part = ""
    if result.pages:
        first, last = result.pages[0], result.pages[-1]
        page_part = f" · {unit} {first}" if first == last else f" · {unit}s {first}-{last}"
    header = (
        f"{safe(result.document.label)}{page_part} · lines {result.line_start}-{result.line_end}"
        f" of {result.total_lines} · {tokens(result.token_estimate)} tokens"
        f" · version {short_version(result.document.version_id)}"
    )
    body_lines = result.text.split("\n") if result.text else []
    if line_numbers:
        body = "\n".join(
            f"{result.line_start + offset}\t{safe(line)}" for offset, line in enumerate(body_lines)
        )
    else:
        body = safe(result.text)
    fence = _fence_for(body)
    parts = [header, f"{fence}text", body, fence]
    if result.truncated and result.next_line is not None:
        parts.append(f"Truncated at the token limit; continue with lines {result.next_line}-")
    notice = _freshness_notice(result.freshness)
    if notice:
        parts.append(notice)
    return "\n".join(parts)


def render_outline(result: OutlineResult) -> str:
    """Render headings or pages with line numbers and section sizes."""
    document = result.document
    unit = "slides" if document.page_label is PageLabel.SLIDE else "pages"
    size = (
        f"{document.page_count} {unit}" if document.page_count else f"{document.line_count} lines"
    )
    lines = [
        f"{safe(document.label)} — {media_kind(document.media_type)}, {size}, "
        f"{tokens(document.token_estimate)} tokens, version {short_version(document.version_id)}"
    ]
    if not result.entries:
        lines.append("No headings or pages; read by line range.")
    for entry in result.entries:
        marker = "#" * entry.level + " " if entry.level else ""
        page = ""
        if entry.page is not None:
            page = f" slide {entry.page}" if unit == "slides" else f" p.{entry.page}"
        size = tokens(entry.token_estimate)
        lines.append(f"L{entry.line}{page} {marker}{safe(entry.text)} ({size})")
    if result.truncated:
        lines.append("Outline truncated; read by line range for the rest.")
    notice = _freshness_notice(document.freshness)
    if notice:
        lines.append(notice)
    return "\n".join(lines)


def render_verify(result: VerifyResult) -> str:
    """Render a verification verdict with exact version-pinned locations."""
    if result.status is VerifyStatus.VERIFIED:
        lines = []
        for match in result.matches:
            how = (
                "exact"
                if match.level is MatchLevel.EXACT
                else "ignoring case, spacing, punctuation or formatting"
            )
            state = {
                Freshness.CURRENT: "source file unchanged",
                Freshness.CHANGED: "source file changed after import",
                Freshness.MISSING: "source file missing",
                Freshness.UNKNOWN: "source file not checked",
            }[match.freshness]
            where = location(match.document, match.line_start, match.line_end, match.page)
            lines.append(
                f"VERIFIED ({how}): {where}"
                f" — version {short_version(match.document.version_id)}, {state}."
            )
        return "\n".join(lines)
    if result.status is VerifyStatus.ONLY_IN_OTHER_VERSION:
        return "\n".join(
            "OUTDATED: found only in version "
            f"{short_version(match.document.version_id)} of "
            f"{location(match.document, match.line_start, match.line_end, match.page)}; "
            "the current version no longer contains it."
            for match in result.matches
        )
    lines = [f"NOT FOUND verbatim in {result.searched_documents} documents."]
    if result.closest is not None:
        closest = result.closest
        lines.append(
            f"Closest passage (similarity {closest.similarity:.2f}): "
            f"{location(closest.document, closest.line_start, closest.line_end, closest.page)}"
        )
        lines.append(f"   {safe(closest.snippet)}")
        lines.append("Quote the document text exactly, or say that it is a paraphrase.")
    return "\n".join(lines)


def render_add(report: AddReport) -> str:
    """Render one bulk preparation summary and every failure with its hint."""
    lines = [
        f"Processed {len(report.outcomes)} files in {report.seconds:.1f}s: "
        f"{report.count(AddStatus.ADDED)} added, {report.count(AddStatus.UPDATED)} updated, "
        f"{report.count(AddStatus.UNCHANGED)} unchanged, {report.count(AddStatus.FAILED)} failed."
    ]
    if report.skipped_unsupported:
        lines.append(f"Skipped {report.skipped_unsupported} files with unsupported types.")
    for outcome in report.outcomes:
        if outcome.status is AddStatus.FAILED:
            reason = outcome.hint or outcome.error_code or "failed"
            lines.append(f"failed: {safe(outcome.path)} — {safe(reason)}")
    return "\n".join(lines)


def render_export(report: ExportReport) -> str:
    """Render one agent view export summary."""
    return (
        f"Agent view: {report.documents} documents ({tokens(report.total_tokens)} tokens) in "
        f"{safe(report.directory)} — {len(report.written)} written, {report.unchanged} unchanged, "
        f"{len(report.removed)} removed. Start with {safe(report.index_file)}"
    )


def _fence_for(body: str) -> str:
    longest = max((len(match.group(0)) for match in _BACKTICKS.finditer(body)), default=2)
    return "`" * max(3, longest + 1)


def _freshness_notice(freshness: Freshness) -> str | None:
    if freshness is Freshness.CHANGED:
        return CHANGED_NOTICE
    if freshness is Freshness.MISSING:
        return MISSING_NOTICE
    return None


__all__ = [
    "CHANGED_NOTICE",
    "MISSING_NOTICE",
    "location",
    "render_add",
    "render_docs",
    "render_export",
    "render_find",
    "render_outline",
    "render_read",
    "render_verify",
    "safe",
    "short_heading",
    "short_version",
    "tokens",
]
