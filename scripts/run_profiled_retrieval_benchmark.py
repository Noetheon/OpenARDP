"""Execute counterbalanced F025 profiling and one post-freeze F034 milestone."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

try:
    from scripts.profiled_retrieval_benchmark import (
        PROFILES,
        PROVIDER_PHASES,
        SOURCE_PHASES,
        canonical_file,
        decide,
        load_protocol,
        render_report,
        summarize,
    )
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.retrieval_holdout import HoldoutInputs, load_holdout
    from scripts.run_retrieval_holdout import _compose_workspace as _compose_holdout_workspace
    from scripts.run_semantic_e2e_benchmark import (
        ProductWorkspace,
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from scripts.semantic_e2e_benchmark import load_inputs
except ModuleNotFoundError:
    from profiled_retrieval_benchmark import (
        PROFILES,
        PROVIDER_PHASES,
        SOURCE_PHASES,
        canonical_file,
        decide,
        load_protocol,
        render_report,
        summarize,
    )
    from realworld_corpus import load_corpus_lock, verify_corpus
    from retrieval_holdout import HoldoutInputs, load_holdout
    from run_retrieval_holdout import _compose_workspace as _compose_holdout_workspace
    from run_semantic_e2e_benchmark import (
        ProductWorkspace,
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from semantic_e2e_benchmark import load_inputs

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.adapters.docling_bundle import verify_installation
from openardp.adapters.e5_semantic import IsolatedE5SemanticProvider
from openardp.adapters.semantic_candidates import (
    HybridRetrievalCandidateSource,
    SemanticContextCandidateSource,
)
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_sha256
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.domain.semantic_retrieval import (
    SemanticRetrievalLimits,
    SemanticRetrievalPolicy,
)
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.semantic_retrieval import semantic_algorithm_identity

_PDF_LOCK = Path("model-bundles/pdf-docling-2.114.0-v1/source-lock.json")
_E5_LOCK = Path("model-bundles/multilingual-e5-small-v1/source-lock.json")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-bundle", type=Path, required=True)
    parser.add_argument("--e5-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _delta(after: dict[str, int], before: dict[str, int], names: tuple[str, ...]) -> dict[str, int]:
    return {name: int(after.get(name, 0)) - int(before.get(name, 0)) for name in names}


def _profile_compiler(
    product: ProductWorkspace,
    provider: IsolatedE5SemanticProvider,
    protocol: dict[str, Any],
    profile: str,
) -> tuple[ContextCompilerService, SemanticContextCandidateSource]:
    source_protocol = protocol["candidate"] if profile == PROFILES[1] else None
    parent = protocol["f025_parent"]
    policy_data = (
        source_protocol["semantic_policy"]
        if source_protocol is not None
        else parent["semantic_policy"]
    )
    retrieval = (
        source_protocol["retrieval_profile"]
        if source_protocol is not None
        else parent["retrieval_profile"]
    )
    policy = SemanticRetrievalPolicy(**policy_data)
    limits = SemanticRetrievalLimits(**parent["provider_limits"])
    prepared = profile == PROFILES[1]
    semantic = SemanticContextCandidateSource(
        product.workspace.object_store,
        product.workspace.catalog,
        provider,
        policy,
        limits,
        text_verifier=product.text_verifier,
        rich_verifier=product.rich_verifier,
        source_balanced=True,
        max_per_document=int(retrieval["semantic_max_per_document"]),
        ranked_prefix=int(retrieval["semantic_ranked_prefix"]),
        rich_first=True,
        prepared_corpus=prepared,
    )
    lexical = RelevanceObservingCandidateSource(
        product.workspace.object_store,
        (
            TextLexicalCandidateSource(product.workspace.object_store, product.workspace.catalog),
            RichLexicalCandidateSource(
                product.workspace.object_store,
                product.workspace.catalog,
                representation_verifier=product.rich_verifier,
                prepared_snapshot=prepared,
                relevance_policy=RelevancePolicy() if prepared else None,
            ),
        ),
        RelevancePolicy(),
    )
    allocation = LexicalAllocationPolicy()
    compiler = ContextCompilerService(
        product.workspace.object_store,
        product.workspace.catalog,
        Utf8ByteEstimator(),
        (HybridRetrievalCandidateSource(lexical, semantic),),
        algorithm=semantic_algorithm_identity(
            provider.recipe,
            policy,
            limits,
            allocation,
            hybrid_lexical_fallback=True,
            source_balanced=True,
            semantic_max_per_document=int(retrieval["semantic_max_per_document"]),
            semantic_ranked_prefix=int(retrieval["semantic_ranked_prefix"]),
            rich_first=True,
            prepared_corpus=prepared,
        ),
        allocation_policy=allocation,
        semantic_abstention=True,
        additive_budgeting=prepared,
    )
    return compiler, semantic


def _product_with_compiler(
    product: ProductWorkspace, compiler: ContextCompilerService
) -> ProductWorkspace:
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


def _execute_profile(
    inputs: Any,
    product: ProductWorkspace,
    provider: IsolatedE5SemanticProvider,
    protocol: dict[str, Any],
    suite: str,
    run: int,
    profile: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    compiler, source = _profile_compiler(product, provider, protocol, profile)
    bound = _product_with_compiler(product, compiler)
    context = (
        protocol["f025_parent"]["context"]
        if suite == "f025_development"
        else inputs.protocol["context"]
    )
    observations: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    for ordinal, question_id in enumerate(inputs.by_id):
        source_before = source.phase_metrics
        provider_before = provider.phase_metrics
        rows = _execute_rows(
            inputs,
            bound,
            include_context_audit=True,
            question_ids=frozenset((question_id,)),
            treatments=(profile,),
            csv_supported=True,
            direct_query_treatments=frozenset((profile,)),
            context_override=context,
        )
        if len(rows) != 1:
            raise ValueError("profile_observation_coverage")
        observation = rows[0]
        observations.append(
            {
                "suite": suite,
                "run": run,
                "profile": profile,
                "ordinal": ordinal,
                "observation": observation,
            }
        )
        phases.append(
            {
                "suite": suite,
                "run": run,
                "profile": profile,
                "ordinal": ordinal,
                "wall_ns": int(observation["wall_ns"]),
                "compiler": compiler.last_phase_metrics,
                "source": _delta(source.phase_metrics, source_before, SOURCE_PHASES),
                "provider": _delta(provider.phase_metrics, provider_before, PROVIDER_PHASES),
            }
        )
    return observations, phases, compiler.algorithm.model_dump(mode="json")


def _f025_workspace(
    root: Path,
    workspace_root: Path,
    pdf_bundle: Path,
    manifest: ModelBundleManifest,
) -> tuple[Any, ProductWorkspace]:
    inputs = load_inputs(root)
    assets = load_corpus_lock(root / "corpora/realworld/v0.1.0")["assets"]
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
    return inputs, product


def _f034_workspace(root: Path, workspace_root: Path, inputs: HoldoutInputs) -> ProductWorkspace:
    product = _compose_holdout_workspace(root, workspace_root, inputs)
    _verify_oracle(cast(Any, inputs), product)
    return product


def _file_fact(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def run(root: Path, pdf_bundle: Path, e5_bundle: Path, output: Path) -> dict[str, Any]:
    """Run the frozen profile, publish manifest-last evidence and return its decision."""
    root = root.resolve(strict=True)
    protocol = load_protocol(root)
    verified_pdf = pdf_bundle.resolve(strict=True)
    verify_installation(verified_pdf, expected_source_lock=root / _PDF_LOCK)
    manifest = ModelBundleManifest.model_validate_json(
        (verified_pdf / "manifest.json").read_bytes()
    )
    verify_corpus(root / "corpora/realworld/v0.1.0")
    holdout_inputs = load_holdout(root)
    all_observations: list[dict[str, Any]] = []
    all_phases: list[dict[str, Any]] = []
    algorithms: dict[str, dict[str, Any]] = {}
    provider_recipes: list[dict[str, Any]] = []
    provider_metrics: list[dict[str, int]] = []
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="openardp-f035-workspaces-") as temporary:
        temporary_root = Path(temporary)
        development_inputs: Any | None = None
        for run_number, order in enumerate(protocol["profile_order"]):
            development_inputs, product = _f025_workspace(
                root,
                temporary_root / f"f025-{run_number}",
                verified_pdf,
                manifest,
            )
            provider = IsolatedE5SemanticProvider(
                e5_bundle.resolve(strict=True), expected_source_lock=root / _E5_LOCK
            )
            try:
                recipe = provider.recipe.model_dump(mode="json")
                recipe["recipe_id"] = provider.recipe.recipe_id
                provider_recipes.append(recipe)
                for profile in order:
                    observations, phases, algorithm = _execute_profile(
                        development_inputs,
                        product,
                        provider,
                        protocol,
                        "f025_development",
                        run_number,
                        str(profile),
                    )
                    algorithms[str(profile)] = algorithm
                    all_observations.extend(observations)
                    all_phases.extend(phases)
                provider_metrics.append(provider.metrics)
            finally:
                provider.close()
        if development_inputs is None:
            raise ValueError("development_inputs_missing")
        for run_number in range(int(protocol["holdout_runs"])):
            product = _f034_workspace(root, temporary_root / f"f034-{run_number}", holdout_inputs)
            provider = IsolatedE5SemanticProvider(
                e5_bundle.resolve(strict=True), expected_source_lock=root / _E5_LOCK
            )
            try:
                recipe = provider.recipe.model_dump(mode="json")
                recipe["recipe_id"] = provider.recipe.recipe_id
                provider_recipes.append(recipe)
                observations, phases, algorithm = _execute_profile(
                    cast(Any, holdout_inputs),
                    product,
                    provider,
                    protocol,
                    "f034_holdout",
                    run_number,
                    "f035_candidate",
                )
                algorithms["f035_candidate"] = algorithm
                all_observations.extend(observations)
                all_phases.extend(phases)
                provider_metrics.append(provider.metrics)
            finally:
                provider.close()
    for row in all_observations:
        observation = row["observation"]
        if observation.get("outcome") == "failed":
            failures.append(str(observation.get("failure_category") or "product_runtime_failure"))
    summary = summarize(
        all_observations,
        all_phases,
        protocol,
        development_inputs.by_id,
        holdout_inputs.by_id,
    )
    decision = decide(summary, tuple(failures))
    if output.exists():
        raise ValueError("output_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".f035-stage-", dir=output.parent))
    try:
        canonical_file(
            stage / "observations.json",
            {"protocol_id": protocol["protocol_id"], "rows": all_observations},
        )
        canonical_file(
            stage / "phases.json",
            {"protocol_id": protocol["protocol_id"], "rows": all_phases},
        )
        canonical_file(stage / "summary.json", summary)
        canonical_file(stage / "decision.json", decision)
        (stage / "report.md").write_text(render_report(summary, decision), encoding="utf-8")
        names = (
            "observations.json",
            "phases.json",
            "summary.json",
            "decision.json",
            "report.md",
        )
        run_manifest: dict[str, Any] = {
            "benchmark_version": protocol["benchmark_version"],
            "protocol_id": protocol["protocol_id"],
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "offline": True,
            "profile_order": protocol["profile_order"],
            "algorithms": algorithms,
            "provider_recipes": provider_recipes,
            "provider_metrics": provider_metrics,
            "files": {name: _file_fact(stage / name) for name in names},
        }
        run_manifest["run_id"] = canonical_sha256(run_manifest)
        canonical_file(stage / "run-manifest.json", run_manifest)
        if sum(path.stat().st_size for path in stage.iterdir()) > int(protocol["result_max_bytes"]):
            raise ValueError("result_size")
        os.replace(stage, output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return decision


def main() -> int:
    """Execute with one stable body-free public failure category."""
    arguments = _arguments()
    print("profiled_retrieval_started", flush=True)
    try:
        decision = run(Path.cwd(), arguments.pdf_bundle, arguments.e5_bundle, arguments.output)
    except Exception:
        print("profiled_retrieval_execution_failed", file=sys.stderr)
        return 2
    print(
        f"validity={decision['validity']} development={decision['development_candidate']} "
        f"holdout={decision['holdout_generalization']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
