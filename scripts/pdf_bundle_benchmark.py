"""Body-free producer for the F023 offline PDF readiness benchmark."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from scripts.pdf_bundle_benchmark_evaluation import decide, render_report, summarize
except ModuleNotFoundError:
    from pdf_bundle_benchmark_evaluation import decide, render_report, summarize

from openardp.adapters.docling_bundle import verify_installation
from openardp.adapters.docling_bundle_archive import install_bundle_package
from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.rich_ingestion import ModelBundleManifest, RichMediaType, RichParserLimits

RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _rss_bytes(value: int) -> int:
    return value if sys.platform == "darwin" else value * 1024


def _convert(
    adapter: IsolatedDoclingAdapter,
    source: bytes,
    repetition: int,
) -> dict[str, Any]:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter_ns()
    output = adapter.parse((source,), media_type=RichMediaType.PDF.value)
    wall_ns = time.perf_counter_ns() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_ns = round(
        ((after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)) * 1_000_000_000
    )
    native = output.canonical_native_bytes
    return {
        "anchored_evidence_count": sum(item.anchor is not None for item in output.candidates),
        "cpu_ns": cpu_ns,
        "cache_state": "cold" if repetition == 0 else "warm",
        "evidence_count": len(output.candidates),
        "native_bytes": len(native),
        "native_sha256": _sha256(native),
        "page_count": len(output.native_document["pages"]),
        "peak_rss_bytes": _rss_bytes(after.ru_maxrss),
        "pointer_evidence_count": sum(
            item.native_pointer.pointer.startswith("#/") for item in output.candidates
        ),
        "repetition": repetition,
        "wall_ns": wall_ns,
    }


def _validate_sample(bundle: Path, lock_path: Path, repetition: int) -> dict[str, Any]:
    """Measure one exact offline installation validation."""
    started = time.perf_counter_ns()
    result = verify_installation(bundle, expected_source_lock=lock_path)
    wall_ns = time.perf_counter_ns() - started
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "bundle_id": result.bundle_id,
        "peak_rss_bytes": _rss_bytes(usage.ru_maxrss),
        "repetition": repetition,
        "source_lock_id": result.source_lock_id,
        "wall_ns": wall_ns,
    }


def _file_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {"byte_length": len(payload), "name": path.name, "sha256": _sha256(payload)}


def execute(
    repository_root: Path,
    *,
    bundle: Path,
    package: Path,
    provision_duration_ns: int,
    output: Path,
) -> dict[str, Any]:
    """Execute, evaluate and atomically publish the complete reference result."""
    root = repository_root.resolve(strict=True)
    if output.exists() or output.is_symlink():
        raise FileExistsError("benchmark output already exists")
    benchmark_root = root / "benchmarks/pdf-bundle/v0.1.0"
    protocol = json.loads((benchmark_root / "protocol.json").read_bytes())
    lock_path = root / "model-bundles/pdf-docling-2.114.0-v1/source-lock.json"
    fixture = root / protocol["fixture_path"]
    source = fixture.read_bytes()
    installation = verify_installation(bundle, expected_source_lock=lock_path)
    manifest = ModelBundleManifest.model_validate_json((bundle / "manifest.json").read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="f023-result-", dir=output.parent))
    work = Path(tempfile.mkdtemp(prefix="f023-work-", dir=output.parent))
    started = time.monotonic_ns()
    try:
        package_result = install_bundle_package(
            package,
            work / "offline-install",
            expected_source_lock=lock_path,
        )
        adapter = IsolatedDoclingAdapter(
            limits=RichParserLimits(timeout_seconds=180.0),
            model_root=bundle / "assets",
            model_manifest=manifest,
        )
        for repetition in range(int(protocol["warmup_samples"])):
            _convert(adapter, source, -(repetition + 1))
        runs = [
            _convert(adapter, source, repetition)
            for repetition in range(int(protocol["retained_samples"]))
        ]
        observations = {
            "benchmark_version": protocol["benchmark_version"],
            "conversion_runs": runs,
            "environment": {
                "architecture": platform.machine().lower(),
                "os_family": platform.system().lower(),
                "python_version": ".".join(map(str, sys.version_info[:3])),
            },
            "fixture": {"byte_length": len(source), "sha256": _sha256(source)},
            "installation": installation.model_dump(mode="json"),
            "offline": {
                "external_model_root_explicit": True,
                "fresh_private_provider_cache_per_worker": True,
                "socket_denied_before_provider_import": True,
            },
            "package": package_result.model_dump(mode="json"),
            "provisioning": {
                "downloaded_bytes": installation.asset_bytes,
                "downloaded_file_count": installation.asset_file_count,
                "duration_ns": provision_duration_ns,
            },
            "validation_runs": [
                _validate_sample(bundle, lock_path, repetition)
                for repetition in range(int(protocol["validation_samples"]))
            ],
        }
        summary = summarize(observations, protocol)
        decision = decide(summary, protocol)
        _write_json(stage / "observations.json", observations)
        _write_json(stage / "summary.json", summary)
        _write_json(stage / "decision.json", decision)
        (stage / "report.md").write_text(render_report(summary, decision), encoding="utf-8")
        run_manifest = {
            "benchmark_version": protocol["benchmark_version"],
            "duration_ns": time.monotonic_ns() - started,
            "files": [
                _file_record(stage / name) for name in RESULT_NAMES if name != "run-manifest.json"
            ],
        }
        run_manifest["run_id"] = _sha256(canonical_json_bytes(run_manifest))
        _write_json(stage / "run-manifest.json", run_manifest)
        if sum((stage / name).stat().st_size for name in RESULT_NAMES) > int(
            protocol["maximum_result_bytes"]
        ):
            raise ValueError("benchmark result exceeds limit")
        shutil.rmtree(work)
        os.replace(stage, output)
        return decision
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)
        raise


__all__ = ["RESULT_NAMES", "execute"]
