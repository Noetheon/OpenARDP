"""Run the frozen F030 cold/warm semantic product-surface measurement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from scripts.provider_retrieval_benchmark import (
        TREATMENTS,
        semantic_projection,
    )
    from scripts.provider_retrieval_benchmark import (
        load_protocol as load_provider_protocol,
    )
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.run_semantic_e2e_benchmark import (
        ProductWorkspace,
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from scripts.semantic_e2e_benchmark import load_inputs
except ModuleNotFoundError:
    from provider_retrieval_benchmark import (
        TREATMENTS,
        semantic_projection,
    )
    from provider_retrieval_benchmark import (
        load_protocol as load_provider_protocol,
    )
    from realworld_corpus import load_corpus_lock, verify_corpus
    from run_semantic_e2e_benchmark import (
        ProductWorkspace,
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from semantic_e2e_benchmark import load_inputs

from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.docling_bundle import verify_installation
from openardp.adapters.e5_semantic import IsolatedE5SemanticProvider
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.domain.semantic_retrieval import SemanticRetrievalLimits, SemanticRetrievalPolicy
from openardp.interfaces.context_composition import local_semantic_context_compiler

VERSION = "0.1.0"
READY = "SEMANTIC_SURFACE_READY"
NOT_READY = "SEMANTIC_SURFACE_NOT_READY"
FILES = ("decision.json", "observations.json", "report.md", "run-manifest.json", "summary.json")
_PDF_LOCK = Path("model-bundles/pdf-docling-2.114.0-v1/source-lock.json")
_E5_LOCK = Path("model-bundles/multilingual-e5-small-v1/source-lock.json")


def _load_protocol(root: Path) -> dict[str, Any]:
    path = root / "benchmarks/semantic-surface/v0.1.0/protocol.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("benchmark_version") != VERSION:
        raise ValueError("semantic surface protocol invalid")
    payload = dict(value)
    declared = payload.pop("protocol_id", None)
    if declared != canonical_sha256(payload):
        raise ValueError("semantic surface protocol identity invalid")
    return value


def _metric_delta(after: dict[str, int], before: dict[str, int]) -> dict[str, int]:
    return {
        "requests": after["requests"] - before["requests"],
        "passages_scored": after["passages_scored"] - before["passages_scored"],
        "cache_hits": after["cache_hits"] - before["cache_hits"],
        "peak_worker_rss_bytes": after["peak_worker_rss_bytes"],
    }


def _projection_id(rows: list[dict[str, Any]]) -> str:
    """Hash the already-canonical timing-free semantic projection."""
    return "sha256:" + hashlib.sha256(semantic_projection(rows)).hexdigest()


def _semantic_product(
    product: ProductWorkspace,
    provider: IsolatedE5SemanticProvider,
    source_protocol: dict[str, Any],
) -> ProductWorkspace:
    retrieval = source_protocol["retrieval_profile"]
    compiler = local_semantic_context_compiler(
        product.workspace,
        Utf8ByteEstimator(),
        product.text_verifier,
        product.rich_verifier,
        provider,
        policy=SemanticRetrievalPolicy(**source_protocol["semantic_policy"]),
        provider_limits=SemanticRetrievalLimits(**source_protocol["provider_limits"]),
        allocation_policy=LexicalAllocationPolicy(),
        hybrid_lexical_fallback=bool(retrieval["hybrid_lexical_fallback"]),
        source_balanced=bool(retrieval["source_balanced_semantic_admission"]),
        semantic_max_per_document=int(retrieval["semantic_max_per_document"]),
        semantic_ranked_prefix=int(retrieval["semantic_ranked_prefix"]),
        rich_first=retrieval["representation_precedence"] == "rich_then_text",
    )
    return ProductWorkspace(
        workspace=product.workspace,
        compiler=compiler,
        candidate_sources=product.candidate_sources,
        query=product.query,
        document_ids=product.document_ids,
        source_by_document=product.source_by_document,
        oracle_bodies=product.oracle_bodies,
        rich_body_by_id=product.rich_body_by_id,
        rich_anchor_by_id=product.rich_anchor_by_id,
        formats=product.formats,
        text_verifier=product.text_verifier,
        rich_verifier=product.rich_verifier,
    )


def _workspace(
    root: Path,
    workspace_root: Path,
    pdf_bundle: Path,
    manifest: ModelBundleManifest,
    assets: list[dict[str, Any]],
    inputs: Any,
    provider: IsolatedE5SemanticProvider,
    source_protocol: dict[str, Any],
) -> ProductWorkspace:
    product = _compose_workspace(
        root,
        workspace_root,
        pdf_bundle,
        manifest,
        assets,
        relevance_policy=RelevancePolicy(),
        allocation_policy=LexicalAllocationPolicy(),
        include_csv=True,
    )
    _verify_oracle(inputs, product)
    return _semantic_product(product, provider, source_protocol)


def _execute_product_rows(
    inputs: Any,
    product: ProductWorkspace,
    source_protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    return _execute_rows(
        inputs,
        product,
        include_context_audit=True,
        treatments=(TREATMENTS[1],),
        csv_supported=True,
        direct_query_treatments=frozenset((TREATMENTS[1],)),
        context_override=source_protocol["context"],
    )


def _run_once(
    root: Path,
    run_index: int,
    pdf_bundle: Path,
    e5_bundle: Path,
    manifest: ModelBundleManifest,
    assets: list[dict[str, Any]],
    inputs: Any,
    source_protocol: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    verified_at = time.perf_counter_ns()
    provider = IsolatedE5SemanticProvider(e5_bundle, expected_source_lock=root / _E5_LOCK)
    bundle_verify_ns = time.perf_counter_ns() - verified_at
    try:
        with tempfile.TemporaryDirectory(prefix=f"openardp-f030-{run_index}-cold-") as cold:
            cold_product = _workspace(
                root,
                Path(cold),
                pdf_bundle,
                manifest,
                assets,
                inputs,
                provider,
                source_protocol,
            )
            before = provider.metrics
            started = time.perf_counter_ns()
            cold_rows = _execute_product_rows(inputs, cold_product, source_protocol)
            cold_wall_ns = time.perf_counter_ns() - started
            after_cold = provider.metrics
        with tempfile.TemporaryDirectory(prefix=f"openardp-f030-{run_index}-warm-") as warm:
            warm_product = _workspace(
                root,
                Path(warm),
                pdf_bundle,
                manifest,
                assets,
                inputs,
                provider,
                source_protocol,
            )
            started = time.perf_counter_ns()
            warm_rows = _execute_product_rows(inputs, warm_product, source_protocol)
            warm_wall_ns = time.perf_counter_ns() - started
            after_warm = provider.metrics
        cold_projection_id = _projection_id(cold_rows)
        warm_projection_id = _projection_id(warm_rows)
        observation: dict[str, Any] = {
            "run_index": run_index,
            "bundle_verify_ns": bundle_verify_ns,
            "cold_wall_ns": cold_wall_ns,
            "warm_wall_ns": warm_wall_ns,
            "cold_projection_id": cold_projection_id,
            "warm_projection_id": warm_projection_id,
            "cold_metrics": _metric_delta(after_cold, before),
            "warm_metrics": _metric_delta(after_warm, after_cold),
        }
        observation["observation_id"] = canonical_sha256(observation)
        return observation, provider.recipe.recipe_id
    finally:
        provider.close()


def _summary(
    observations: dict[str, Any], runs: list[dict[str, Any]], protocol: dict[str, Any]
) -> dict[str, Any]:
    cold = sum(int(run["cold_wall_ns"]) for run in runs)
    warm = sum(int(run["warm_wall_ns"]) for run in runs)
    warm_passages = sum(int(run["warm_metrics"]["passages_scored"]) for run in runs)
    warm_hits = sum(int(run["warm_metrics"]["cache_hits"]) for run in runs)
    projections = {
        str(run[field]) for run in runs for field in ("cold_projection_id", "warm_projection_id")
    }
    value: dict[str, Any] = {
        "benchmark_version": VERSION,
        "protocol_id": protocol["protocol_id"],
        "corpus_id": protocol["corpus_id"],
        "question_set_id": protocol["question_set_id"],
        "provider_recipe_id": observations["provider_recipe_id"],
        "binding_runs": len(runs),
        "bundle_verification_total_ns": sum(int(run["bundle_verify_ns"]) for run in runs),
        "cold_wall_total_ns": cold,
        "warm_wall_total_ns": warm,
        "warm_to_cold_millionths": warm * 1_000_000 // cold,
        "warm_cache_hits": warm_hits,
        "warm_passages_scored": warm_passages,
        "warm_cache_reuse_millionths": (
            warm_hits * 1_000_000 // warm_passages if warm_passages else 0
        ),
        "peak_worker_rss_bytes": max(
            int(metrics["peak_worker_rss_bytes"])
            for run in runs
            for metrics in (run["cold_metrics"], run["warm_metrics"])
        ),
        "within_run_projection_identity": all(
            run["cold_projection_id"] == run["warm_projection_id"] for run in runs
        ),
        "across_run_projection_identity": len(projections) == 1,
        "offline": True,
    }
    value["summary_id"] = canonical_sha256(value)
    return value


def _decision(summary: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    gates = protocol["gates"]
    failures: list[str] = []
    if summary["warm_cache_reuse_millionths"] < gates["cache_reuse_minimum_millionths"]:
        failures.append("warm_cache_reuse_below_floor")
    if summary["peak_worker_rss_bytes"] > gates["peak_worker_rss_max_bytes"]:
        failures.append("peak_worker_rss_exceeded")
    if (
        gates["warm_not_slower_than_cold"]
        and summary["warm_wall_total_ns"] > summary["cold_wall_total_ns"]
    ):
        failures.append("warm_slower_than_cold")
    if gates["within_run_projection_identity"] and not summary["within_run_projection_identity"]:
        failures.append("within_run_projection_mismatch")
    if gates["across_run_projection_identity"] and not summary["across_run_projection_identity"]:
        failures.append("across_run_projection_mismatch")
    value: dict[str, Any] = {
        "benchmark_version": VERSION,
        "protocol_id": protocol["protocol_id"],
        "summary_id": summary["summary_id"],
        "decision": READY if not failures else NOT_READY,
        "failures": failures,
    }
    value["decision_id"] = canonical_sha256(value)
    return value


def _report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    return (
        "# Semantic retrieval product-surface benchmark\n\n"
        f"Decision: `{decision['decision']}`\n\n"
        f"- Cold wall total: {summary['cold_wall_total_ns']} ns\n"
        f"- Warm wall total: {summary['warm_wall_total_ns']} ns\n"
        f"- Warm/cold: {summary['warm_to_cold_millionths']} millionths\n"
        f"- Warm cache reuse: {summary['warm_cache_reuse_millionths']} millionths\n"
        f"- Peak worker RSS: {summary['peak_worker_rss_bytes']} bytes\n"
        "- Verified semantic bundle: 492794646 bytes\n"
        "- Reference platform: macOS arm64; Linux and Windows timing is unmeasured\n"
        f"- Failures: {', '.join(decision['failures']) if decision['failures'] else 'none'}\n\n"
        "This result covers one pinned offline provider and one small redistributable corpus. "
        "It does not validate answer generation, broad-domain quality or production SLOs.\n"
    )


def _publish(
    output: Path,
    observations: dict[str, Any],
    summary: dict[str, Any],
    decision: dict[str, Any],
    *,
    maximum_bytes: int,
) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        values = {
            "observations.json": canonical_json_bytes(observations) + b"\n",
            "summary.json": canonical_json_bytes(summary) + b"\n",
            "decision.json": canonical_json_bytes(decision) + b"\n",
            "report.md": _report(summary, decision).encode("utf-8"),
        }
        for name, payload in values.items():
            (stage / name).write_bytes(payload)
        manifest: dict[str, Any] = {
            "files": {
                name: {
                    "byte_length": len(payload),
                    "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
                }
                for name, payload in values.items()
            }
        }
        manifest["result_id"] = canonical_sha256(manifest)
        (stage / "run-manifest.json").write_bytes(canonical_json_bytes(manifest) + b"\n")
        if sum((stage / name).stat().st_size for name in FILES) > maximum_bytes:
            raise ValueError("semantic surface result too large")
        os.replace(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def execute(
    repository_root: Path,
    *,
    pdf_bundle: Path,
    e5_bundle: Path,
    output: Path,
) -> dict[str, Any]:
    """Run two cold/warm pairs and atomically publish body-free evidence."""
    root = repository_root.resolve(strict=True)
    protocol = _load_protocol(root)
    source_protocol = load_provider_protocol(root, "0.3.0")
    inputs = load_inputs(root)
    corpus = verify_corpus(root / "corpora/realworld/v0.1.0")
    if (
        source_protocol["protocol_id"] != protocol["source_protocol_id"]
        or corpus.corpus_id != protocol["corpus_id"]
        or inputs.questions["question_set_id"] != protocol["question_set_id"]
    ):
        raise ValueError("semantic surface input identity mismatch")
    assets = load_corpus_lock(root / "corpora/realworld/v0.1.0")["assets"]
    verify_installation(pdf_bundle, expected_source_lock=root / _PDF_LOCK)
    manifest = ModelBundleManifest.model_validate_json((pdf_bundle / "manifest.json").read_bytes())
    runs: list[dict[str, Any]] = []
    recipe_ids: set[str] = set()
    for run_index in range(1, int(protocol["binding_runs"]) + 1):
        observation, recipe_id = _run_once(
            root,
            run_index,
            pdf_bundle,
            e5_bundle,
            manifest,
            assets,
            inputs,
            source_protocol,
        )
        runs.append(observation)
        recipe_ids.add(recipe_id)
    if len(recipe_ids) != 1:
        raise ValueError("semantic provider recipe drift")
    observations: dict[str, Any] = {
        "benchmark_version": VERSION,
        "protocol_id": protocol["protocol_id"],
        "corpus_id": protocol["corpus_id"],
        "question_set_id": protocol["question_set_id"],
        "provider_recipe_id": recipe_ids.pop(),
        "runs": runs,
    }
    observations["observations_id"] = canonical_sha256(observations)
    summary = _summary(observations, runs, protocol)
    decision = _decision(summary, protocol)
    _publish(
        output,
        observations,
        summary,
        decision,
        maximum_bytes=int(protocol["result_max_bytes"]),
    )
    return decision


def main() -> int:
    """Parse explicit local bundle paths and execute the frozen benchmark."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--pdf-bundle", type=Path, required=True)
    parser.add_argument("--e5-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = execute(
            arguments.repository_root,
            pdf_bundle=arguments.pdf_bundle,
            e5_bundle=arguments.e5_bundle,
            output=arguments.output,
        )
    except FileExistsError:
        print("benchmark_output_conflict")
        return 8
    except (OSError, ValueError):
        print("benchmark_execution_failed")
        return 6
    print(f"decision={decision['decision']} failures={len(decision['failures'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
