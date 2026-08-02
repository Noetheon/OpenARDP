"""Body-free producer for the F024 six-format structural baseline."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

try:  # pragma: no cover - resource is unavailable on Windows
    import resource
except ImportError:  # pragma: no cover - Windows
    resource = None  # type: ignore[assignment]

try:
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.realworld_corpus_benchmark_evaluation import decide, render_report, summarize
except ModuleNotFoundError:
    from realworld_corpus import load_corpus_lock, verify_corpus
    from realworld_corpus_benchmark_evaluation import decide, render_report, summarize

from openardp.adapters.docling_bundle import verify_installation
from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.identity import canonical_json_bytes, canonical_sha256, source_version_id
from openardp.domain.ingestion import TextMediaType
from openardp.domain.rich_ingestion import ModelBundleManifest, RichMediaType, RichParserLimits
from openardp.ports.parser import RichParserResourceLimitExceeded

RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
_BENCHMARK_ROOT = Path(__file__).parents[1] / "benchmarks/realworld-corpus/v0.1.0"
_MODEL_LOCK = Path("model-bundles/pdf-docling-2.114.0-v1/source-lock.json")
_CSV_PROBE = Path(__file__).with_name("realworld_csv_probe.py")
_ZERO_ID = "sha256:" + "0" * 64


def _sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _rss_bytes(value: int) -> int:
    return value if sys.platform == "darwin" else value * 1024


def _usage() -> tuple[int, int]:
    if resource is None:  # pragma: no cover - Windows
        return time.process_time_ns(), 0
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_ns = round(
        (own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime) * 1_000_000_000
    )
    rss = max(_rss_bytes(own.ru_maxrss), _rss_bytes(children.ru_maxrss))
    return cpu_ns, rss


def _measure[T](operation: Callable[[], T]) -> tuple[T, int, int, int]:
    before_cpu, _ = _usage()
    started = time.perf_counter_ns()
    value = operation()
    wall_ns = time.perf_counter_ns() - started
    after_cpu, rss = _usage()
    return value, wall_ns, max(0, after_cpu - before_cpu), rss


def _base_row(asset: Mapping[str, Any], repetition: int) -> dict[str, Any]:
    return {
        "asset_key": asset["key"],
        "error_category": None,
        "format": asset["format"],
        "network_attempts": 0,
        "outcome": "pass",
        "repetition": repetition,
        "source_id": asset["sha256"],
    }


def observe_text(asset: Mapping[str, Any], path: Path, repetition: int) -> dict[str, Any]:
    """Parse one exact TXT/Markdown asset and retain only structural identities."""
    payload = path.read_bytes()
    if source_version_id(payload) != asset["sha256"]:
        raise ValueError("source_identity")
    parser = TextParserAdapter()
    media_type = (
        TextMediaType.MARKDOWN.value if asset["format"] == "md" else TextMediaType.PLAIN.value
    )
    output, wall_ns, cpu_ns, rss = _measure(lambda: parser.parse((payload,), media_type=media_type))
    native = canonical_json_bytes(output.model_dump(mode="json"))
    blocks = [item.model_dump(mode="json") for item in output.blocks]
    return {
        **_base_row(asset, repetition),
        "anchor_classes": ["line_range"],
        "block_count": len(blocks),
        "block_set_id": canonical_sha256(blocks),
        "cpu_ns": cpu_ns,
        "native_bytes": len(native),
        "native_id": _sha(native),
        "page_count": 0,
        "peak_rss_bytes": rss,
        "pointer_bounded_count": 0,
        "pointer_resolution_complete": True,
        "recipe_id": parser.recipe.representation_id_for(str(asset["sha256"])),
        "retrieval_complete": all(
            item.line_start <= item.line_end and bool(item.text.encode("utf-8"))
            for item in output.blocks
        ),
        "table_count": 0,
        "wall_ns": wall_ns,
    }


def _invoke_csv(asset: Mapping[str, Any], corpus_root: Path) -> dict[str, Any]:
    request = {
        "key": asset["key"],
        "max_cells": 1_000_000,
        "max_characters": 16_777_216,
        "max_file_bytes": 8_388_608,
        "max_rows": 100_000,
        "path": asset["path"],
        "profile_version": "0.1.0",
        "root": str(corpus_root.resolve(strict=True)),
        "sha256": asset["sha256"],
    }
    with tempfile.TemporaryDirectory(prefix="f024-csv-") as temporary:
        request_path = Path(temporary) / "request.json"
        request_path.write_bytes(canonical_json_bytes(request) + b"\n")
        completed = subprocess.run(  # noqa: S603 - fixed interpreter and reviewed script.
            [
                sys.executable,
                "-I",
                "-S",
                str(_CSV_PROBE),
                "--request",
                str(request_path),
            ],
            cwd=Path(__file__).parents[1],
            check=False,
            capture_output=True,
            timeout=120,
        )
    if completed.returncode != 0 or completed.stderr or len(completed.stdout) > 1_048_576:
        raise ValueError("csv_process")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("csv_response") from error
    if not isinstance(value, dict) or canonical_json_bytes(value) + b"\n" != completed.stdout:
        raise ValueError("csv_response")
    return value


def observe_csv(
    asset: Mapping[str, Any],
    corpus_root: Path,
    repetition: int,
) -> dict[str, Any]:
    """Run and validate the isolated body-free real-world CSV probe."""
    response, wall_ns, cpu_ns, rss = _measure(lambda: _invoke_csv(asset, corpus_root))
    if response.get("implementation_sha256") != _sha(_CSV_PROBE.read_bytes()):
        raise ValueError("csv_implementation")
    if response.get("source_id") != asset["sha256"] or response.get("key") != asset["key"]:
        raise ValueError("csv_source")
    anchors = response.get("anchor_classes")
    if not isinstance(anchors, list) or anchors != sorted(set(anchors)):
        raise ValueError("csv_anchors")
    return {
        **_base_row(asset, repetition),
        "anchor_classes": anchors,
        "block_count": int(response["block_count"]),
        "block_set_id": response["block_set_id"],
        "cpu_ns": cpu_ns,
        "native_bytes": int(response["native_bytes"]),
        "native_id": response["native_id"],
        "page_count": 1,
        "peak_rss_bytes": rss,
        "pointer_bounded_count": 0,
        "pointer_resolution_complete": {
            "page_region",
            "provider_pointer",
            "table_cell",
            "text_span",
        }.issubset(anchors),
        "recipe_id": response["recipe_id"],
        "retrieval_complete": response.get("retrieval_complete") is True,
        "table_count": 1,
        "wall_ns": wall_ns,
    }


def observe_rich(
    asset: Mapping[str, Any],
    path: Path,
    repetition: int,
    *,
    model_root: Path | None,
    model_manifest: ModelBundleManifest | None,
) -> dict[str, Any]:
    """Parse one PDF/DOCX/PPTX asset with the reviewed isolated provider profile."""
    payload = path.read_bytes()
    if source_version_id(payload) != asset["sha256"]:
        raise ValueError("source_identity")
    format_name = str(asset["format"])
    media_type = {
        "docx": RichMediaType.DOCX.value,
        "pdf": RichMediaType.PDF.value,
        "pptx": RichMediaType.PPTX.value,
    }[format_name]
    adapter = IsolatedDoclingAdapter(
        limits=RichParserLimits(timeout_seconds=120.0),
        model_root=model_root if format_name == "pdf" else None,
        model_manifest=model_manifest if format_name == "pdf" else None,
    )
    output, wall_ns, cpu_ns, rss = _measure(
        lambda: adapter.parse((payload,), media_type=media_type)
    )
    pointer_complete = True
    pointer_bounded_count = 0
    for candidate in output.candidates:
        try:
            adapter.resolve(
                output.native_document,
                pointer=candidate.native_pointer.pointer,
            )
        except RichParserResourceLimitExceeded:
            # The resolver reaches the target before applying its output-byte cap.
            # Retain this unfavorable but correct bounded-retrieval fact explicitly.
            pointer_bounded_count += 1
        except (KeyError, TypeError, ValueError):
            pointer_complete = False
    candidate_values = [item.model_dump(mode="json") for item in output.candidates]
    native = output.canonical_native_bytes
    pages = output.native_document.get("pages", {})
    tables = output.native_document.get("tables", [])
    return {
        **_base_row(asset, repetition),
        "anchor_classes": sorted({str(item.anchor.anchor_type) for item in output.candidates}),
        "block_count": len(candidate_values),
        "block_set_id": canonical_sha256(candidate_values),
        "cpu_ns": cpu_ns,
        "native_bytes": len(native),
        "native_id": _sha(native),
        "page_count": len(pages) if isinstance(pages, (dict, list)) else 0,
        "peak_rss_bytes": rss,
        "pointer_bounded_count": pointer_bounded_count,
        "pointer_resolution_complete": pointer_complete,
        "recipe_id": canonical_sha256(adapter.recipe.model_dump(mode="json")),
        "retrieval_complete": all(bool(item.retrieval_bytes) for item in output.candidates),
        "table_count": len(tables) if isinstance(tables, list) else 0,
        "wall_ns": wall_ns,
    }


def _error_category(error: BaseException) -> str:
    if isinstance(error, subprocess.TimeoutExpired):
        return "timeout"
    name = type(error).__name__.casefold()
    if "resource" in name:
        return "resource_limit"
    if "model" in name or "bundle" in name:
        return "model_boundary"
    if isinstance(error, (KeyError, TypeError, ValueError)):
        return "validation"
    return "parser_failure"


def _failed_row(asset: Mapping[str, Any], repetition: int, error: BaseException) -> dict[str, Any]:
    return {
        **_base_row(asset, repetition),
        "anchor_classes": [],
        "block_count": 0,
        "block_set_id": _ZERO_ID,
        "cpu_ns": 0,
        "error_category": _error_category(error),
        "native_bytes": 0,
        "native_id": _ZERO_ID,
        "outcome": "fail",
        "page_count": 0,
        "peak_rss_bytes": 0,
        "pointer_bounded_count": 0,
        "pointer_resolution_complete": False,
        "recipe_id": _ZERO_ID,
        "retrieval_complete": False,
        "table_count": 0,
        "wall_ns": 0,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _manifest_entry(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {"byte_length": len(payload), "name": path.name, "sha256": _sha(payload)}


def publish_result(
    observations: dict[str, Any],
    protocol: dict[str, Any],
    output: Path,
    *,
    duration_ns: int,
) -> dict[str, Any]:
    """Evaluate and atomically publish one complete body-free result set."""
    if output.exists() or output.is_symlink():
        raise FileExistsError("benchmark output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-stage-", dir=output.parent))
    try:
        summary = summarize(observations, protocol)
        decision = decide(summary, protocol)
        _write_json(stage / "observations.json", observations)
        _write_json(stage / "summary.json", summary)
        _write_json(stage / "decision.json", decision)
        (stage / "report.md").write_text(
            render_report(summary, decision),
            encoding="utf-8",
        )
        manifest = {
            "benchmark_version": protocol["benchmark_version"],
            "duration_ns": duration_ns,
            "files": [
                _manifest_entry(stage / name)
                for name in RESULT_NAMES
                if name != "run-manifest.json"
            ],
        }
        manifest["run_id"] = canonical_sha256(manifest)
        _write_json(stage / "run-manifest.json", manifest)
        if sum((stage / name).stat().st_size for name in RESULT_NAMES) > int(
            protocol["maximum_result_bytes"]
        ):
            raise ValueError("result_size")
        os.replace(stage, output)
        return decision
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def execute(
    repository_root: Path,
    *,
    pdf_bundle: Path,
    output: Path,
) -> dict[str, Any]:
    """Execute all six real assets twice and publish the fail-closed baseline."""
    root = repository_root.resolve(strict=True)
    corpus_root = root / "corpora/realworld/v0.1.0"
    verified = verify_corpus(corpus_root)
    lock = load_corpus_lock(corpus_root)
    protocol = json.loads((root / "benchmarks/realworld-corpus/v0.1.0/protocol.json").read_bytes())
    installation = verify_installation(
        pdf_bundle,
        expected_source_lock=root / _MODEL_LOCK,
    )
    model_manifest = ModelBundleManifest.model_validate_json(
        (pdf_bundle / "manifest.json").read_bytes()
    )
    if _sha(_CSV_PROBE.read_bytes()) != protocol["expected_csv_probe_sha256"]:
        raise ValueError("csv_probe_drift")
    started = time.monotonic_ns()
    rows: list[dict[str, Any]] = []
    for asset in lock["assets"]:
        for repetition in range(int(protocol["required_repetitions"])):
            try:
                format_name = str(asset["format"])
                if format_name in {"md", "txt"}:
                    row = observe_text(asset, corpus_root / str(asset["path"]), repetition)
                elif format_name == "csv":
                    row = observe_csv(asset, corpus_root, repetition)
                else:
                    row = observe_rich(
                        asset,
                        corpus_root / str(asset["path"]),
                        repetition,
                        model_root=pdf_bundle / "assets",
                        model_manifest=model_manifest,
                    )
            except Exception as error:  # retain a stable unfavorable observation
                row = _failed_row(asset, repetition, error)
            rows.append(row)
    duration_ns = time.monotonic_ns() - started
    observations = {
        "benchmark_version": protocol["benchmark_version"],
        "corpus": {
            "corpus_id": verified.corpus_id,
            "payload_bytes": verified.payload_bytes,
            "payload_count": verified.payload_count,
        },
        "environment": {
            "architecture": platform.machine().lower(),
            "os_family": platform.system().lower(),
            "python_version": ".".join(map(str, sys.version_info[:3])),
        },
        "model": {
            "bundle_id": installation.bundle_id,
            "source_lock_id": installation.source_lock_id,
        },
        "offline": {
            "corpus_preverified": True,
            "explicit_pdf_bundle": True,
            "socket_denied_before_provider_import": True,
        },
        "rows": rows,
    }
    if duration_ns > int(protocol["maximum_run_ns"]):
        raise ValueError("run_time")
    return publish_result(observations, protocol, output, duration_ns=duration_ns)


__all__ = [
    "RESULT_NAMES",
    "execute",
    "observe_csv",
    "observe_rich",
    "observe_text",
    "publish_result",
]
