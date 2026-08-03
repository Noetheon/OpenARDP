"""Execute and publish the exact offline F025 semantic use case."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.semantic_e2e_benchmark import (
        PRODUCT_TREATMENTS,
        RESULT_NAMES,
        SemanticBenchmarkError,
        SemanticInputs,
        atom_matches,
        file_digest,
        load_inputs,
        make_observation,
        selected_observation,
        semantic_projection,
    )
    from scripts.semantic_e2e_evaluation import decide, render_report, summarize
except ModuleNotFoundError:
    from realworld_corpus import load_corpus_lock, verify_corpus
    from semantic_e2e_benchmark import (
        PRODUCT_TREATMENTS,
        RESULT_NAMES,
        SemanticBenchmarkError,
        SemanticInputs,
        atom_matches,
        file_digest,
        load_inputs,
        make_observation,
        selected_observation,
        semantic_projection,
    )
    from semantic_e2e_evaluation import decide, render_report, summarize

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.adapters.docling_bundle import verify_installation
from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    ContextCompileLimits,
    ContextCompileRequest,
    ContextSelectionPolicy,
)
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.rich_ingestion import RichIngestionService

_FIXED_TIME = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
_MODEL_LOCK = Path("model-bundles/pdf-docling-2.114.0-v1/source-lock.json")


@dataclass(frozen=True, slots=True)
class ProductWorkspace:
    """Composed product services and stable source mappings for one fresh run."""

    compiler: ContextCompilerService
    query: DocumentQueryService
    document_ids: tuple[Any, ...]
    source_by_document: dict[str, str]
    oracle_bodies: dict[str, list[str]]
    rich_body_by_id: dict[str, str]
    rich_anchor_by_id: dict[str, str]
    formats: tuple[str, ...]


def _write_json(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes(value) + b"\n"
    path.write_bytes(payload)


def _body_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return canonical_json_bytes(value).decode("utf-8")


def _compose_workspace(
    root: Path,
    workspace_root: Path,
    pdf_bundle: Path,
    manifest: ModelBundleManifest,
    assets: list[dict[str, Any]],
    *,
    relevance_policy: RelevancePolicy | None = None,
) -> ProductWorkspace:
    workspace = LocalWorkspace.initialize(workspace_root, now=_FIXED_TIME)
    entropy = 0

    def bits() -> int:
        nonlocal entropy
        entropy += 1
        return entropy

    text_ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        IsolatedParserAdapter(),
        source_factory=LocalSource,
        clock=lambda: _FIXED_TIME,
        owner_id_factory=lambda: "semantic-benchmark",
        lease_token_factory=lambda: "0" * 64,
        random_bits=bits,
    )
    rich_services = {
        "docx": RichIngestionService(
            workspace.object_store,
            workspace.catalog,
            IsolatedDoclingAdapter(),
            source_factory=LocalSource,
            clock=lambda: _FIXED_TIME,
            owner_id_factory=lambda: "semantic-benchmark",
            lease_token_factory=lambda: "1" * 64,
            random_bits=bits,
        ),
        "pptx": RichIngestionService(
            workspace.object_store,
            workspace.catalog,
            IsolatedDoclingAdapter(),
            source_factory=LocalSource,
            clock=lambda: _FIXED_TIME,
            owner_id_factory=lambda: "semantic-benchmark",
            lease_token_factory=lambda: "2" * 64,
            random_bits=bits,
        ),
        "pdf": RichIngestionService(
            workspace.object_store,
            workspace.catalog,
            IsolatedDoclingAdapter(model_root=pdf_bundle / "assets", model_manifest=manifest),
            source_factory=LocalSource,
            clock=lambda: _FIXED_TIME,
            owner_id_factory=lambda: "semantic-benchmark",
            lease_token_factory=lambda: "3" * 64,
            random_bits=bits,
        ),
    }
    source_by_document: dict[str, str] = {}
    oracle_bodies: dict[str, list[str]] = {}
    rich_body_by_id: dict[str, str] = {}
    rich_anchor_by_id: dict[str, str] = {}
    document_ids: list[Any] = []
    formats: list[str] = []
    corpus = root / "corpora/realworld/v0.1.0"
    for asset in assets:
        format_name = str(asset["format"])
        source_key = str(asset["key"])
        source = corpus / str(asset["path"])
        if format_name == "csv":
            oracle_bodies[source_key] = [source.read_text(encoding="utf-8-sig")]
            continue
        if format_name in {"md", "txt"}:
            result = text_ingestion.ingest(source)
            oracle_bodies[source_key] = [source.read_text(encoding="utf-8")]
        else:
            service = rich_services[format_name]
            result = service.ingest(source)
            artifacts = workspace.catalog.load_rich_representation(result.scope)
            if artifacts is None:
                raise SemanticBenchmarkError("rich_representation_missing")
            service.verify_ready_representation(artifacts)
            bodies: list[str] = []
            for record in artifacts.bundle.records:
                stored = workspace.object_store.verify(
                    record.retrieval_object.object_id,
                    expected_length=record.retrieval_object.byte_length,
                )
                payload = b"".join(workspace.object_store.iter_chunks(stored.object_id))
                body = payload.decode("utf-8")
                projection_id = record.projection.evidence_projection_id
                rich_body_by_id[projection_id] = body
                rich_anchor_by_id[projection_id] = type(record.projection.reference.anchor).__name__
                bodies.append(body)
            oracle_bodies[source_key] = bodies
        source_by_document[str(result.scope.document_id)] = source_key
        document_ids.append(result.scope.document_id)
        formats.append(format_name)
    verifier = rich_services["pdf"].verify_ready_representation
    query = DocumentQueryService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
        representation_verifier=text_ingestion.verify_ready_representation,
        clock=lambda: _FIXED_TIME,
    )
    lexical_sources = (
        TextLexicalCandidateSource(workspace.object_store, workspace.catalog),
        RichLexicalCandidateSource(
            workspace.object_store,
            workspace.catalog,
            representation_verifier=verifier,
        ),
    )
    candidate_sources = (
        (
            RelevanceObservingCandidateSource(
                workspace.object_store,
                lexical_sources,
                relevance_policy,
            ),
        )
        if relevance_policy is not None
        else lexical_sources
    )
    compiler = ContextCompilerService(
        workspace.object_store,
        workspace.catalog,
        Utf8ByteEstimator(),
        candidate_sources,
        relevance_policy=relevance_policy,
    )
    return ProductWorkspace(
        compiler=compiler,
        query=query,
        document_ids=tuple(sorted(document_ids, key=str)),
        source_by_document=source_by_document,
        oracle_bodies=oracle_bodies,
        rich_body_by_id=rich_body_by_id,
        rich_anchor_by_id=rich_anchor_by_id,
        formats=tuple(sorted(formats)),
    )


def _verify_oracle(inputs: SemanticInputs, product: ProductWorkspace) -> None:
    for question in inputs.by_id.values():
        for atom in question["support_atoms"]:
            bodies = product.oracle_bodies.get(str(atom["source_key"]), [])
            if not any(atom_matches(body, atom["variants"]) for body in bodies):
                raise SemanticBenchmarkError(
                    f"oracle_atom_missing:{question['question_id']}:{atom['atom_id']}"
                )


def _selected_rows(
    product: ProductWorkspace,
    question: dict[str, Any],
    treatment: str,
    items: tuple[Any, ...],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for order, item in enumerate(items):
        provenance = item.provenance
        source_key = product.source_by_document[str(provenance.document_id)]
        if provenance.record_type == "block":
            block = product.query.get(provenance.block_id)
            expected = item.content.body if item.content is not None else None
            body = block.text or _body_text(block.structured)
            citation_valid = expected == body
            evidence_id = str(block.block_id)
            anchor_type = "line_range"
        else:
            body = product.rich_body_by_id[provenance.evidence_projection_id]
            expected = item.content.body if item.content is not None else None
            citation_valid = _body_text(expected) == body
            evidence_id = provenance.evidence_projection_id
            anchor_type = product.rich_anchor_by_id[evidence_id]
        selected.append(
            selected_observation(
                order=order,
                evidence_id=evidence_id,
                source_key=source_key,
                representation=item.representation.value,
                anchor_type=anchor_type,
                body=body,
                question=question,
                citation_valid=citation_valid,
            )
        )
    return selected


def _execute_rows(
    inputs: SemanticInputs,
    product: ProductWorkspace,
    *,
    include_context_audit: bool = False,
    question_ids: frozenset[str] | None = None,
    treatments: tuple[str, ...] = PRODUCT_TREATMENTS,
) -> list[dict[str, Any]]:
    context = inputs.protocol["context"]
    limits = ContextCompileLimits(
        max_scopes=context["max_scopes"],
        max_discovered=context["max_discovered"],
        max_candidates=context["max_candidates"],
        max_body_bytes=context["max_body_bytes"],
        max_decisions=context["max_decisions"],
        max_bundle_units=context["max_bundle_units"],
    )
    rows: list[dict[str, Any]] = []
    for question in inputs.by_id.values():
        if question_ids is not None and question["question_id"] not in question_ids:
            continue
        for treatment in treatments:
            if question["answerable"] and "csv" in question["required_formats"]:
                rows.append(
                    make_observation(
                        question,
                        treatment,
                        [],
                        outcome="unsupported_format",
                        failure_category="csv_product_ingestion_unsupported",
                    )
                )
                continue
            task = (
                question["question"]
                if treatment == "openardp_direct"
                else question["operator_query"]
            )
            started = time.perf_counter_ns()
            cpu_started = time.process_time_ns()
            try:
                result = product.compiler.compile(
                    ContextCompileRequest(
                        task=task,
                        document_ids=product.document_ids,
                        budget_limit=context["budget_bytes"],
                        estimator=Utf8ByteEstimator().identity,
                        policy=ContextSelectionPolicy(
                            mode=ContextMode.EXACT,
                            maximum_sensitivity=Sensitivity.UNKNOWN,
                        ),
                        limits=limits,
                    )
                )
                selected = _selected_rows(product, question, treatment, result.bundle.items)
                row = make_observation(
                    question,
                    treatment,
                    selected,
                    wall_ns=time.perf_counter_ns() - started,
                    cpu_ns=time.process_time_ns() - cpu_started,
                )
                if include_context_audit:
                    rejected_reasons = Counter(
                        decision.reason_code for decision in result.receipt.rejected
                    )
                    row["context_audit"] = {
                        "algorithm": result.receipt.algorithm.model_dump(mode="json"),
                        "notices": [notice.code for notice in result.receipt.notices],
                        "rejected_reason_counts": dict(sorted(rejected_reasons.items())),
                        "warnings": [warning.code for warning in result.bundle.warnings],
                    }
            except Exception:
                row = make_observation(
                    question,
                    treatment,
                    [],
                    outcome="failed",
                    failure_category="product_runtime_failure",
                    wall_ns=time.perf_counter_ns() - started,
                    cpu_ns=time.process_time_ns() - cpu_started,
                )
            rows.append(row)
    return rows


def _publish(
    output: Path,
    inputs: SemanticInputs,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    decision: dict[str, Any],
    *,
    model_bundle_id: str,
    total_wall_ns: int,
) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        observations = {
            "benchmark_version": "0.1.0",
            "corpus_id": inputs.protocol["corpus_id"],
            "question_set_id": inputs.questions["question_set_id"],
            "protocol_id": inputs.protocol["protocol_id"],
            "rows": rows,
        }
        _write_json(stage / "observations.json", observations)
        _write_json(stage / "summary.json", summary)
        _write_json(stage / "decision.json", decision)
        (stage / "report.md").write_text(render_report(summary, decision), encoding="utf-8")
        files = {}
        for name in RESULT_NAMES:
            if name == "run-manifest.json":
                continue
            digest, length = file_digest(stage / name)
            files[name] = {"sha256": digest, "byte_length": length}
        manifest: dict[str, Any] = {
            "benchmark_version": "0.1.0",
            "corpus_id": inputs.protocol["corpus_id"],
            "question_set_id": inputs.questions["question_set_id"],
            "protocol_id": inputs.protocol["protocol_id"],
            "model_bundle_id": model_bundle_id,
            "offline": True,
            "fresh_runs": 2,
            "total_wall_ns": total_wall_ns,
            "files": files,
        }
        manifest["run_id"] = canonical_sha256(manifest)
        _write_json(stage / "run-manifest.json", manifest)
        if sum((stage / name).stat().st_size for name in RESULT_NAMES) > int(
            inputs.protocol["execution"]["result_max_bytes"]
        ):
            raise SemanticBenchmarkError("result_size")
        os.replace(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def execute(repository_root: Path, *, pdf_bundle: Path, output: Path) -> dict[str, Any]:
    """Run two fresh product workspaces, require semantic determinism and publish."""
    root = repository_root.resolve(strict=True)
    inputs = load_inputs(root)
    corpus = verify_corpus(root / "corpora/realworld/v0.1.0")
    if corpus.corpus_id != inputs.protocol["corpus_id"]:
        raise SemanticBenchmarkError("corpus_identity")
    assets = load_corpus_lock(root / "corpora/realworld/v0.1.0")["assets"]
    installation = verify_installation(pdf_bundle, expected_source_lock=root / _MODEL_LOCK)
    manifest = ModelBundleManifest.model_validate_json((pdf_bundle / "manifest.json").read_bytes())
    started = time.perf_counter_ns()
    with tempfile.TemporaryDirectory(prefix="openardp-f025-a-") as first_root:
        first_product = _compose_workspace(root, Path(first_root), pdf_bundle, manifest, assets)
        _verify_oracle(inputs, first_product)
        first = _execute_rows(inputs, first_product)
        formats = first_product.formats
    with tempfile.TemporaryDirectory(prefix="openardp-f025-b-") as second_root:
        second_product = _compose_workspace(root, Path(second_root), pdf_bundle, manifest, assets)
        _verify_oracle(inputs, second_product)
        second = _execute_rows(inputs, second_product)
    identical = [semantic_projection(row) for row in first] == [
        semantic_projection(row) for row in second
    ]
    summary = summarize(
        first,
        inputs.by_id,
        corpus_id=inputs.protocol["corpus_id"],
        question_set_id=inputs.questions["question_set_id"],
        protocol_id=inputs.protocol["protocol_id"],
        supported_formats_ingested=formats,
        semantic_runs_identical=identical,
    )
    hard_failures = [] if identical else ["semantic_fresh_run_mismatch"]
    if any(row["outcome"] == "failed" for row in first):
        hard_failures.append("product_runtime_failure")
    decision = decide(summary, inputs.protocol, hard_failures=hard_failures)
    _publish(
        output,
        inputs,
        first,
        summary,
        decision,
        model_bundle_id=installation.bundle_id,
        total_wall_ns=time.perf_counter_ns() - started,
    )
    return decision


def main() -> int:
    """Parse explicit paths and emit one body-free completion line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--pdf-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = execute(
            arguments.repository_root,
            pdf_bundle=arguments.pdf_bundle,
            output=arguments.output,
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
