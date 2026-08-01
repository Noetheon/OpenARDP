"""Integration coverage for fair five-treatment release benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.adapters.release_benchmarks import (
    BenchmarkCase,
    BenchmarkTreatmentUnavailable,
    NativeRetrievalTreatment,
    NativeReuseTreatment,
    OpenArdpCompilerTreatment,
    OpenArdpRetrievalTreatment,
    RawReparseTreatment,
    UnavailableTreatment,
)
from openardp.domain.release import Baseline, BenchmarkMetric, BenchmarkPhase, EvidenceStatus
from openardp.services import release_benchmarks
from openardp.services.release_benchmarks import (
    ReleaseCorpusMalformed,
    load_benchmark_cases,
    run_benchmarks,
)

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks" / "release" / "v0.1.0"


class _Clock:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> int:
        self.value += 10
        return self.value


class _ReverseClock:
    def __init__(self) -> None:
        self.value = 100

    def __call__(self) -> int:
        self.value -= 1
        return self.value


def _treatments(clock: _Clock) -> list[object]:
    return [
        RawReparseTreatment(clock=clock),
        NativeReuseTreatment(clock=clock),
        NativeRetrievalTreatment(clock=clock),
        OpenArdpRetrievalTreatment(clock=clock),
        OpenArdpCompilerTreatment(clock=clock),
    ]


def test_frozen_cases_run_all_five_baselines_with_equal_inputs_and_instrumentation() -> None:
    """Produce raw samples, parser counts, storage and exact quality from one corpus."""
    cases = load_benchmark_cases(ROOT, CORPUS)
    observations = run_benchmarks(cases, _treatments(_Clock()), repetitions=7)  # type: ignore[arg-type]
    assert {
        item.case_id for item in observations if item.case_id != "optional-model-evaluator"
    } == {item.case_id for item in cases}
    assert {item.baseline for item in observations} == set(Baseline)
    assert all(
        item.status is EvidenceStatus.PASSED
        for item in observations
        if item.case_id != "optional-model-evaluator"
    )
    for case in cases:
        for baseline in Baseline:
            assert (
                sum(
                    item.baseline is baseline
                    and item.case_id == case.case_id
                    and item.metric is BenchmarkMetric.LATENCY
                    for item in observations
                )
                >= 7
            )
    for phase in (BenchmarkPhase.COLD, BenchmarkPhase.WARM, BenchmarkPhase.UPDATE):
        assert {
            item.baseline
            for item in observations
            if item.phase is phase and item.metric is BenchmarkMetric.LATENCY
        } == set(Baseline)
    quality = tuple(
        item.value
        for item in observations
        if item.metric in {BenchmarkMetric.CORRECTNESS, BenchmarkMetric.COVERAGE}
        and item.status is EvidenceStatus.PASSED
    )
    assert quality and set(quality) == {1.0}


def test_source_edit_invalidation_requires_explicit_prepare(tmp_path: Path) -> None:
    """Never reuse a projection after the source-edit boundary is invalidated."""
    source = tmp_path / "source.txt"
    source.write_text("alpha evidence", encoding="utf-8")
    case = BenchmarkCase("edited-case", "edited-case", source, ("alpha",), ("alpha",))
    treatment = NativeReuseTreatment(clock=_Clock())
    treatment.prepare(case)
    assert treatment.execute(case).selected_text == "alpha evidence"
    source.write_text("beta evidence", encoding="utf-8")
    treatment.invalidate(case.case_id)
    with pytest.raises(BenchmarkTreatmentUnavailable, match="native-representation-unavailable"):
        treatment.execute(case)
    treatment.prepare(case)
    assert treatment.execute(case).selected_text == "beta evidence"


def test_unavailable_treatment_and_cancellation_remain_explicit() -> None:
    """Retain an unavailable baseline and abort cooperatively without partial truth."""
    case = load_benchmark_cases(ROOT, CORPUS)[0]
    clock = _Clock()
    treatments = _treatments(clock)
    treatments[-1] = UnavailableTreatment(Baseline.OPENARDP_COMPILER, "model-assets-unavailable")
    observations = run_benchmarks(cases=(case,), treatments=treatments, repetitions=7)  # type: ignore[arg-type]
    unavailable = tuple(item for item in observations if item.status is EvidenceStatus.UNAVAILABLE)
    assert {item.reason for item in unavailable} == {
        "model-assets-unavailable",
        "optional-evaluator-unavailable",
    }
    with pytest.raises(InterruptedError, match="benchmark cancelled"):
        run_benchmarks(
            cases=(case,),
            treatments=_treatments(clock),  # type: ignore[arg-type]
            repetitions=1,
            cancelled=lambda: True,
        )


def test_malformed_corpus_digest_fails_before_treatment(tmp_path: Path) -> None:
    """Reject source drift instead of benchmarking unequal inputs."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for name in ("corpus-manifest.json", "judgments.json"):
        (corpus / name).write_bytes((CORPUS / name).read_bytes())
    manifest = json.loads((corpus / "corpus-manifest.json").read_bytes())
    manifest["judgments_sha256"] = "sha256:" + "0" * 64
    (corpus / "corpus-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ReleaseCorpusMalformed):
        load_benchmark_cases(ROOT, corpus)


def test_invalid_clock_sample_is_retained_as_rejected() -> None:
    """Keep an invalid timing sample visible instead of aborting or dropping a baseline."""
    case = load_benchmark_cases(ROOT, CORPUS)[0]
    treatments = _treatments(_Clock())
    treatments[0] = RawReparseTreatment(clock=_ReverseClock())
    observations = run_benchmarks((case,), treatments, repetitions=1)  # type: ignore[arg-type]
    rejected = tuple(item for item in observations if item.status is EvidenceStatus.REJECTED)
    assert len(rejected) == 1
    assert rejected[0].baseline is Baseline.RAW_REPARSE
    assert rejected[0].reason == "monotonic-clock-moved-backwards"


def test_environment_profile_handles_platforms_without_sysconf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep body-free platform evidence portable when POSIX sysconf is absent."""
    monkeypatch.delattr(release_benchmarks.os, "sysconf", raising=False)
    profile = release_benchmarks.environment_profile(reference_timing=False)
    assert profile.memory_gib_bucket == "unknown"
