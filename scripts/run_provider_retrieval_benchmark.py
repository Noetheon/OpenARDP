"""Execute the frozen offline F027/F029 retrieval comparison."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from scripts.provider_retrieval_benchmark import (
        RESULT_NAMES,
        TREATMENTS,
        decide,
        file_digest,
        load_protocol,
        render_report,
        semantic_projection,
        summarize,
    )
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.run_semantic_e2e_benchmark import (
        ProductWorkspace,
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from scripts.semantic_e2e_benchmark import SemanticBenchmarkError, load_inputs
except ModuleNotFoundError:
    from provider_retrieval_benchmark import (
        RESULT_NAMES,
        TREATMENTS,
        decide,
        file_digest,
        load_protocol,
        render_report,
        semantic_projection,
        summarize,
    )
    from realworld_corpus import load_corpus_lock, verify_corpus
    from run_semantic_e2e_benchmark import (
        ProductWorkspace,
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from semantic_e2e_benchmark import SemanticBenchmarkError, load_inputs

from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.docling_bundle import verify_installation
from openardp.adapters.e5_semantic import IsolatedE5SemanticProvider
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.domain.semantic_retrieval import SemanticRetrievalLimits, SemanticRetrievalPolicy
from openardp.interfaces.context_composition import local_semantic_context_compiler

_PDF_LOCK = Path("model-bundles/pdf-docling-2.114.0-v1/source-lock.json")
_E5_LOCK = Path("model-bundles/multilingual-e5-small-v1/source-lock.json")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _interleave(
    lexical: list[dict[str, Any]], semantic: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_key = {
        (str(row["question_id"]), str(row["treatment"])): row for row in (*lexical, *semantic)
    }
    return [
        by_key[(question_id, treatment)]
        for question_id in (f"Q{number:02d}" for number in range(1, 20))
        for treatment in TREATMENTS
    ]


def _run_workspace(
    root: Path,
    workspace_root: Path,
    pdf_bundle: Path,
    e5_bundle: Path,
    manifest: ModelBundleManifest,
    assets: list[dict[str, Any]],
    inputs: Any,
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], tuple[str, ...], dict[str, int], dict[str, Any]]:
    product: ProductWorkspace = _compose_workspace(
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
    direct = frozenset(TREATMENTS)
    lexical_rows = _execute_rows(
        inputs,
        product,
        include_context_audit=True,
        treatments=(TREATMENTS[0],),
        csv_supported=True,
        direct_query_treatments=direct,
        context_override=protocol["context"],
    )
    policy = SemanticRetrievalPolicy(**protocol["semantic_policy"])
    limits = SemanticRetrievalLimits(**protocol["provider_limits"])
    retrieval = protocol.get("retrieval_profile", {})
    provider = IsolatedE5SemanticProvider(e5_bundle, expected_source_lock=root / _E5_LOCK)
    try:
        semantic_compiler = local_semantic_context_compiler(
            product.workspace,
            Utf8ByteEstimator(),
            product.text_verifier,
            product.rich_verifier,
            provider,
            policy=policy,
            provider_limits=limits,
            allocation_policy=LexicalAllocationPolicy(),
            hybrid_lexical_fallback=bool(retrieval.get("hybrid_lexical_fallback", False)),
            source_balanced=bool(retrieval.get("source_balanced_semantic_admission", False)),
            semantic_max_per_document=int(retrieval.get("semantic_max_per_document", 32)),
            semantic_ranked_prefix=int(retrieval.get("semantic_ranked_prefix", 4)),
            rich_first=retrieval.get("representation_precedence") == "rich_then_text",
        )
        semantic_product = ProductWorkspace(
            workspace=product.workspace,
            compiler=semantic_compiler,
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
        semantic_rows = _execute_rows(
            inputs,
            semantic_product,
            include_context_audit=True,
            treatments=(TREATMENTS[1],),
            csv_supported=True,
            direct_query_treatments=direct,
            context_override=protocol["context"],
        )
        metrics = provider.metrics
        recipe = provider.recipe.model_dump(mode="json")
        recipe["recipe_id"] = provider.recipe.recipe_id
    finally:
        provider.close()
    return _interleave(lexical_rows, semantic_rows), product.formats, metrics, recipe


def _publish(
    output: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    decision: dict[str, Any],
    manifest_facts: dict[str, Any],
    *,
    maximum_bytes: int,
) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        _write_json(
            stage / "observations.json",
            {
                "benchmark_version": summary["benchmark_version"],
                "corpus_id": summary["corpus_id"],
                "question_set_id": summary["question_set_id"],
                "protocol_id": summary["protocol_id"],
                "rows": rows,
            },
        )
        _write_json(stage / "summary.json", summary)
        _write_json(stage / "decision.json", decision)
        (stage / "report.md").write_text(render_report(summary, decision), encoding="utf-8")
        files = {}
        for name in RESULT_NAMES:
            if name != "run-manifest.json":
                digest, length = file_digest(stage / name)
                files[name] = {"sha256": digest, "byte_length": length}
        manifest = {**manifest_facts, "files": files}
        manifest["run_id"] = canonical_sha256(manifest)
        _write_json(stage / "run-manifest.json", manifest)
        if sum((stage / name).stat().st_size for name in RESULT_NAMES) > maximum_bytes:
            raise SemanticBenchmarkError("provider_result_size")
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
    protocol_version: str = "0.3.0",
) -> dict[str, Any]:
    """Run both profiles in two fresh workspaces and atomically publish evidence."""
    root = repository_root.resolve(strict=True)
    inputs = load_inputs(root)
    protocol = load_protocol(root, protocol_version)
    if (
        protocol["corpus_id"] != inputs.protocol["corpus_id"]
        or protocol["question_set_id"] != inputs.questions["question_set_id"]
        or protocol["source_protocol_id"] != inputs.protocol["protocol_id"]
    ):
        raise SemanticBenchmarkError("provider_input_identity")
    corpus = verify_corpus(root / "corpora/realworld/v0.1.0")
    if corpus.corpus_id != protocol["corpus_id"]:
        raise SemanticBenchmarkError("provider_corpus_identity")
    assets = load_corpus_lock(root / "corpora/realworld/v0.1.0")["assets"]
    pdf = verify_installation(pdf_bundle, expected_source_lock=root / _PDF_LOCK)
    manifest = ModelBundleManifest.model_validate_json((pdf_bundle / "manifest.json").read_bytes())
    started = time.perf_counter_ns()
    with tempfile.TemporaryDirectory(prefix="openardp-f029-a-") as first_root:
        first, formats, first_metrics, recipe = _run_workspace(
            root,
            Path(first_root),
            pdf_bundle,
            e5_bundle,
            manifest,
            assets,
            inputs,
            protocol,
        )
    with tempfile.TemporaryDirectory(prefix="openardp-f029-b-") as second_root:
        second, second_formats, second_metrics, second_recipe = _run_workspace(
            root,
            Path(second_root),
            pdf_bundle,
            e5_bundle,
            manifest,
            assets,
            inputs,
            protocol,
        )
    semantic_first = [row for row in first if row["treatment"] == TREATMENTS[1]]
    semantic_second = [row for row in second if row["treatment"] == TREATMENTS[1]]
    semantic_identical = semantic_projection(semantic_first) == semantic_projection(semantic_second)
    all_identical = semantic_projection(first) == semantic_projection(second)
    hard_failures: list[str] = []
    if not all_identical:
        hard_failures.append("fresh_run_mismatch")
    if formats != second_formats:
        hard_failures.append("ingested_format_mismatch")
    if recipe != second_recipe:
        hard_failures.append("provider_recipe_mismatch")
    if any(row["outcome"] == "failed" for row in first):
        hard_failures.append("product_runtime_failure")
    second_failure_count = sum(row["outcome"] == "failed" for row in second)
    if second_failure_count and "product_runtime_failure" not in hard_failures:
        hard_failures.append("product_runtime_failure")
    summary = summarize(
        first,
        inputs.by_id,
        corpus_id=protocol["corpus_id"],
        question_set_id=protocol["question_set_id"],
        source_protocol_id=protocol["source_protocol_id"],
        protocol_id=protocol["protocol_id"],
        supported_formats_ingested=formats,
        semantic_runs_identical=semantic_identical,
        provider_metrics=first_metrics,
        benchmark_version=protocol["benchmark_version"],
    )
    decision = decide(summary, hard_failures=hard_failures)
    _publish(
        output,
        first,
        summary,
        decision,
        {
            "benchmark_version": protocol["benchmark_version"],
            "corpus_id": protocol["corpus_id"],
            "question_set_id": protocol["question_set_id"],
            "source_protocol_id": protocol["source_protocol_id"],
            "protocol_id": protocol["protocol_id"],
            "offline": True,
            "fresh_runs": 2,
            "all_runs_identical": all_identical,
            "semantic_runs_identical": semantic_identical,
            "supported_formats_ingested": list(formats),
            "second_supported_formats_ingested": list(second_formats),
            "pdf_bundle_id": pdf.bundle_id,
            "provider_recipe": recipe,
            "second_provider_recipe": second_recipe,
            "first_provider_metrics": first_metrics,
            "second_provider_metrics": second_metrics,
            "second_failure_count": second_failure_count,
            "total_wall_ns": time.perf_counter_ns() - started,
        },
        maximum_bytes=int(protocol["result_max_bytes"]),
    )
    return decision


def main() -> int:
    """Parse explicit bundle paths and emit one body-free outcome line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--pdf-bundle", type=Path, required=True)
    parser.add_argument("--e5-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--protocol-version",
        choices=("0.1.0", "0.2.0", "0.3.0"),
        default="0.3.0",
    )
    arguments = parser.parse_args()
    try:
        decision = execute(
            arguments.repository_root,
            pdf_bundle=arguments.pdf_bundle,
            e5_bundle=arguments.e5_bundle,
            output=arguments.output,
            protocol_version=arguments.protocol_version,
        )
    except FileExistsError:
        print("benchmark_output_conflict")
        return 8
    except (OSError, ValueError):
        print("benchmark_execution_failed")
        return 6
    print(
        f"decision={decision['decision']} failures={len(decision['failures'])} "
        f"output={arguments.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
