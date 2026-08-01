"""Offline benchmark treatments over the frozen synthetic release corpus."""

from __future__ import annotations

import hashlib
import re
import time
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from openardp.domain.identity import canonical_sha256
from openardp.domain.release import (
    Baseline,
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPhase,
    EvidenceStatus,
    MetricUnit,
    benchmark_observation_id,
)
from openardp.ports.release import MonotonicNanoseconds

_MAX_SOURCE_BYTES = 16 * 1024 * 1024
_MAX_ARCHIVE_MEMBERS = 2_000
_MAX_ARCHIVE_XML_BYTES = 32 * 1024 * 1024
_WORD = re.compile(r"[\w-]+", re.UNICODE)


class BenchmarkTreatmentUnavailable(RuntimeError):
    """Raised when a declared treatment cannot run in the current environment."""


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """One exact corpus source and inspectable mechanical judgment."""

    case_id: str
    source_case_id: str
    source: Path
    query_terms: tuple[str, ...]
    expected_terms: tuple[str, ...]
    expected_evidence_ids: tuple[str, ...] = ()
    expected_anchors: tuple[str, ...] = ()
    maximum_selected_bytes: int = 256


@dataclass(frozen=True, slots=True)
class TreatmentResult:
    """Body-local treatment facts converted to body-free observations."""

    selected_text: str
    native_bytes: int
    parser_invocations: int
    selected_evidence_ids: tuple[str, ...] = ()
    selected_anchors: tuple[str, ...] = ()

    @property
    def selected_bytes(self) -> int:
        """Return the selected UTF-8 byte count."""
        return len(self.selected_text.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class EvidenceUnit:
    """One deterministic provider-native retrieval unit."""

    evidence_id: str
    anchor: str
    text: str


@dataclass(frozen=True, slots=True)
class NativeDocument:
    """One persisted provider-native projection used by fair reuse baselines."""

    source_version_id: str
    byte_length: int
    units: tuple[EvidenceUnit, ...]


class ReleaseBenchmarkTreatment:
    """Base class that times one baseline and emits closed observations."""

    baseline: Baseline
    latency_phase: BenchmarkPhase

    def __init__(self, *, clock: MonotonicNanoseconds = time.monotonic_ns) -> None:
        """Create a treatment with an injectable monotonic clock."""
        self._clock = clock

    def prepare(self, case: BenchmarkCase) -> None:
        """Warm treatment state before retained observations."""

    def invalidate(self, case_id: str) -> None:
        """Invalidate any cached state for an edited source."""

    def execute(self, case: BenchmarkCase) -> TreatmentResult:
        """Execute the concrete treatment."""
        raise NotImplementedError

    def run_case(self, case: BenchmarkCase, *, repetition: int) -> tuple[BenchmarkObservation, ...]:
        """Measure one treatment without retaining document bodies."""
        started = self._clock()
        result = self.execute(case)
        elapsed = self._clock() - started
        if elapsed < 0:
            raise ValueError("monotonic clock moved backwards")
        observations = [
            _passed(
                self.baseline,
                case.case_id,
                self.latency_phase,
                repetition,
                BenchmarkMetric.LATENCY,
                MetricUnit.NANOSECONDS,
                elapsed,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.WARM,
                repetition,
                BenchmarkMetric.PARSER_INVOCATIONS,
                MetricUnit.COUNT,
                result.parser_invocations,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.WARM,
                repetition,
                BenchmarkMetric.NATIVE_BYTES,
                MetricUnit.BYTES,
                result.native_bytes,
            ),
        ]
        if self.baseline in {
            Baseline.NATIVE_RETRIEVAL,
            Baseline.OPENARDP_RETRIEVAL,
            Baseline.OPENARDP_COMPILER,
        }:
            precision, recall, reciprocal_rank = _rank_scores(
                case.expected_evidence_ids,
                result.selected_evidence_ids,
            )
            anchor_correctness = _anchor_score(
                case.expected_anchors,
                result.selected_anchors,
            )
            for metric, value in (
                (BenchmarkMetric.PRECISION, precision),
                (BenchmarkMetric.RECALL, recall),
                (BenchmarkMetric.RECIPROCAL_RANK, reciprocal_rank),
                (BenchmarkMetric.ANCHOR_CORRECTNESS, anchor_correctness),
                (
                    BenchmarkMetric.CORRECTNESS,
                    min(precision, recall, reciprocal_rank, anchor_correctness),
                ),
            ):
                observations.append(
                    _passed(
                        self.baseline,
                        case.case_id,
                        self.latency_phase,
                        repetition,
                        metric,
                        MetricUnit.RATIO,
                        value,
                    )
                )
        if self.baseline is Baseline.OPENARDP_COMPILER:
            observations.extend(
                (
                    _passed(
                        self.baseline,
                        case.case_id,
                        BenchmarkPhase.COMPILE,
                        repetition,
                        BenchmarkMetric.SELECTED_BYTES,
                        MetricUnit.BYTES,
                        result.selected_bytes,
                    ),
                    _passed(
                        self.baseline,
                        case.case_id,
                        BenchmarkPhase.COMPILE,
                        repetition,
                        BenchmarkMetric.COVERAGE,
                        MetricUnit.RATIO,
                        _evidence_coverage(
                            case.expected_evidence_ids,
                            result.selected_evidence_ids,
                        ),
                    ),
                )
            )
        return tuple(observations)

    def lifecycle_observations(
        self, case: BenchmarkCase, *, repetition: int
    ) -> tuple[BenchmarkObservation, ...]:
        """Measure cold preparation, warm reuse, update and deterministic replay."""
        self.invalidate(case.case_id)
        stale_rejected = 1.0
        if self.baseline is not Baseline.RAW_REPARSE:
            try:
                self.execute(case)
            except BenchmarkTreatmentUnavailable:
                pass
            else:
                stale_rejected = 0.0
        cold_started = self._clock()
        self.prepare(case)
        cold_elapsed = self._clock() - cold_started
        warm_started = self._clock()
        before = self.execute(case)
        warm_elapsed = self._clock() - warm_started
        self.invalidate(case.case_id)
        update_started = self._clock()
        self.prepare(case)
        update_elapsed = self._clock() - update_started
        after = self.execute(case)
        replay_match = float(
            before.selected_evidence_ids == after.selected_evidence_ids
            and before.selected_anchors == after.selected_anchors
        )
        return (
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.COLD,
                repetition,
                BenchmarkMetric.LATENCY,
                MetricUnit.NANOSECONDS,
                cold_elapsed,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.COLD,
                repetition,
                BenchmarkMetric.PARSER_INVOCATIONS,
                MetricUnit.COUNT,
                1,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.COLD,
                repetition,
                BenchmarkMetric.STORAGE_BYTES,
                MetricUnit.BYTES,
                before.native_bytes,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.WARM,
                repetition,
                BenchmarkMetric.LATENCY,
                MetricUnit.NANOSECONDS,
                warm_elapsed,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.UPDATE,
                repetition,
                BenchmarkMetric.LATENCY,
                MetricUnit.NANOSECONDS,
                update_elapsed,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.UPDATE,
                repetition,
                BenchmarkMetric.STALE_REJECTION,
                MetricUnit.RATIO,
                stale_rejected,
            ),
            _passed(
                self.baseline,
                case.case_id,
                BenchmarkPhase.REPLAY,
                repetition,
                BenchmarkMetric.REPLAY_MATCH,
                MetricUnit.RATIO,
                replay_match,
            ),
        )


class RawReparseTreatment(ReleaseBenchmarkTreatment):
    """Read and parse the original source on every retrieval."""

    baseline = Baseline.RAW_REPARSE
    latency_phase = BenchmarkPhase.RETRIEVAL

    def prepare(self, case: BenchmarkCase) -> None:
        """Exercise one cold parse without retaining provider state."""
        _parse_native(case)

    def execute(self, case: BenchmarkCase) -> TreatmentResult:
        """Read and parse the source for this exact execution."""
        native = _parse_native(case)
        return _result(native.units, native.byte_length, parser_invocations=1)


class NativeReuseTreatment(ReleaseBenchmarkTreatment):
    """Reuse a persisted native text projection without reparsing the source."""

    baseline = Baseline.NATIVE_REUSE
    latency_phase = BenchmarkPhase.RETRIEVAL

    def __init__(self, *, clock: MonotonicNanoseconds = time.monotonic_ns) -> None:
        """Create an empty reusable native projection cache."""
        super().__init__(clock=clock)
        self._native: dict[str, NativeDocument] = {}

    def prepare(self, case: BenchmarkCase) -> None:
        """Parse and retain one native projection before measured reuse."""
        self._native[case.case_id] = _parse_native(case)

    def invalidate(self, case_id: str) -> None:
        """Remove a stale projection for one edited case."""
        self._native.pop(case_id, None)

    def execute(self, case: BenchmarkCase) -> TreatmentResult:
        """Return a prepared projection without invoking a parser."""
        native = self._native_result(case)
        return _result(native.units, native.byte_length, parser_invocations=0)

    def _native_result(self, case: BenchmarkCase) -> NativeDocument:
        """Return the exact persisted native document or fail explicitly."""
        try:
            return self._native[case.case_id]
        except KeyError as error:
            raise BenchmarkTreatmentUnavailable("native-representation-unavailable") from error


class NativeRetrievalTreatment(NativeReuseTreatment):
    """Apply exact lexical retrieval directly to the persisted native projection."""

    baseline = Baseline.NATIVE_RETRIEVAL
    latency_phase = BenchmarkPhase.RETRIEVAL

    def execute(self, case: BenchmarkCase) -> TreatmentResult:
        """Run lexical retrieval over the prepared native projection."""
        native = self._native_result(case)
        selected = _ranked_units(native.units, case.query_terms)
        return _result(selected, native.byte_length, parser_invocations=0)


class OpenArdpRetrievalTreatment(NativeReuseTreatment):
    """Retrieve deterministic evidence chunks from a reusable parsed projection."""

    baseline = Baseline.OPENARDP_RETRIEVAL
    latency_phase = BenchmarkPhase.RETRIEVAL

    def execute(self, case: BenchmarkCase) -> TreatmentResult:
        """Rank reusable evidence chunks for the exact case query."""
        native = self._native_result(case)
        selected = _ranked_units(native.units, case.query_terms)
        return _result(selected, native.byte_length, parser_invocations=0)


class OpenArdpCompilerTreatment(OpenArdpRetrievalTreatment):
    """Compile the highest-ranked evidence within an exact UTF-8 byte budget."""

    baseline = Baseline.OPENARDP_COMPILER
    latency_phase = BenchmarkPhase.COMPILE

    def execute(self, case: BenchmarkCase) -> TreatmentResult:
        """Compile retrieved evidence within the declared byte budget."""
        native = self._native_result(case)
        ranked = _ranked_units(native.units, case.query_terms)
        selected = _budget_units(ranked, case.maximum_selected_bytes)
        return _result(selected, native.byte_length, parser_invocations=0)


class UnavailableTreatment(ReleaseBenchmarkTreatment):
    """Represent a declared baseline that is unavailable without substituting semantics."""

    def __init__(self, baseline: Baseline, reason: str) -> None:
        """Declare one unavailable baseline and stable reason."""
        super().__init__()
        self.baseline = baseline
        self.latency_phase = BenchmarkPhase.RETRIEVAL
        self._reason = reason

    def execute(self, case: BenchmarkCase) -> TreatmentResult:
        """Fail explicitly instead of substituting a different treatment."""
        raise BenchmarkTreatmentUnavailable(self._reason)


def unavailable_observation(
    baseline: Baseline,
    case_id: str,
    repetition: int,
    reason: str,
) -> BenchmarkObservation:
    """Return one stable unavailable observation for an honest failed treatment."""
    provisional = BenchmarkObservation.model_construct(
        observation_id="sha256:" + "0" * 64,
        baseline=baseline,
        case_id=case_id,
        phase=BenchmarkPhase.RETRIEVAL,
        repetition=repetition,
        metric=BenchmarkMetric.LATENCY,
        unit=MetricUnit.NANOSECONDS,
        value=None,
        status=EvidenceStatus.UNAVAILABLE,
        reason=_safe_reason(reason),
    )
    return provisional.model_copy(
        update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
    )


def rejected_observation(
    baseline: Baseline,
    case_id: str,
    repetition: int,
    reason: str,
) -> BenchmarkObservation:
    """Return one explicit rejected raw sample for invalid measurement evidence."""
    provisional = BenchmarkObservation.model_construct(
        observation_id="sha256:" + "0" * 64,
        baseline=baseline,
        case_id=case_id,
        phase=BenchmarkPhase.RETRIEVAL,
        repetition=repetition,
        metric=BenchmarkMetric.LATENCY,
        unit=MetricUnit.NANOSECONDS,
        value=None,
        status=EvidenceStatus.REJECTED,
        reason=_safe_reason(reason),
    )
    return provisional.model_copy(
        update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
    )


def source_digest(path: Path) -> str:
    """Return the bounded regular-file SHA-256 identity used by corpus validation."""
    data = _read_source(path)
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _parse_source(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in {".txt", ".md"}:
        return _read_source(path).decode("utf-8", errors="strict")
    if suffix == ".docx":
        return _archive_text(path, prefix="word/", suffix=".xml")
    if suffix == ".pptx":
        return _archive_text(path, prefix="ppt/slides/", suffix=".xml")
    raise BenchmarkTreatmentUnavailable("source-format-unavailable")


def _parse_native(case: BenchmarkCase) -> NativeDocument:
    """Create the exact persisted native projection once for reuse treatments."""
    text = _parse_source(case.source)
    data = _read_source(case.source)
    return NativeDocument(
        source_version_id=f"sha256:{hashlib.sha256(data).hexdigest()}",
        byte_length=len(text.encode("utf-8")),
        units=_parse_units(case, text),
    )


def _parse_units(case: BenchmarkCase, text: str) -> tuple[EvidenceUnit, ...]:
    lines = tuple(line.strip() for line in text.splitlines() if line.strip())
    if not lines and text.strip():
        lines = (text.strip(),)
    return tuple(
        EvidenceUnit(
            evidence_id=canonical_sha256(
                {
                    "case_id": case.source_case_id,
                    "ordinal": ordinal,
                    "text": line,
                }
            ),
            anchor=f"line-{ordinal + 1}",
            text=line,
        )
        for ordinal, line in enumerate(lines)
    )


def _result(
    units: Sequence[EvidenceUnit],
    native_bytes: int,
    *,
    parser_invocations: int,
) -> TreatmentResult:
    selected = tuple(units)
    return TreatmentResult(
        selected_text="\n".join(item.text for item in selected),
        native_bytes=native_bytes,
        parser_invocations=parser_invocations,
        selected_evidence_ids=tuple(item.evidence_id for item in selected),
        selected_anchors=tuple(item.anchor for item in selected),
    )


def _read_source(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise BenchmarkTreatmentUnavailable("source-not-regular")
    size = path.stat().st_size
    if size > _MAX_SOURCE_BYTES:
        raise BenchmarkTreatmentUnavailable("source-limit-exceeded")
    data = path.read_bytes()
    if len(data) != size:
        raise BenchmarkTreatmentUnavailable("source-changed-during-read")
    return data


def _archive_text(path: Path, *, prefix: str, suffix: str) -> str:
    _read_source(path)
    texts: list[str] = []
    expanded = 0
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > _MAX_ARCHIVE_MEMBERS:
                raise BenchmarkTreatmentUnavailable("archive-member-limit-exceeded")
            for member in sorted(members, key=lambda item: item.filename):
                pure = PurePosixPath(member.filename)
                if pure.is_absolute() or ".." in pure.parts:
                    raise BenchmarkTreatmentUnavailable("archive-path-unsafe")
                if not member.filename.startswith(prefix) or not member.filename.endswith(suffix):
                    continue
                expanded += member.file_size
                if expanded > _MAX_ARCHIVE_XML_BYTES:
                    raise BenchmarkTreatmentUnavailable("archive-expanded-limit-exceeded")
                raw = archive.read(member)
                if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
                    raise BenchmarkTreatmentUnavailable("archive-xml-doctype-rejected")
                # DTD/entity declarations are rejected above before the bounded parse.
                root = ElementTree.fromstring(raw)  # noqa: S314
                texts.extend(text for text in root.itertext() if text.strip())
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        raise BenchmarkTreatmentUnavailable("archive-malformed") from error
    return "\n".join(texts)


def _chunks(text: str) -> tuple[str, ...]:
    lines = tuple(line.strip() for line in text.splitlines() if line.strip())
    return lines or ((text.strip(),) if text.strip() else ())


def _ranked_units(
    units: Sequence[EvidenceUnit], query_terms: Sequence[str]
) -> tuple[EvidenceUnit, ...]:
    normalized_terms = tuple(term.casefold() for term in query_terms if term)
    ranked = sorted(
        enumerate(units),
        key=lambda item: (
            -sum(item[1].text.casefold().count(term) for term in normalized_terms),
            item[0],
        ),
    )
    return tuple(
        unit for _, unit in ranked if any(term in unit.text.casefold() for term in normalized_terms)
    ) or tuple(unit for _, unit in ranked[:1])


def _budget_units(units: Sequence[EvidenceUnit], maximum_bytes: int) -> tuple[EvidenceUnit, ...]:
    if maximum_bytes < 1:
        raise ValueError("maximum_selected_bytes must be positive")
    selected: list[EvidenceUnit] = []
    consumed = 0
    for unit in units:
        separator = 1 if selected else 0
        size = len(unit.text.encode("utf-8")) + separator
        if consumed + size > maximum_bytes:
            continue
        selected.append(unit)
        consumed += size
    return tuple(selected)


def _rank_scores(expected: Sequence[str], actual: Sequence[str]) -> tuple[float, float, float]:
    if not expected:
        return (0.0, 0.0, 0.0)
    expected_set = set(expected)
    relevant = sum(item in expected_set for item in actual)
    precision = relevant / len(actual) if actual else 0.0
    recall = relevant / len(expected_set)
    reciprocal_rank = next(
        (1.0 / rank for rank, item in enumerate(actual, start=1) if item in expected_set),
        0.0,
    )
    return precision, recall, reciprocal_rank


def _anchor_score(expected: Sequence[str], actual: Sequence[str]) -> float:
    if not expected:
        return 0.0
    return sum(anchor in actual for anchor in expected) / len(expected)


def _evidence_coverage(expected: Sequence[str], actual: Sequence[str]) -> float:
    if not expected:
        return 0.0
    return len(set(expected) & set(actual)) / len(set(expected))


def _lexical_select(text: str, query_terms: Sequence[str]) -> str:
    return _ranked_chunks(_chunks(text), query_terms)


def _ranked_chunks(chunks: Sequence[str], query_terms: Sequence[str]) -> str:
    normalized_terms = tuple(term.casefold() for term in query_terms if term)
    ranked = sorted(
        enumerate(chunks),
        key=lambda item: (
            -sum(item[1].casefold().count(term) for term in normalized_terms),
            item[0],
        ),
    )
    positive = [
        text for _, text in ranked if any(term in text.casefold() for term in normalized_terms)
    ]
    return "\n".join(positive or [text for _, text in ranked[:1]])


def _term_coverage(text: str, expected_terms: Sequence[str]) -> float:
    terms = tuple(term.casefold() for term in expected_terms)
    if not terms:
        return 1.0
    words = {word.casefold() for word in _WORD.findall(text)}
    return sum(term in words for term in terms) / len(terms)


def _truncate_utf8(text: str, maximum_bytes: int) -> str:
    if maximum_bytes < 1:
        raise ValueError("maximum_selected_bytes must be positive")
    encoded = text.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return text
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore")


def _passed(
    baseline: Baseline,
    case_id: str,
    phase: BenchmarkPhase,
    repetition: int,
    metric: BenchmarkMetric,
    unit: MetricUnit,
    value: int | float,
) -> BenchmarkObservation:
    provisional = BenchmarkObservation.model_construct(
        observation_id="sha256:" + "0" * 64,
        baseline=baseline,
        case_id=case_id,
        phase=phase,
        repetition=repetition,
        metric=metric,
        unit=unit,
        value=value,
        status=EvidenceStatus.PASSED,
    )
    return provisional.model_copy(
        update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
    )


def _safe_reason(reason: str) -> str:
    normalized = re.sub(r"[^a-z0-9._-]+", "-", reason.casefold()).strip("-")
    return normalized[:128] or "treatment-unavailable"


__all__ = [
    "BenchmarkCase",
    "BenchmarkTreatmentUnavailable",
    "NativeRetrievalTreatment",
    "NativeReuseTreatment",
    "OpenArdpCompilerTreatment",
    "OpenArdpRetrievalTreatment",
    "RawReparseTreatment",
    "ReleaseBenchmarkTreatment",
    "TreatmentResult",
    "UnavailableTreatment",
    "rejected_observation",
    "source_digest",
    "unavailable_observation",
]
