"""Token-efficient agent access: documents, find, read, outline and quote verification.

The service keeps a disposable agent index synchronized with the catalog heads and uses
it only to locate evidence. Returned text, snippets and document identities come from a
copy rebuilt from authoritative sources (catalog, content-addressed store and verified
native artifacts) once per representation and process; a disagreeing index entry is
rebuilt in place. Every answer names the exact document version it was taken from.
"""

from __future__ import annotations

import re
from collections import Counter, OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from openardp.domain.agent_query import (
    MAX_QUOTE_CHARACTERS,
    QueryPlan,
    best_snippet,
    closest_similarity,
    is_question,
    locate_quote,
    plan_query,
    quote_fragments,
    term_coverage,
)
from openardp.domain.agent_results import (
    ClosestPassage,
    DocsResult,
    DocumentEntry,
    DocumentRef,
    FindHit,
    FindResult,
    Freshness,
    OutlineEntry,
    OutlineResult,
    PendingDocument,
    QuoteMatch,
    ReadResult,
    VerifyResult,
    VerifyStatus,
)
from openardp.domain.agent_text import (
    AgentPassage,
    AgentTextRecord,
    IndexedDocument,
    estimate_tokens,
    page_for_line,
)
from openardp.domain.ingestion import (
    DocumentSummary,
    SourceFreshness,
    SourceStatus,
    TextMediaType,
)
from openardp.ports.agent import (
    AgentDocumentAmbiguous,
    AgentDocumentNotFound,
    AgentIndex,
    AgentRangeInvalid,
    AgentRenderUnavailable,
)
from openardp.ports.catalog import RepresentationIntegrityError
from openardp.ports.object_store import ObjectStoreError
from openardp.services.agent_texts import (
    AgentTextBuilder,
    BuiltText,
    document_label,
    short_id,
)

DEFAULT_FIND_LIMIT = 8
MAX_FIND_LIMIT = 50
DEFAULT_READ_TOKENS = 2_000
MIN_READ_TOKENS = 50
MAX_READ_TOKENS = 20_000
MAX_OUTLINE_ENTRIES = 200
_CANDIDATE_PASSAGES = 300
_PER_DOCUMENT_FIRST_PASS = 3
_VERIFY_ALL_DOCUMENTS_UP_TO = 50
_VERIFY_CANDIDATE_DOCUMENTS = 25
_CLOSEST_PASSAGES = 15
_VERIFIED_CACHE_CHARACTERS = 8_000_000
_MIN_SHORT_ID = 6
_RANGE = re.compile(r"^\s*(\d{1,7})\s*(?:(-)\s*(\d{1,7})?)?\s*$")
_HEX_REFERENCE = re.compile(r"^#?[0-9a-f-]{6,36}$")
_VERSION_REFERENCE = re.compile(r"^(?:sha256:)?([0-9a-f]{8,64})$")

StatusProbe = Callable[[str], SourceStatus]


@dataclass(frozen=True, slots=True)
class RefreshReport:
    """Outcome of synchronizing the agent index with catalog heads."""

    indexed: int
    rebuilt: tuple[str, ...]
    removed: int
    failed: tuple[str, ...]


class AgentAccessService:
    """Serve compact located evidence over a disposable, self-healing agent index."""

    def __init__(
        self,
        builder: AgentTextBuilder,
        index: AgentIndex,
        *,
        status_probe: StatusProbe | None = None,
    ) -> None:
        """Bind the text builder, the disposable index and an optional exact probe."""
        self._builder = builder
        self._index = index
        self._status_probe = status_probe
        self._summaries: dict[str, DocumentSummary] = {}
        self._verified_cache: OrderedDict[str, BuiltText] = OrderedDict()

    def refresh(self) -> RefreshReport:
        """Bring the agent index in line with every READY catalog head."""
        summaries = {
            str(summary.document_id): summary for summary in self._builder.ready_summaries()
        }
        self._summaries = summaries
        indexed = {document.document_id: document for document in self._index.indexed_documents()}
        removed = [document_id for document_id in indexed if document_id not in summaries]
        self._index.remove_documents(removed)
        rebuilt: list[str] = []
        failed: list[str] = []
        for document_id, summary in summaries.items():
            current = indexed.get(document_id)
            if summary.head is None:
                continue
            if (
                current is not None
                and _matches_head(current, summary)
                and current.renderer == self._builder.expected_renderer(current.media_type)
            ):
                continue
            label = document_label(summary.source_key.locator)
            try:
                built = self._builder.build(summary)
            except (
                AgentRenderUnavailable,
                RepresentationIntegrityError,
                ObjectStoreError,
                UnicodeDecodeError,
                ValueError,
            ):
                self._index.remove_documents([document_id])
                failed.append(label)
                continue
            self._index.replace_document(built.record, built.passages)
            rebuilt.append(label)
        return RefreshReport(
            indexed=len(summaries) - len(failed),
            rebuilt=tuple(rebuilt),
            removed=len(removed),
            failed=tuple(failed),
        )

    def documents(self, *, check_freshness: bool = True) -> DocsResult:
        """Return every prepared document with size and freshness, plus pending sources."""
        self.refresh()
        entries = [
            DocumentEntry(
                **_ref(document).model_dump(),
                token_estimate=document.token_estimate,
                line_count=document.line_count,
                page_count=document.page_count,
                heading_count=document.heading_count,
                freshness=self._freshness(document) if check_freshness else Freshness.UNKNOWN,
            )
            for document in self._index.indexed_documents()
        ]
        entries.sort(key=lambda entry: (entry.label.casefold(), entry.document_id))
        indexed_ids = {entry.document_id for entry in entries}
        pending = [
            PendingDocument(
                document_id=str(summary.document_id),
                label=document_label(summary.source_key.locator),
                locator=summary.source_key.locator,
            )
            for summary in self._builder.all_summaries()
            if str(summary.document_id) not in indexed_ids
        ]
        pending.sort(key=lambda item: (item.label.casefold(), item.document_id))
        return DocsResult(
            documents=tuple(entries),
            pending=tuple(pending),
            total_tokens=sum(entry.token_estimate for entry in entries),
        )

    def resolve(self, reference: str) -> IndexedDocument:
        """Resolve an ID, short ID, file name or path suffix to one prepared document."""
        self.refresh()
        return self._resolve(reference, self._index.indexed_documents())

    def find(
        self,
        query: str,
        *,
        document: str | None = None,
        limit: int = DEFAULT_FIND_LIMIT,
    ) -> FindResult:
        """Return ranked, diversified passages for a question or keyword query."""
        limit = max(1, min(limit, MAX_FIND_LIMIT))
        plan = plan_query(query)
        self.refresh()
        documents = {item.document_id: item for item in self._index.indexed_documents()}
        if not plan.terms:
            return FindResult(query_terms=(), hits=(), candidates=0)
        scope = (
            [self._resolve(document, tuple(documents.values())).document_id] if document else None
        )
        question = is_question(query)
        for attempt in range(2):
            rows = self._index.search(
                plan.match_expression(),
                document_ids=scope,
                limit=_CANDIDATE_PASSAGES,
            )
            selected = _diversify(_ranked(rows, documents, plan, question=question), limit)
            verified = [
                (coverage, self._verified_passage(documents[passage.document_id], passage))
                for coverage, _rank, passage in selected
            ]
            # A drifted hit rebuilt its index entry; search the repaired index once more.
            if attempt or all(pair is not None for _coverage, pair in verified):
                break
        hits: list[FindHit] = []
        hit_documents: dict[str, AgentTextRecord] = {}
        for coverage, pair in verified:
            if pair is None:
                continue
            record, passage = pair
            hit_documents[record.document_id] = record
            hits.append(
                FindHit(
                    document=_ref(record),
                    line_start=passage.line_start,
                    line_end=passage.line_end,
                    page=passage.page,
                    heading=passage.heading,
                    snippet=best_snippet(passage.text, plan),
                    matched_terms=coverage,
                    token_estimate=estimate_tokens(passage.text),
                )
            )
        changed = tuple(
            sorted(
                record.label
                for record in hit_documents.values()
                if self._freshness(record) in {Freshness.CHANGED, Freshness.MISSING}
            )
        )
        return FindResult(
            query_terms=tuple(term.fts().replace('"', "") for term in plan.terms),
            hits=tuple(hits),
            candidates=len(rows),
            changed_sources=changed,
        )

    def read(
        self,
        document: str,
        *,
        page: str | None = None,
        lines: str | None = None,
        section: str | None = None,
        max_tokens: int = DEFAULT_READ_TOKENS,
    ) -> ReadResult:
        """Return one bounded excerpt selected by page, line range or section heading."""
        record = self._verified(self.resolve(document)).record
        text_lines = record.text.split("\n") if record.text else []
        start, end = _select_range(record, text_lines, page=page, lines=lines, section=section)
        budget = max(MIN_READ_TOKENS, min(max_tokens, MAX_READ_TOKENS)) * 4
        selected: list[str] = []
        used = 0
        truncated = False
        next_line: int | None = None
        for number in range(start, end + 1):
            line = text_lines[number - 1]
            if not selected and len(line) + 1 > budget:
                selected.append(line[:budget] + " …[line truncated]")
                truncated = number < end
                next_line = number + 1 if truncated else None
                break
            if selected and used + len(line) + 1 > budget:
                truncated = True
                next_line = number
                break
            selected.append(line)
            used += len(line) + 1
        last = start + len(selected) - 1
        text = "\n".join(selected)
        return ReadResult(
            document=_ref(record),
            line_start=start,
            line_end=max(last, 0),
            total_lines=len(text_lines),
            pages=_pages_between(record, start, last),
            text=text,
            token_estimate=estimate_tokens(text),
            truncated=truncated,
            next_line=next_line,
            freshness=self._freshness(record),
        )

    def outline(self, document: str, *, max_entries: int = MAX_OUTLINE_ENTRIES) -> OutlineResult:
        """Return headings, or pages and slides, with the token size of each section."""
        record = self._verified(self.resolve(document)).record
        text_lines = record.text.split("\n") if record.text else []
        starts: list[tuple[int, int, str]] = [
            (heading.line, heading.level, heading.text) for heading in record.headings
        ]
        if not starts:
            starts = [
                (page.line, 0, _first_content(text_lines, page.line)) for page in record.pages
            ]
        entries: list[OutlineEntry] = []
        for position, (line, level, text) in enumerate(starts[:max_entries]):
            end = _section_end(starts, position, len(text_lines))
            entries.append(
                OutlineEntry(
                    line=line,
                    level=level,
                    text=text,
                    page=page_for_line(record.pages, line),
                    token_estimate=estimate_tokens("\n".join(text_lines[line - 1 : end])),
                )
            )
        return OutlineResult(
            document=DocumentEntry(
                **_ref(record).model_dump(),
                token_estimate=record.token_estimate,
                line_count=record.line_count,
                page_count=record.page_count,
                heading_count=record.heading_count,
                freshness=self._freshness(record),
            ),
            entries=tuple(entries),
            truncated=len(starts) > max_entries,
        )

    def verify(
        self,
        quote: str,
        *,
        document: str | None = None,
        version: str | None = None,
    ) -> VerifyResult:
        """Verify that a quote occurs verbatim in an exact prepared document version."""
        fragments = quote_fragments(quote)
        if not fragments:
            raise AgentRangeInvalid("quote is empty")
        if len(quote) > MAX_QUOTE_CHARACTERS:
            raise AgentRangeInvalid("quote is too long")
        self.refresh()
        documents = self._index.indexed_documents()
        plan = plan_query(" ".join(fragments))
        targets = (
            (self._resolve(document, documents),)
            if document
            else self._verification_targets(documents, plan)
        )
        matches = [
            match for target in targets if (match := self._current_match(target, quote)) is not None
        ]
        if matches:
            return VerifyResult(
                status=VerifyStatus.VERIFIED,
                matches=tuple(matches),
                searched_documents=len(targets),
            )
        if version is not None:
            historical = self._historical_matches(targets, quote, version)
            if historical:
                return VerifyResult(
                    status=VerifyStatus.ONLY_IN_OTHER_VERSION,
                    matches=historical,
                    searched_documents=len(targets),
                )
        return VerifyResult(
            status=VerifyStatus.NOT_FOUND,
            closest=self._closest(targets, plan, quote),
            searched_documents=len(targets),
        )

    def _verification_targets(
        self,
        documents: tuple[IndexedDocument, ...],
        plan: QueryPlan,
    ) -> tuple[IndexedDocument, ...]:
        if len(documents) <= _VERIFY_ALL_DOCUMENTS_UP_TO or not plan.terms:
            return documents
        by_id = {document.document_id: document for document in documents}
        ordered: list[IndexedDocument] = []
        for passage, _rank in self._index.search(
            plan.match_expression(),
            document_ids=None,
            limit=_CANDIDATE_PASSAGES,
        ):
            candidate = by_id.get(passage.document_id)
            if candidate is not None and candidate not in ordered:
                ordered.append(candidate)
            if len(ordered) >= _VERIFY_CANDIDATE_DOCUMENTS:
                break
        return tuple(ordered)

    def _current_match(self, document: IndexedDocument, quote: str) -> QuoteMatch | None:
        # The index only narrows candidates; a positive answer is re-checked below.
        cached = self._index.load_text(document.document_id)
        if cached is not None and locate_quote(cached.text, quote) is None:
            return None
        record = self._verified(document).record
        location = locate_quote(record.text, quote)
        if location is None:
            return None
        first = _line_of(record.text, location.start)
        last = _line_of(record.text, max(location.start, location.end - 1))
        return QuoteMatch(
            document=_ref(record),
            line_start=first,
            line_end=last,
            page=page_for_line(record.pages, first),
            level=location.level,
            current_version=True,
            freshness=self._exact_freshness(record),
        )

    def _historical_matches(
        self,
        targets: tuple[IndexedDocument, ...],
        quote: str,
        version: str,
    ) -> tuple[QuoteMatch, ...]:
        wanted = _VERSION_REFERENCE.match(version.strip().casefold())
        if wanted is None:
            raise AgentRangeInvalid("version must be a sha256 identifier or its hex prefix")
        matches: list[QuoteMatch] = []
        for target in targets:
            for version_id in self._builder.version_ids(UUID(target.document_id)):
                if version_id == target.version_id:
                    continue
                if not version_id.removeprefix("sha256:").startswith(wanted.group(1)):
                    continue
                text = self._builder.text_for_version(UUID(target.document_id), version_id)
                location = locate_quote(text, quote) if text is not None else None
                if text is None or location is None:
                    continue
                first = _line_of(text, location.start)
                current = self._verified(target).record
                matches.append(
                    QuoteMatch(
                        document=_ref(current).model_copy(update={"version_id": version_id}),
                        line_start=first,
                        line_end=_line_of(text, max(location.start, location.end - 1)),
                        level=location.level,
                        current_version=False,
                        freshness=Freshness.CHANGED,
                    )
                )
        return tuple(matches)

    def _closest(
        self,
        targets: tuple[IndexedDocument, ...],
        plan: QueryPlan,
        quote: str,
    ) -> ClosestPassage | None:
        if not plan.terms or not targets:
            return None
        by_id = {target.document_id: target for target in targets}
        rows = self._index.search(
            plan.match_expression(),
            document_ids=list(by_id),
            limit=_CLOSEST_PASSAGES,
        )
        ranked = sorted(
            ((closest_similarity(passage.text, quote)[0], passage) for passage, _rank in rows),
            key=lambda item: -item[0],
        )
        for similarity, candidate in ranked:
            pair = self._verified_passage(by_id[candidate.document_id], candidate)
            if pair is None:
                continue
            record, passage = pair
            return ClosestPassage(
                document=_ref(record),
                line_start=passage.line_start,
                line_end=passage.line_end,
                page=passage.page,
                similarity=round(min(max(similarity, 0.0), 1.0), 3),
                snippet=best_snippet(passage.text, plan),
            )
        return None

    def _verified(self, document: IndexedDocument) -> BuiltText:
        """Return the document rebuilt from authoritative sources, healing a drifted index.

        The rebuild reads the catalog, the content-addressed source or the verified native
        artifact, so returned content never depends on the index being intact. It runs once
        per representation and process; a disagreeing index entry is replaced.
        """
        summary = self._summaries.get(document.document_id) or self._builder.summary_for(
            document.document_id
        )
        if summary is None or summary.head is None:
            raise AgentDocumentNotFound("document is no longer prepared")
        key = summary.head.representation_id
        cached = self._verified_cache.get(key)
        if cached is not None:
            self._verified_cache.move_to_end(key)
            return cached
        built = self._builder.build(summary)
        stored = self._index.load_text(document.document_id)
        if stored is None or _content(stored) != _content(built.record):
            self._index.replace_document(built.record, built.passages)
        self._verified_cache[key] = built
        retained = sum(len(item.record.text) for item in self._verified_cache.values())
        while retained > _VERIFIED_CACHE_CHARACTERS and len(self._verified_cache) > 1:
            _key, evicted = self._verified_cache.popitem(last=False)
            retained -= len(evicted.record.text)
        return built

    def _verified_passage(
        self,
        document: IndexedDocument,
        passage: AgentPassage,
    ) -> tuple[AgentTextRecord, AgentPassage] | None:
        """Return the verified passage an index hit points to, or None after drift."""
        built = self._verified(document)
        if passage.ordinal < len(built.passages):
            exact = built.passages[passage.ordinal]
            if (exact.line_start, exact.line_end, exact.text) == (
                passage.line_start,
                passage.line_end,
                passage.text,
            ):
                return built.record, exact
        self._index.replace_document(built.record, built.passages)
        return None

    def _resolve(
        self,
        reference: str,
        documents: tuple[IndexedDocument, ...],
    ) -> IndexedDocument:
        cleaned = reference.strip()
        if not cleaned:
            raise AgentDocumentNotFound("document reference is empty")
        folded = cleaned.casefold()
        exact = [document for document in documents if document.document_id == folded]
        if exact:
            return exact[0]
        rules: list[Callable[[IndexedDocument], bool]] = []
        compact = folded.lstrip("#").replace("-", "")
        if _HEX_REFERENCE.match(folded) and len(compact) >= _MIN_SHORT_ID:
            rules.append(lambda document: document.document_id.replace("-", "").endswith(compact))
        rules.append(lambda document: document.label.casefold() == folded)
        normalized = folded.replace("\\", "/")
        rules.append(
            lambda document: (
                document.locator.casefold().replace("\\", "/").endswith("/" + normalized)
            )
        )
        rules.append(lambda document: folded in document.label.casefold())
        for rule in rules:
            matches = [document for document in documents if rule(document)]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise AgentDocumentAmbiguous(
                    "document reference is ambiguous",
                    candidates=[
                        f"{match.label} (id {short_id(match.document_id)})"
                        for match in matches[:10]
                    ],
                )
        raise AgentDocumentNotFound("document reference matches no prepared document")

    def _freshness(self, document: IndexedDocument) -> Freshness:
        """Return a cheap freshness check: stat first, hash only when metadata moved."""
        try:
            metadata = Path(document.locator).lstat()
        except FileNotFoundError:
            return Freshness.MISSING
        except OSError:
            return Freshness.UNKNOWN
        recorded = document.source_modified_at
        if (
            recorded is not None
            and metadata.st_size == document.source_byte_length
            and abs(metadata.st_mtime_ns / 1_000_000_000 - recorded.timestamp()) < 0.001
        ):
            return Freshness.CURRENT
        return self._exact_freshness(document)

    def _exact_freshness(self, document: IndexedDocument) -> Freshness:
        if self._status_probe is None:
            return Freshness.UNKNOWN
        try:
            status = self._status_probe(document.document_id)
        except (OSError, ValueError, RuntimeError):
            return Freshness.UNKNOWN
        if status.freshness is SourceFreshness.SOURCE_MISSING:
            return Freshness.MISSING
        if status.head is not None and status.head.version_id != document.version_id:
            return Freshness.CHANGED
        return {
            SourceFreshness.CURRENT: Freshness.CURRENT,
            SourceFreshness.SOURCE_CHANGED: Freshness.CHANGED,
        }.get(status.freshness, Freshness.UNKNOWN)


def _ref(document: IndexedDocument) -> DocumentRef:
    return DocumentRef(
        document_id=document.document_id,
        short_id=short_id(document.document_id),
        label=document.label,
        locator=document.locator,
        media_type=document.media_type,
        version_id=document.version_id,
        page_label=document.page_label,
    )


def _matches_head(document: IndexedDocument, summary: DocumentSummary) -> bool:
    """Return whether an index entry still names the catalog head and source path."""
    head = summary.head
    return (
        head is not None
        and document.version_id == head.version_id
        and document.representation_id == head.representation_id
        and document.locator == summary.source_key.locator
    )


def _content(record: AgentTextRecord) -> dict[str, object]:
    """Return every stored fact of a record except the moment it was indexed."""
    return record.model_dump(mode="json", exclude={"indexed_at"})


def _ranked(
    rows: tuple[tuple[AgentPassage, float], ...],
    documents: dict[str, IndexedDocument],
    plan: QueryPlan,
    *,
    question: bool,
) -> list[tuple[int, float, AgentPassage]]:
    """Order index hits: full text coverage, coverage, prose for questions, then rank."""
    return sorted(
        (
            (term_coverage(f"{passage.heading}\n{passage.text}", plan), rank, passage)
            for passage, rank in rows
            if passage.document_id in documents
        ),
        key=lambda item: (
            -min(1, term_coverage(item[2].text, plan)),
            -item[0],
            question and _tabular(item[2], documents[item[2].document_id]),
            item[1],
            item[2].document_id,
            item[2].ordinal,
        ),
    )


def _tabular(passage: AgentPassage, document: IndexedDocument) -> bool:
    """Return whether a passage is a table or CSV row run rather than prose."""
    return document.media_type == TextMediaType.CSV.value or passage.text.lstrip().startswith("|")


def _diversify(
    scored: list[tuple[int, float, AgentPassage]],
    limit: int,
) -> list[tuple[int, float, AgentPassage]]:
    selected: list[tuple[int, float, AgentPassage]] = []
    per_document: Counter[str] = Counter()
    deferred: list[tuple[int, float, AgentPassage]] = []
    for item in scored:
        if len(selected) >= limit:
            break
        document_id = item[2].document_id
        if per_document[document_id] < _PER_DOCUMENT_FIRST_PASS:
            selected.append(item)
            per_document[document_id] += 1
        else:
            deferred.append(item)
    for item in deferred:
        if len(selected) >= limit:
            break
        selected.append(item)
    order = {id(item): position for position, item in enumerate(scored)}
    return sorted(selected, key=lambda item: order[id(item)])


def _parse_range(value: str, *, name: str) -> tuple[int, int | None, bool]:
    """Parse ``12``, ``12-20`` or ``12-`` into first, optional last and a range flag."""
    match = _RANGE.match(value)
    if match is None:
        raise AgentRangeInvalid(f"{name} must look like 12, 12-20 or 12-")
    first = int(match.group(1))
    if first < 1:
        raise AgentRangeInvalid(f"{name} numbers start at 1")
    if match.group(2) is None:
        return first, None, False
    last = int(match.group(3)) if match.group(3) is not None else None
    if last is not None and last < first:
        raise AgentRangeInvalid(f"{name} range is empty")
    return first, last, True


def _select_range(
    record: AgentTextRecord,
    text_lines: list[str],
    *,
    page: str | None,
    lines: str | None,
    section: str | None,
) -> tuple[int, int]:
    total = len(text_lines)
    if total == 0:
        raise AgentRangeInvalid("document has no text")
    if sum(value is not None for value in (page, lines, section)) > 1:
        raise AgentRangeInvalid("choose only one of page, lines or section")
    if page is not None:
        return _trim_blank(text_lines, *_page_range(record, total, page))
    if lines is not None:
        first, last, _is_range = _parse_range(lines, name="lines")
        if first > total:
            raise AgentRangeInvalid(f"line {first} is beyond the last line {total}")
        return first, total if last is None else min(total, last)
    if section is not None:
        return _trim_blank(text_lines, *_section_range(record, total, section))
    return 1, total


def _trim_blank(text_lines: list[str], start: int, end: int) -> tuple[int, int]:
    """Drop blank lines at both ends of a selected range, keeping at least one line."""
    while start < end and not text_lines[start - 1].strip():
        start += 1
    while end > start and not text_lines[end - 1].strip():
        end -= 1
    return start, end


def _page_range(record: AgentTextRecord, total: int, page: str) -> tuple[int, int]:
    unit = record.page_label.value if record.page_label is not None else "page"
    if not record.pages:
        raise AgentRangeInvalid("this document has no pages; use lines or section")
    first, last, is_range = _parse_range(page, name=unit)
    numbers = [item.number for item in record.pages]
    if first not in numbers:
        raise AgentRangeInvalid(f"{unit} {first} does not exist ({min(numbers)}-{max(numbers)})")
    if last is None:
        last = max(numbers) if is_range else first
    start_line = next(item.line for item in record.pages if item.number == first)
    following = [item.line for item in record.pages if item.number > last]
    end_line = (min(following) - 1) if following else total
    return min(start_line + 1, total), max(min(start_line + 1, total), end_line)


def _section_range(record: AgentTextRecord, total: int, section: str) -> tuple[int, int]:
    wanted = section.strip().casefold()
    headings = list(record.headings)
    matches = [heading for heading in headings if heading.text.casefold() == wanted] or [
        heading for heading in headings if wanted in heading.text.casefold()
    ]
    if not matches:
        raise AgentRangeInvalid("no heading matches that section")
    chosen = matches[0]
    later = [
        heading.line
        for heading in headings
        if heading.line > chosen.line and heading.level <= chosen.level
    ]
    return chosen.line, (min(later) - 1) if later else total


def _pages_between(record: AgentTextRecord, start: int, end: int) -> tuple[int, ...]:
    if not record.pages or end < start:
        return ()
    numbers = {page.number for page in record.pages if start <= page.line <= end}
    first = page_for_line(record.pages, start)
    if first is not None:
        numbers.add(first)
    return tuple(sorted(numbers))


def _section_end(starts: list[tuple[int, int, str]], position: int, total: int) -> int:
    _line, level, _text = starts[position]
    for later_line, later_level, _later_text in starts[position + 1 :]:
        if later_level <= level or level == 0:
            return later_line - 1
    return total


def _first_content(text_lines: list[str], marker_line: int) -> str:
    for line in text_lines[marker_line : marker_line + 40]:
        stripped = line.strip().lstrip("#").strip()
        if stripped and not stripped.startswith("<!--"):
            return stripped[:80]
    return ""


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


__all__ = [
    "DEFAULT_FIND_LIMIT",
    "DEFAULT_READ_TOKENS",
    "MAX_FIND_LIMIT",
    "MAX_READ_TOKENS",
    "AgentAccessService",
    "RefreshReport",
    "StatusProbe",
]
