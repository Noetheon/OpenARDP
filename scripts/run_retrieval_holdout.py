"""Execute the frozen offline F034 lexical and semantic retrieval holdout."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

try:
    from scripts.retrieval_holdout import (
        QUESTION_IDS,
        RESULT_NAMES,
        TREATMENTS,
        HoldoutError,
        HoldoutInputs,
        evaluate_verdict,
        load_holdout,
    )
    from scripts.retrieval_holdout_evaluation import (
        render_report,
        summarize,
        verdict_checks,
    )
    from scripts.run_semantic_e2e_benchmark import (
        ProductWorkspace,
        _execute_rows,
        _verify_oracle,
    )
    from scripts.semantic_e2e_benchmark import semantic_projection
except ModuleNotFoundError:
    from retrieval_holdout import (
        QUESTION_IDS,
        RESULT_NAMES,
        TREATMENTS,
        HoldoutError,
        HoldoutInputs,
        evaluate_verdict,
        load_holdout,
    )
    from retrieval_holdout_evaluation import render_report, summarize, verdict_checks
    from run_semantic_e2e_benchmark import ProductWorkspace, _execute_rows, _verify_oracle
    from semantic_e2e_benchmark import semantic_projection

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.adapters.e5_semantic import IsolatedE5SemanticProvider
from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.rich_ingestion import RichRepresentationArtifacts
from openardp.domain.semantic_retrieval import SemanticRetrievalLimits, SemanticRetrievalPolicy
from openardp.interfaces.context_composition import local_semantic_context_compiler
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService

_FIXED_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_E5_LOCK = Path("model-bundles/multilingual-e5-small-v1/source-lock.json")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _file_fact(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def _compose_workspace(root: Path, workspace_root: Path, inputs: HoldoutInputs) -> ProductWorkspace:
    workspace = LocalWorkspace.initialize(workspace_root, now=_FIXED_TIME)
    entropy = 0

    def bits() -> int:
        nonlocal entropy
        entropy += 1
        return entropy

    ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        IsolatedParserAdapter(),
        source_factory=LocalSource,
        clock=lambda: _FIXED_TIME,
        owner_id_factory=lambda: "retrieval-holdout",
        lease_token_factory=lambda: "5" * 64,
        random_bits=bits,
    )
    source_by_document: dict[str, str] = {}
    document_ids: list[Any] = []
    corpus_root = root / "corpora/retrieval-holdout/v0.1.0"
    for source in inputs.corpus["sources"]:
        result = ingestion.ingest(corpus_root / str(source["path"]))
        source_by_document[str(result.scope.document_id)] = str(source["key"])
        document_ids.append(result.scope.document_id)

    text = TextLexicalCandidateSource(workspace.object_store, workspace.catalog)

    def verify_rich(_artifacts: RichRepresentationArtifacts) -> None:
        raise HoldoutError("unexpected_rich_representation")

    rich = RichLexicalCandidateSource(
        workspace.object_store,
        workspace.catalog,
        representation_verifier=verify_rich,
    )
    candidates = (text, rich)
    observed = RelevanceObservingCandidateSource(
        workspace.object_store,
        candidates,
        RelevancePolicy(),
    )
    compiler = ContextCompilerService(
        workspace.object_store,
        workspace.catalog,
        Utf8ByteEstimator(),
        (observed,),
        relevance_policy=RelevancePolicy(),
        allocation_policy=LexicalAllocationPolicy(),
    )
    query = DocumentQueryService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
        representation_verifier=ingestion.verify_ready_representation,
        clock=lambda: _FIXED_TIME,
    )
    return ProductWorkspace(
        workspace=workspace,
        compiler=compiler,
        candidate_sources=candidates,
        query=query,
        document_ids=tuple(sorted(document_ids, key=str)),
        source_by_document=source_by_document,
        oracle_bodies={key: [body] for key, body in inputs.source_text.items()},
        rich_body_by_id={},
        rich_anchor_by_id={},
        formats=("md",),
        text_verifier=ingestion.verify_ready_representation,
        rich_verifier=verify_rich,
    )


def _interleave(
    lexical: list[dict[str, Any]], semantic: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    lookup = {
        (str(row["question_id"]), str(row["treatment"])): row for row in (*lexical, *semantic)
    }
    return [
        lookup[(question_id, treatment)] for question_id in QUESTION_IDS for treatment in TREATMENTS
    ]


def _run_workspace(
    root: Path,
    workspace_root: Path,
    e5_bundle: Path,
    inputs: HoldoutInputs,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, Any]]:
    product = _compose_workspace(root, workspace_root, inputs)
    shared_inputs = cast(Any, inputs)
    _verify_oracle(shared_inputs, product)
    protocol = inputs.protocol
    lexical = _execute_rows(
        shared_inputs,
        product,
        include_context_audit=True,
        treatments=(TREATMENTS[0],),
        direct_query_treatments=frozenset(TREATMENTS),
        context_override=protocol["context"],
    )
    provider = IsolatedE5SemanticProvider(e5_bundle, expected_source_lock=root / _E5_LOCK)
    try:
        retrieval = protocol["retrieval_profile"]
        semantic_compiler = local_semantic_context_compiler(
            product.workspace,
            Utf8ByteEstimator(),
            product.text_verifier,
            product.rich_verifier,
            provider,
            policy=SemanticRetrievalPolicy(**protocol["semantic_policy"]),
            provider_limits=SemanticRetrievalLimits(**protocol["provider_limits"]),
            allocation_policy=LexicalAllocationPolicy(),
            hybrid_lexical_fallback=bool(retrieval["hybrid_lexical_fallback"]),
            source_balanced=bool(retrieval["source_balanced_semantic_admission"]),
            semantic_max_per_document=int(retrieval["semantic_max_per_document"]),
            semantic_ranked_prefix=int(retrieval["semantic_ranked_prefix"]),
            rich_first=retrieval["representation_precedence"] == "rich_then_text",
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
        semantic = _execute_rows(
            shared_inputs,
            semantic_product,
            include_context_audit=True,
            treatments=(TREATMENTS[1],),
            direct_query_treatments=frozenset(TREATMENTS),
            context_override=protocol["context"],
        )
        metrics = provider.metrics
        recipe = provider.recipe.model_dump(mode="json")
        recipe["recipe_id"] = provider.recipe.recipe_id
    finally:
        provider.close()
    return _interleave(lexical, semantic), metrics, recipe


def _model_matches(recipe: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(recipe.get(key) == value for key, value in expected.items())


def _projection_id(rows: list[dict[str, Any]]) -> str:
    payload = b"[" + b",".join(semantic_projection(row) for row in rows) + b"]"
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _publish(
    output: Path,
    inputs: HoldoutInputs,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    decision: dict[str, Any],
    manifest_facts: dict[str, Any],
) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        _write_json(
            stage / "observations.json",
            {
                "benchmark_version": inputs.protocol["benchmark_version"],
                "corpus_id": inputs.corpus["corpus_id"],
                "question_set_id": inputs.question_set["question_set_id"],
                "protocol_id": inputs.protocol["protocol_id"],
                "rows": rows,
            },
        )
        _write_json(stage / "summary.json", summary)
        _write_json(stage / "decision.json", decision)
        (stage / "report.md").write_text(render_report(summary, decision), encoding="utf-8")
        files = {
            name: _file_fact(stage / name) for name in RESULT_NAMES if name != "run-manifest.json"
        }
        manifest = {**manifest_facts, "files": files}
        manifest["run_id"] = canonical_sha256(manifest)
        _write_json(stage / "run-manifest.json", manifest)
        if sum((stage / name).stat().st_size for name in RESULT_NAMES) > int(
            inputs.protocol["result_max_bytes"]
        ):
            raise HoldoutError("result_size")
        os.replace(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def execute(repository_root: Path, *, e5_bundle: Path, output: Path) -> dict[str, Any]:
    """Run two fresh workspaces and atomically publish independently checkable evidence."""
    root = repository_root.resolve(strict=True)
    inputs = load_holdout(root)
    started = time.perf_counter_ns()
    with tempfile.TemporaryDirectory(prefix="openardp-f034-a-") as first_root:
        first, first_metrics, first_recipe = _run_workspace(
            root, Path(first_root), e5_bundle, inputs
        )
    with tempfile.TemporaryDirectory(prefix="openardp-f034-b-") as second_root:
        second, second_metrics, second_recipe = _run_workspace(
            root, Path(second_root), e5_bundle, inputs
        )
    identical = [semantic_projection(row) for row in first] == [
        semantic_projection(row) for row in second
    ]
    failures: list[str] = []
    if any(row["outcome"] == "failed" for row in (*first, *second)):
        failures.append("product_runtime_failure")
    if not identical:
        failures.append("fresh_run_mismatch")
    if first_recipe != second_recipe:
        failures.append("provider_recipe_mismatch")
    model_matches = _model_matches(first_recipe, inputs.protocol["model"])
    if not model_matches:
        failures.append("provider_model_mismatch")
    summary = summarize(
        first,
        inputs.questions,
        corpus_id=str(inputs.corpus["corpus_id"]),
        question_set_id=str(inputs.question_set["question_set_id"]),
        protocol_id=str(inputs.protocol["protocol_id"]),
        fresh_runs_identical=identical,
        provider_metrics=first_metrics,
    )
    validity, quality = verdict_checks(summary)
    validity["provider_model_identity"] = model_matches
    validity["provider_recipe_identical"] = first_recipe == second_recipe
    decision = evaluate_verdict(
        validity_checks=validity,
        quality_checks=quality,
        failures=tuple(failures),
        summary_id=str(summary["summary_id"]),
    )
    _publish(
        output,
        inputs,
        first,
        summary,
        decision,
        {
            "benchmark_version": inputs.protocol["benchmark_version"],
            "corpus_id": inputs.corpus["corpus_id"],
            "question_set_id": inputs.question_set["question_set_id"],
            "protocol_id": inputs.protocol["protocol_id"],
            "offline": True,
            "fresh_runs": 2,
            "all_runs_identical": identical,
            "first_projection_id": _projection_id(first),
            "second_projection_id": _projection_id(second),
            "provider_recipe": first_recipe,
            "second_provider_recipe": second_recipe,
            "first_provider_metrics": first_metrics,
            "second_provider_metrics": second_metrics,
            "second_failure_count": sum(row["outcome"] == "failed" for row in second),
            "total_wall_ns": time.perf_counter_ns() - started,
        },
    )
    return decision


def main() -> int:
    """Parse explicit local assets and emit one body-free outcome."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--e5-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = execute(
            arguments.repository_root,
            e5_bundle=arguments.e5_bundle,
            output=arguments.output,
        )
    except FileExistsError:
        print("holdout_output_conflict")
        return 8
    except (OSError, ValueError):
        print("holdout_execution_failed")
        return 6
    print(f"validity={decision['validity']} quality={decision['quality']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
