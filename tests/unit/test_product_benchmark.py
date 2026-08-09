"""Unit contracts for the F020 product-value benchmark."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.adapters.product_benchmarks import (
    corpus_token,
    generate_text_corpus,
    load_benchmark_inputs,
)
from openardp.domain.product_benchmark import (
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPhase,
    BenchmarkProfile,
    BenchmarkTreatment,
    MetricUnit,
    ObservationStatus,
    ValueOutcome,
    make_observation,
)
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.ports.parser import RichParserModelAssetsInvalid
from scripts.product_benchmark_evaluation import (
    decide_value,
    summarize_timing,
)
from scripts.product_benchmark_runner import execute_product_benchmark


def _inputs(repository_root: Path):
    return load_benchmark_inputs(repository_root / "benchmarks/product-value/v0.1.0")


def _timing(value: int, repetition: int) -> BenchmarkObservation:
    return make_observation(
        protocol_id="sha256:" + "1" * 64,
        corpus_id="sha256:" + "2" * 64,
        policy_id="sha256:" + "3" * 64,
        environment_id="sha256:" + "4" * 64,
        profile=BenchmarkProfile.SMOKE,
        workload_id="search-smoke",
        treatment=BenchmarkTreatment.OPENARDP,
        phase=BenchmarkPhase.SEARCH,
        metric=BenchmarkMetric.LATENCY,
        unit=MetricUnit.NANOSECONDS,
        repetition=repetition,
        value=value,
    )


def test_observation_identity_and_metric_units_are_closed() -> None:
    """Reject tampered identities, non-finite values and metric/unit drift."""
    observation = _timing(123, 0)
    assert observation.status is ObservationStatus.PASSED
    assert observation.observation_id.startswith("sha256:")
    with pytest.raises(ValidationError, match="identity"):
        BenchmarkObservation.model_validate(
            observation.model_copy(update={"observation_id": "sha256:" + "f" * 64})
        )
    with pytest.raises(ValidationError, match="unit"):
        BenchmarkObservation.model_validate(
            observation.model_copy(update={"unit": MetricUnit.BYTES})
        )
    with pytest.raises(ValueError):
        make_observation(
            protocol_id="sha256:" + "1" * 64,
            corpus_id="sha256:" + "2" * 64,
            policy_id="sha256:" + "3" * 64,
            environment_id="sha256:" + "4" * 64,
            profile=BenchmarkProfile.SMOKE,
            workload_id="bad",
            treatment=BenchmarkTreatment.OPENARDP,
            phase=BenchmarkPhase.SEARCH,
            metric=BenchmarkMetric.LATENCY,
            unit=MetricUnit.NANOSECONDS,
            repetition=0,
            value=float("nan"),
        )


def test_unavailable_observation_requires_closed_reason() -> None:
    """Keep unavailable capability visible without a fabricated numeric value."""
    observation = make_observation(
        protocol_id="sha256:" + "1" * 64,
        corpus_id="sha256:" + "2" * 64,
        policy_id="sha256:" + "3" * 64,
        environment_id="sha256:" + "4" * 64,
        profile=BenchmarkProfile.REFERENCE,
        workload_id="rich-pdf",
        treatment=BenchmarkTreatment.OPENARDP,
        phase=BenchmarkPhase.PREPARE,
        metric=BenchmarkMetric.LATENCY,
        unit=MetricUnit.NANOSECONDS,
        repetition=0,
        status=ObservationStatus.UNAVAILABLE,
        reason_code="pdf-model-bundle-unavailable",
    )
    assert observation.value is None
    with pytest.raises(ValidationError):
        BenchmarkObservation.model_validate(
            observation.model_copy(update={"reason_code": "contains spaces"})
        )


def test_inputs_are_closed_and_identity_bearing(repository_root: Path, tmp_path: Path) -> None:
    """Load the frozen input quartet and reject duplicate JSON member names."""
    inputs = _inputs(repository_root)
    assert inputs.protocol.protocol_version == "0.1.0"
    assert inputs.corpus.profiles[BenchmarkProfile.SCALE].block_count == 100_000
    assert inputs.protocol_id.startswith("sha256:")
    malformed = tmp_path / "inputs"
    malformed.mkdir()
    for source in (repository_root / "benchmarks/product-value/v0.1.0").glob("*.json"):
        (malformed / source.name).write_bytes(source.read_bytes())
    (malformed / "protocol.json").write_text(
        '{"protocol_version":"0.1.0","protocol_version":"0.1.0"}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_benchmark_inputs(malformed)


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (BenchmarkProfile.SMOKE, 100),
        (BenchmarkProfile.REFERENCE, 10_000),
        (BenchmarkProfile.SCALE, 100_000),
    ],
)
def test_generated_corpus_is_deterministic_and_exact(
    repository_root: Path,
    tmp_path: Path,
    profile: BenchmarkProfile,
    expected: int,
) -> None:
    """Generate exact block counts and identical bytes in independent roots."""
    inputs = _inputs(repository_root)
    first = generate_text_corpus(inputs, profile, tmp_path / "first")
    second = generate_text_corpus(inputs, profile, tmp_path / "second")
    assert first.block_count == expected
    assert first.source_sha256 == second.source_sha256
    assert first.source.read_bytes() == second.source.read_bytes()
    for ordinal in inputs.corpus.profiles[profile].query_ordinals:
        assert corpus_token(inputs.corpus.seed, ordinal) in first.source.read_text(encoding="utf-8")


def test_timing_summary_is_deterministic_and_sample_sufficient() -> None:
    """Compute stable p50/p95/MAD/bootstrap intervals from retained raw samples."""
    observations = tuple(_timing(value, index) for index, value in enumerate(range(10, 80, 10)))
    first = summarize_timing(observations, minimum_samples=7, bootstrap_resamples=1_000)
    second = summarize_timing(observations, minimum_samples=7, bootstrap_resamples=1_000)
    assert first == second
    assert first.sample_count == 7
    assert first.p50 == 40
    assert first.p95 == 70
    assert first.median_absolute_deviation == 20
    assert first.confidence_low <= first.p50 <= first.confidence_high
    with pytest.raises(ValueError, match="insufficient"):
        summarize_timing(observations[:6], minimum_samples=7, bootstrap_resamples=100)


def test_rich_fixture_inventory_is_exact_and_immutable(repository_root: Path) -> None:
    """Bind every actual rich fixture to the frozen format and SHA-256 inventory."""
    inputs = _inputs(repository_root)
    assert tuple(item.format for item in inputs.corpus.rich_fixtures) == (
        "docx",
        "pdf",
        "pptx",
    )
    for fixture in inputs.corpus.rich_fixtures:
        payload = (repository_root / fixture.path).read_bytes()
        assert "sha256:" + hashlib.sha256(payload).hexdigest() == fixture.sha256


def test_interrupted_run_never_publishes_partial_evidence(
    repository_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clean staging and work roots when execution is interrupted before publication."""
    from scripts import product_benchmark_runner

    def interrupt(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(product_benchmark_runner, "_run_text_profile", interrupt)
    output = tmp_path / "result"
    with pytest.raises(KeyboardInterrupt):
        execute_product_benchmark(
            repository_root,
            profile=BenchmarkProfile.SMOKE,
            output=output,
        )
    assert not output.exists()
    assert tuple(tmp_path.iterdir()) == ()


def test_rich_preflight_binds_pdf_assets_only_to_pdf(
    repository_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepare all formats together without granting PDF assets to Office parsers."""
    from scripts import product_benchmark_runner

    configurations: list[tuple[Path | None, ModelBundleManifest | None]] = []

    class FakeAdapter:
        def __init__(
            self,
            *,
            model_root: Path | None = None,
            model_manifest: ModelBundleManifest | None = None,
        ) -> None:
            configurations.append((model_root, model_manifest))

    manifest = ModelBundleManifest(bundle_name="test", bundle_version="1", files=())
    monkeypatch.setattr(product_benchmark_runner, "IsolatedDoclingAdapter", FakeAdapter)

    parsers = product_benchmark_runner._preflight_rich(
        repository_root,
        _inputs(repository_root),
        model_root=tmp_path,
        model_manifest=manifest,
    )

    assert configurations == [(None, None), (tmp_path, manifest), (None, None)]
    assert len({id(parser) for parser in parsers.values()}) == 3


def test_invalid_rich_preflight_runs_before_text_and_creates_no_work(
    repository_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject invalid rich configuration before any costly text phase or staging."""
    from scripts import product_benchmark_runner

    text_started = False

    def reject(*_args: object, **_kwargs: object) -> None:
        raise RichParserModelAssetsInvalid("secret /Users/example/private.pdf")

    def observe_text(*_args: object, **_kwargs: object) -> None:
        nonlocal text_started
        text_started = True

    monkeypatch.setattr(product_benchmark_runner, "_preflight_rich", reject)
    monkeypatch.setattr(product_benchmark_runner, "_run_text_profile", observe_text)
    output = tmp_path / "result"

    with pytest.raises(RichParserModelAssetsInvalid):
        execute_product_benchmark(
            repository_root,
            profile=BenchmarkProfile.REFERENCE,
            output=output,
        )

    assert not text_started
    assert not output.exists()
    assert tuple(tmp_path.iterdir()) == ()


def test_non_rich_profile_skips_rich_preflight(
    repository_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not validate optional PDF assets for a profile that has no rich work."""
    from scripts import product_benchmark_runner

    class TextStarted(RuntimeError):
        pass

    def reject_preflight(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("rich preflight must not run")

    def stop_at_text(*_args: object, **_kwargs: object) -> None:
        raise TextStarted

    monkeypatch.setattr(product_benchmark_runner, "_preflight_rich", reject_preflight)
    monkeypatch.setattr(product_benchmark_runner, "_run_text_profile", stop_at_text)

    with pytest.raises(TextStarted):
        execute_product_benchmark(
            repository_root,
            profile=BenchmarkProfile.SCALE,
            output=tmp_path / "result",
        )

    assert tuple(tmp_path.iterdir()) == ()


def test_value_policy_hard_failures_dominate_performance(repository_root: Path) -> None:
    """Never turn stale or incorrect evidence into conditional or favorable value."""
    inputs = _inputs(repository_root)
    favorable = {
        "anchor_correctness": 1.0,
        "context_coverage": 1.0,
        "precision": 1.0,
        "recall": 1.0,
        "replay_match": 1.0,
        "stale_incidents": 0,
        "unchanged_parser_invocations": 0,
        "reference_blocks": 10_000,
        "scale_blocks": 100_000,
        "search_p95_ns_at_100k": 1,
        "status_p95_ns": 1,
        "context_selected_native_ratio": 0.1,
        "break_even": 2,
        "rich_formats": ("docx", "pdf", "pptx"),
        "complete": True,
    }
    assert decide_value(inputs, favorable).outcome is ValueOutcome.WORTHWHILE
    unsafe = dict(favorable, stale_incidents=1)
    decision = decide_value(inputs, unsafe)
    assert decision.outcome is ValueOutcome.NOT_DEMONSTRATED
    assert "stale-evidence-served" in decision.reason_codes


def test_missing_pdf_or_scale_is_conditionally_worthwhile(repository_root: Path) -> None:
    """Preserve useful safe reuse while making incomplete capability prominent."""
    inputs = _inputs(repository_root)
    metrics = {
        "anchor_correctness": 1.0,
        "context_coverage": 1.0,
        "precision": 1.0,
        "recall": 1.0,
        "replay_match": 1.0,
        "stale_incidents": 0,
        "unchanged_parser_invocations": 0,
        "reference_blocks": 10_000,
        "scale_blocks": 0,
        "search_p95_ns_at_100k": None,
        "status_p95_ns": 1,
        "context_selected_native_ratio": 0.1,
        "break_even": 2,
        "rich_formats": ("docx", "pptx"),
        "complete": False,
    }
    decision = decide_value(inputs, metrics)
    assert decision.outcome is ValueOutcome.CONDITIONALLY_WORTHWHILE
    assert decision.reason_codes == (
        "pdf-unavailable",
        "scale-target-not-completed",
        "benchmark-incomplete",
    )


def test_normative_inputs_are_json_without_runtime_results(repository_root: Path) -> None:
    """Keep policy inputs inspectable and independent from measured output."""
    root = repository_root / "benchmarks/product-value/v0.1.0"
    names = {path.name for path in root.glob("*.json")}
    assert names == {"corpus-spec.json", "judgments.json", "protocol.json", "value-policy.json"}
    for path in root.glob("*.json"):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
