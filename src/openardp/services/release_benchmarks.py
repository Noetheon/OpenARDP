"""Fair orchestration and body-free platform evidence for F015 benchmarks."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from openardp.adapters.release_benchmarks import (
    BenchmarkCase,
    BenchmarkTreatmentUnavailable,
    ReleaseBenchmarkTreatment,
    rejected_observation,
    unavailable_observation,
)
from openardp.adapters.release_evidence import inventory_source_tree
from openardp.domain.identity import canonical_sha256
from openardp.domain.release import (
    Baseline,
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPhase,
    EnvironmentProfile,
    EvidenceCheck,
    EvidenceStatus,
    EvidenceSuite,
    MetricUnit,
    PlatformEvidence,
    ReleaseGatePolicy,
    SuiteName,
    benchmark_observation_id,
    platform_evidence_id,
)

CancellationCheck = Callable[[], bool]


class ReleaseCorpusMalformed(ValueError):
    """Raised when frozen corpus bytes do not match the committed manifest."""


def load_benchmark_cases(repository_root: Path, corpus: Path) -> tuple[BenchmarkCase, ...]:
    """Load exact judged cases after validating manifest paths, sizes and digests."""
    root = repository_root.resolve(strict=True)
    corpus_root = corpus.resolve(strict=True)
    manifest_bytes = _read_regular(corpus_root / "corpus-manifest.json", 4 * 1024 * 1024)
    judgments_bytes = _read_regular(corpus_root / "judgments.json", 4 * 1024 * 1024)
    manifest = _closed_json(manifest_bytes)
    judgments = _closed_json(judgments_bytes)
    if manifest.get("corpus_version") != "0.1.0" or judgments.get("judgment_version") != "0.1.0":
        raise ReleaseCorpusMalformed("unsupported corpus or judgment version")
    if manifest.get("judgments_sha256") != _digest(judgments_bytes):
        raise ReleaseCorpusMalformed("judgment digest mismatch")
    records = manifest.get("records")
    cases = judgments.get("cases")
    budgets = judgments.get("budgets")
    if (
        not isinstance(records, list)
        or not isinstance(cases, list)
        or not isinstance(budgets, list)
    ):
        raise ReleaseCorpusMalformed("corpus collections are malformed")
    budget_values = tuple(
        (
            _required_string(_mapping(item), "budget_id"),
            _required_int(_mapping(item), "maximum_bytes"),
        )
        for item in budgets
    )
    if len({item[0] for item in budget_values}) != len(budget_values):
        raise ReleaseCorpusMalformed("budget identifiers are duplicate")
    by_case: dict[str, Mapping[str, Any]] = {}
    for raw in records:
        record = _mapping(raw)
        case_id = _required_string(record, "case_id")
        if case_id in by_case:
            raise ReleaseCorpusMalformed("duplicate corpus case")
        by_case[case_id] = record
    loaded: list[BenchmarkCase] = []
    seen: set[str] = set()
    for raw in cases:
        judgment = _mapping(raw)
        case_id = _required_string(judgment, "case_id")
        if case_id in seen or case_id not in by_case:
            raise ReleaseCorpusMalformed("judgment case is duplicate or absent")
        seen.add(case_id)
        record = by_case[case_id]
        relative = PureRepositoryPath(_required_string(record, "path"))
        source = (root / relative.value).resolve(strict=True)
        if not source.is_relative_to(root):
            raise ReleaseCorpusMalformed("corpus source escapes repository")
        data = _read_regular(source, 16 * 1024 * 1024)
        if len(data) != _required_int(record, "byte_length") or _digest(data) != _required_string(
            record, "sha256"
        ):
            raise ReleaseCorpusMalformed("corpus source digest mismatch")
        terms = _string_tuple(judgment.get("expected_terms"))
        evidence_ids = _string_tuple(judgment.get("expected_evidence_ids"))
        anchors = _string_tuple(judgment.get("expected_anchors"))
        if len(evidence_ids) != len(anchors):
            raise ReleaseCorpusMalformed("judgment evidence and anchors are misaligned")
        for budget_id, maximum_bytes in budget_values:
            loaded.append(
                BenchmarkCase(
                    case_id=f"{case_id}-budget-{budget_id}",
                    source_case_id=case_id,
                    source=source,
                    query_terms=terms,
                    expected_terms=terms,
                    expected_evidence_ids=evidence_ids,
                    expected_anchors=anchors,
                    maximum_selected_bytes=maximum_bytes,
                )
            )
    if not loaded:
        raise ReleaseCorpusMalformed("judged corpus is empty")
    return tuple(sorted(loaded, key=lambda item: item.case_id))


def run_benchmarks(
    cases: Sequence[BenchmarkCase],
    treatments: Sequence[ReleaseBenchmarkTreatment],
    *,
    repetitions: int,
    warmups: int = 1,
    cancelled: CancellationCheck = lambda: False,
) -> tuple[BenchmarkObservation, ...]:
    """Run every case/treatment fairly and retain unavailable outcomes."""
    if repetitions < 1 or warmups < 0:
        raise ValueError("benchmark repetitions must be positive and warmups non-negative")
    observed_baselines = tuple(item.baseline for item in treatments)
    if len(set(observed_baselines)) != len(observed_baselines) or set(observed_baselines) != set(
        Baseline
    ):
        raise ValueError("exactly one treatment for every baseline is required")
    observations: list[BenchmarkObservation] = []
    for case in cases:
        if cancelled():
            raise InterruptedError("benchmark cancelled")
        for treatment in treatments:
            try:
                treatment.prepare(case)
                for _ in range(warmups):
                    treatment.run_case(case, repetition=0)
                for repetition in range(repetitions):
                    if cancelled():
                        raise InterruptedError("benchmark cancelled")
                    observations.extend(
                        treatment.lifecycle_observations(case, repetition=repetition)
                    )
                    observations.extend(treatment.run_case(case, repetition=repetition))
            except BenchmarkTreatmentUnavailable as error:
                observations.append(
                    unavailable_observation(
                        treatment.baseline,
                        case.case_id,
                        0,
                        str(error),
                    )
                )
            except ValueError as error:
                observations.append(
                    rejected_observation(
                        treatment.baseline,
                        case.case_id,
                        0,
                        str(error),
                    )
                )
    observations.append(
        _unavailable_quality_observation(
            baseline=Baseline.OPENARDP_COMPILER,
            case_id="optional-model-evaluator",
            reason="optional-evaluator-unavailable",
        )
    )
    keys = tuple(item.key for item in observations)
    if len(keys) != len(set(keys)):
        raise ValueError("benchmark emitted duplicate observation keys")
    return tuple(observations)


def _unavailable_quality_observation(
    *, baseline: Baseline, case_id: str, reason: str
) -> BenchmarkObservation:
    provisional = BenchmarkObservation.model_construct(
        observation_id="sha256:" + "0" * 64,
        baseline=baseline,
        case_id=case_id,
        phase=BenchmarkPhase.REPLAY,
        repetition=0,
        metric=BenchmarkMetric.CORRECTNESS,
        unit=MetricUnit.RATIO,
        value=None,
        status=EvidenceStatus.UNAVAILABLE,
        reason=reason,
    )
    return provisional.model_copy(
        update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
    )


def environment_profile(*, reference_timing: bool) -> EnvironmentProfile:
    """Return a redacted platform profile without host, user or path facts."""
    os_family = _os_family()
    architecture = _safe_architecture(platform.machine())
    return EnvironmentProfile(
        platform_id=os_family,
        os_family=os_family,
        architecture=architecture,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        logical_cpu_bucket=_cpu_bucket(os.cpu_count()),
        memory_gib_bucket=_memory_bucket(_physical_memory_bytes()),
        timer_resolution_ns=max(1, round(time.get_clock_info("monotonic").resolution * 1e9)),
        reference_timing=reference_timing,
    )


def build_platform_evidence(
    *,
    repository_root: Path,
    corpus: Path,
    observations: Sequence[BenchmarkObservation],
    suite_results: Mapping[SuiteName, Sequence[EvidenceCheck]],
    reference_timing: bool,
) -> PlatformEvidence:
    """Bind observations and explicit suite assertions to exact candidate inputs."""
    root = repository_root.resolve(strict=True)
    source_tree = inventory_source_tree(root, _source_policy(corpus))
    protocol_id = _digest(_read_regular(corpus / "protocol.json", 1024 * 1024))
    corpus_id = canonical_sha256(
        {
            "manifest": _closed_json(
                _read_regular(corpus / "corpus-manifest.json", 4 * 1024 * 1024)
            ),
            "judgments": _closed_json(_read_regular(corpus / "judgments.json", 4 * 1024 * 1024)),
        }
    )
    configuration_id = canonical_sha256(
        {
            "configuration_version": "0.1.0",
            "repetitions": 7,
            "warmups": 1,
        }
    )
    lockfile_id = _digest(_read_regular(root / "uv.lock", 16 * 1024 * 1024))
    environment = environment_profile(reference_timing=reference_timing)
    bound_observations = _bind_observations(
        observations,
        corpus=corpus,
        source_tree_id=source_tree.source_tree_id,
        protocol_id=protocol_id,
        corpus_id=corpus_id,
        configuration_id=configuration_id,
        lockfile_id=lockfile_id,
        environment=environment,
    )
    required_checks = ReleaseGatePolicy.model_validate_json(
        _read_regular(corpus / "gate-policy.json", 1024 * 1024)
    ).required_checks
    suites = _build_suites(bound_observations, suite_results, required_checks)
    provisional = PlatformEvidence(
        evidence_id="sha256:" + "0" * 64,
        source_tree_id=source_tree.source_tree_id,
        protocol_id=protocol_id,
        corpus_id=corpus_id,
        configuration_id=configuration_id,
        lockfile_id=lockfile_id,
        environment=environment,
        baselines=tuple(Baseline),
        observations=bound_observations,
        suites=suites,
    )
    return provisional.model_copy(
        update={"evidence_id": platform_evidence_id(provisional.identity_projection)}
    )


def _bind_observations(
    observations: Sequence[BenchmarkObservation],
    *,
    corpus: Path,
    source_tree_id: str,
    protocol_id: str,
    corpus_id: str,
    configuration_id: str,
    lockfile_id: str,
    environment: EnvironmentProfile,
) -> tuple[BenchmarkObservation, ...]:
    manifest = _closed_json(_read_regular(corpus / "corpus-manifest.json", 4 * 1024 * 1024))
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ReleaseCorpusMalformed("corpus records are malformed")
    source_ids = {
        _required_string(_mapping(item), "case_id"): _required_string(_mapping(item), "sha256")
        for item in records
    }
    bound: list[BenchmarkObservation] = []
    for observation in observations:
        source_case_id = observation.case_id.split("-budget-", maxsplit=1)[0]
        source_version_id = source_ids.get(source_case_id, corpus_id)
        provisional = observation.model_copy(
            update={
                "observation_id": "sha256:" + "0" * 64,
                "source_version_id": source_version_id,
                "protocol_id": protocol_id,
                "corpus_id": corpus_id,
                "configuration_id": configuration_id,
                "executable_id": source_tree_id,
                "lockfile_id": lockfile_id,
                "platform_id": environment.platform_id,
                "python_version": environment.python_version,
            }
        )
        bound.append(
            provisional.model_copy(
                update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
            )
        )
    return tuple(bound)


def _build_suites(
    observations: Sequence[BenchmarkObservation],
    suite_results: Mapping[SuiteName, Sequence[EvidenceCheck]],
    required_checks: Mapping[SuiteName, Sequence[str]],
) -> tuple[EvidenceSuite, ...]:
    performance_checks = tuple(
        EvidenceCheck(
            check_id=f"baseline-{baseline.value}",
            status=(
                EvidenceStatus.PASSED
                if any(
                    item.baseline is baseline and item.status is EvidenceStatus.PASSED
                    for item in observations
                )
                else EvidenceStatus.FAILED
            ),
            reason=(
                None
                if any(
                    item.baseline is baseline and item.status is EvidenceStatus.PASSED
                    for item in observations
                )
                else "baseline-unavailable"
            ),
            evidence_ids=tuple(
                item.observation_id
                for item in observations
                if item.baseline is baseline and item.status is EvidenceStatus.PASSED
            ),
        )
        for baseline in Baseline
    )
    performance_checks = (
        *performance_checks,
        _phase_check("lifecycle-cold", observations, BenchmarkPhase.COLD),
        _phase_check("lifecycle-warm", observations, BenchmarkPhase.WARM),
        _phase_check("lifecycle-update", observations, BenchmarkPhase.UPDATE),
        _metric_check(
            "deterministic-replay", observations, BenchmarkMetric.REPLAY_MATCH, exact=1.0
        ),
        _metric_check("storage-overhead", observations, BenchmarkMetric.STORAGE_BYTES),
    )
    correctness_checks = (
        _metric_check("precision-complete", observations, BenchmarkMetric.PRECISION, exact=1.0),
        _metric_check("recall-complete", observations, BenchmarkMetric.RECALL, exact=1.0),
        _metric_check(
            "reciprocal-rank-complete",
            observations,
            BenchmarkMetric.RECIPROCAL_RANK,
            exact=1.0,
        ),
        _metric_check(
            "anchor-correctness-complete",
            observations,
            BenchmarkMetric.ANCHOR_CORRECTNESS,
            exact=1.0,
        ),
        _three_budget_check(observations),
        _metric_check(
            "stale-rejection-complete",
            observations,
            BenchmarkMetric.STALE_REJECTION,
            exact=1.0,
        ),
        _abstention_check(observations),
    )
    merged: dict[SuiteName, tuple[EvidenceCheck, ...]] = {
        SuiteName.PERFORMANCE: performance_checks,
        SuiteName.CORRECTNESS: correctness_checks,
    }
    for suite in SuiteName:
        if suite not in merged:
            supplied = {item.check_id: item for item in suite_results.get(suite, ())}
            merged[suite] = tuple(
                supplied.get(check_id)
                or EvidenceCheck(
                    check_id=check_id,
                    status=EvidenceStatus.UNAVAILABLE,
                    reason="suite-evidence-unavailable",
                )
                for check_id in required_checks[suite]
            )
    return tuple(_suite(name, merged[name]) for name in SuiteName)


def _phase_check(
    check_id: str,
    observations: Sequence[BenchmarkObservation],
    phase: BenchmarkPhase,
) -> EvidenceCheck:
    selected = tuple(
        item
        for item in observations
        if item.phase is phase and item.metric is BenchmarkMetric.LATENCY
    )
    passed = (
        bool(selected)
        and {item.baseline for item in selected} == set(Baseline)
        and all(item.status is EvidenceStatus.PASSED for item in selected)
    )
    return EvidenceCheck(
        check_id=check_id,
        status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
        reason=None if passed else "lifecycle-phase-incomplete",
        observed=len({item.baseline for item in selected}),
        expected=len(Baseline),
        evidence_ids=tuple(item.observation_id for item in selected),
    )


def _metric_check(
    check_id: str,
    observations: Sequence[BenchmarkObservation],
    metric: BenchmarkMetric,
    *,
    exact: float | None = None,
) -> EvidenceCheck:
    selected = tuple(item for item in observations if item.metric is metric)
    passed = bool(selected) and all(
        item.status is EvidenceStatus.PASSED
        and item.value is not None
        and (exact is None or float(item.value) == exact)
        for item in selected
    )
    return EvidenceCheck(
        check_id=check_id,
        status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
        reason=None if passed else "metric-evidence-incomplete",
        observed=sum(item.status is EvidenceStatus.PASSED for item in selected),
        expected=len(selected) or 1,
        evidence_ids=tuple(item.observation_id for item in selected),
    )


def _three_budget_check(observations: Sequence[BenchmarkObservation]) -> EvidenceCheck:
    selected = tuple(
        item
        for item in observations
        if item.metric is BenchmarkMetric.COVERAGE and item.baseline is Baseline.OPENARDP_COMPILER
    )
    budget_ids = {
        budget
        for item in selected
        for budget in (item.case_id.rsplit("-budget-", maxsplit=1)[-1],)
        if "-budget-" in item.case_id
    }
    passed = budget_ids == {"small", "medium", "large"} and all(
        item.status is EvidenceStatus.PASSED and item.value == 1.0 for item in selected
    )
    return EvidenceCheck(
        check_id="three-budget-coverage",
        status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
        reason=None if passed else "budget-evidence-incomplete",
        observed=len(budget_ids),
        expected=3,
        evidence_ids=tuple(item.observation_id for item in selected),
    )


def _abstention_check(observations: Sequence[BenchmarkObservation]) -> EvidenceCheck:
    selected = tuple(
        item
        for item in observations
        if item.case_id == "optional-model-evaluator" and item.status is EvidenceStatus.UNAVAILABLE
    )
    passed = len(selected) == 1 and selected[0].reason == "optional-evaluator-unavailable"
    return EvidenceCheck(
        check_id="evaluator-abstention-explicit",
        status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
        reason=None if passed else "evaluator-abstention-missing",
        observed=len(selected),
        expected=1,
        evidence_ids=tuple(item.observation_id for item in selected),
    )


def _suite(name: SuiteName, checks: Sequence[EvidenceCheck]) -> EvidenceSuite:
    passed = bool(checks) and all(item.status is EvidenceStatus.PASSED for item in checks)
    return EvidenceSuite(
        name=name,
        status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
        expected_count=len(checks),
        observed_count=len(checks),
        checks=tuple(checks),
    )


class PureRepositoryPath:
    """Validated portable repository-relative path."""

    def __init__(self, value: str) -> None:
        candidate = Path(value)
        if not value or candidate.is_absolute() or "\\" in value or ".." in candidate.parts:
            raise ReleaseCorpusMalformed("corpus path is not portable")
        self.value = value


def _source_policy(corpus: Path) -> tuple[str, ...]:
    policy = _closed_json(_read_regular(corpus / "source-tree-policy.json", 1024 * 1024))
    paths = policy.get("allowed_paths")
    if not isinstance(paths, list):
        raise ReleaseCorpusMalformed("source-tree policy is malformed")
    return _string_tuple(paths)


def _closed_json(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data, object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseCorpusMalformed("release input is not strict JSON") from error
    if not isinstance(value, dict):
        raise ReleaseCorpusMalformed("release input must be a JSON object")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReleaseCorpusMalformed("duplicate JSON key")
        value[key] = item
    return value


def _read_regular(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ReleaseCorpusMalformed("release input is not a regular file")
    size = path.stat().st_size
    if size > maximum:
        raise ReleaseCorpusMalformed("release input exceeds size limit")
    data = path.read_bytes()
    if len(data) != size:
        raise ReleaseCorpusMalformed("release input changed during read")
    return data


def _digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ReleaseCorpusMalformed("expected JSON object")
    return value


def _required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ReleaseCorpusMalformed(f"{key} must be a non-empty string")
    return item


def _required_int(value: Mapping[str, Any], key: str) -> int:
    item = value.get(key)
    if type(item) is not int or item < 0:
        raise ReleaseCorpusMalformed(f"{key} must be a non-negative integer")
    return item


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
        raise ReleaseCorpusMalformed("expected non-empty string list")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise ReleaseCorpusMalformed("string list must be unique")
    return result


def _os_family() -> Literal["linux", "macos", "windows"]:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    raise RuntimeError("unsupported release evidence platform")


def _safe_architecture(value: str) -> str:
    cleaned = "".join(char.casefold() if char.isalnum() else "-" for char in value).strip("-")
    return cleaned[:128] or "unknown"


def _cpu_bucket(
    value: int | None,
) -> Literal["unknown", "1", "2", "3-4", "5-8", "9-16", "17+"]:
    if value is None:
        return "unknown"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    if value <= 4:
        return "3-4"
    if value <= 8:
        return "5-8"
    if value <= 16:
        return "9-16"
    return "17+"


def _physical_memory_bytes() -> int | None:
    sysconf = getattr(os, "sysconf", None)
    if not callable(sysconf):
        return None
    try:
        pages = sysconf("SC_PHYS_PAGES")
        page_size = sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        return None
    if not isinstance(pages, int) or not isinstance(page_size, int):
        return None
    return pages * page_size


def _memory_bucket(
    value: int | None,
) -> Literal["unknown", "<4", "4-7", "8-15", "16-31", "32-63", "64+"]:
    if value is None:
        return "unknown"
    gib = value / (1024**3)
    if gib < 4:
        return "<4"
    if gib < 8:
        return "4-7"
    if gib < 16:
        return "8-15"
    if gib < 32:
        return "16-31"
    if gib < 64:
        return "32-63"
    return "64+"


__all__ = [
    "ReleaseCorpusMalformed",
    "build_platform_evidence",
    "environment_profile",
    "load_benchmark_cases",
    "run_benchmarks",
]
