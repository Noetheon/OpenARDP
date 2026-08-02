"""Pure policy and statistics tests for the F023 benchmark."""

from __future__ import annotations

from copy import deepcopy

from scripts.pdf_bundle_benchmark_evaluation import decide, summarize


def _protocol() -> dict[str, object]:
    return {
        "benchmark_version": "0.1.0",
        "expected_asset_bytes": 100,
        "expected_asset_file_count": 5,
        "expected_bundle_id": "bundle",
        "expected_package_id": "package",
        "expected_source_lock_id": "lock",
        "maximum_asset_bytes": 200,
        "maximum_package_overhead_bytes": 20,
        "maximum_validation_ns": 1_000,
        "maximum_validation_rss_bytes": 1_000,
        "retained_samples": 3,
        "validation_samples": 3,
    }


def _observations() -> dict[str, object]:
    return {
        "conversion_runs": [
            {
                "anchored_evidence_count": 2,
                "cache_state": "cold" if value == 10 else "warm",
                "cpu_ns": value + 1,
                "evidence_count": 2,
                "native_sha256": "native",
                "page_count": 1,
                "peak_rss_bytes": 50 + value,
                "pointer_evidence_count": 2,
                "wall_ns": value,
            }
            for value in (10, 20, 30)
        ],
        "installation": {
            "asset_bytes": 100,
            "asset_file_count": 5,
            "bundle_id": "bundle",
            "installation_bytes": 105,
            "source_lock_id": "lock",
        },
        "offline": {"cache": True, "network": True},
        "package": {"package_bytes": 110, "package_id": "package"},
        "provisioning": {
            "downloaded_bytes": 100,
            "downloaded_file_count": 5,
            "duration_ns": 1_000,
        },
        "validation_runs": [
            {
                "bundle_id": "bundle",
                "peak_rss_bytes": 100,
                "source_lock_id": "lock",
                "wall_ns": value,
            }
            for value in (100, 200, 300)
        ],
    }


def test_summary_uses_declared_robust_statistics_and_ready_policy() -> None:
    """Keep p50, nearest-rank p95, MAD and the closed decision deterministic."""
    protocol = _protocol()
    summary = summarize(_observations(), protocol)

    assert summary["conversion"]["wall_p50_ns"] == 20
    assert summary["conversion"]["wall_p95_ns"] == 30
    assert summary["conversion"]["wall_mad_ns"] == 10
    assert summary["conversion"]["wall_median_confidence_low_ns"] == 10
    assert summary["conversion"]["wall_median_confidence_high_ns"] == 30
    assert decide(summary, protocol)["decision"] == "PDF_OFFLINE_READY"


def test_unfavorable_result_is_retained_with_exact_failure_codes() -> None:
    """Fail closed instead of dropping or relabeling an unfavorable observation."""
    observations = deepcopy(_observations())
    observations["offline"]["network"] = False
    observations["conversion_runs"][1]["native_sha256"] = "drift"
    summary = summarize(observations, _protocol())
    decision = decide(summary, _protocol())

    assert decision["decision"] == "PDF_OFFLINE_NOT_READY"
    assert decision["failure_codes"] == [
        "correctness:deterministic_native",
        "offline:authority",
    ]
