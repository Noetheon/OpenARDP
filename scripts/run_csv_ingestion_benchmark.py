"""Evaluate stable CSV ingestion against the unchanged frozen F025 CSV questions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.block import ContentBlock
from openardp.domain.common import validate_json
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.ingestion import IngestionDisposition, IngestionResult
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.search import SearchService

try:
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.semantic_e2e_benchmark import (
        atom_matches,
        load_inputs,
        make_observation,
        selected_observation,
        semantic_projection,
    )
except ModuleNotFoundError:
    from realworld_corpus import load_corpus_lock, verify_corpus
    from semantic_e2e_benchmark import (
        atom_matches,
        load_inputs,
        make_observation,
        selected_observation,
        semantic_projection,
    )

BENCHMARK_VERSION = "0.1.0"
CSV_QUESTIONS = frozenset({"Q15", "Q16"})
CSV_SOURCE_KEY = "cisa-known-exploited-vulnerabilities"
FIXED_TIME = datetime(2026, 8, 3, 3, 0, tzinfo=UTC)


class CsvIngestionBenchmarkError(ValueError):
    """Stable CSV benchmark execution failure."""


@dataclass(frozen=True, slots=True)
class _CsvProduct:
    """Minimal stable CSV product composition for one fresh workspace."""

    workspace: LocalWorkspace
    ingestion: IngestionService
    query: DocumentQueryService
    search: SearchService
    result: IngestionResult


def _source_records(source: Path) -> tuple[list[dict[str, Any]], list[list[int]]]:
    """Independently project the locked source with only the Python CSV reader."""
    text = source.read_text(encoding="utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    header: list[str] | None = None
    projections: list[dict[str, Any]] = []
    ranges: list[list[int]] = []
    prior_line = 0
    for record_number, row in enumerate(reader, start=1):
        line_end = reader.line_num
        ranges.append([prior_line + 1, line_end])
        prior_line = line_end
        if header is None:
            header = list(row)
            projections.append({"header": header, "record": record_number, "type": "csv_header"})
        else:
            projections.append(
                {
                    "fields": [
                        [header[index] if index < len(header) else None, value]
                        for index, value in enumerate(row)
                    ],
                    "record": record_number,
                    "type": "csv_record",
                }
            )
    return projections, ranges


def _product_csv_facts(
    product: _CsvProduct,
    source: Path,
) -> dict[str, Any]:
    """Reverify native and normalized CSV artifacts, then discard all bodies."""
    document_id = product.result.scope.document_id
    aggregate = product.workspace.catalog.resolve_ready_representation(
        document_id,
        version_id=None,
    )
    if aggregate is None:
        raise CsvIngestionBenchmarkError("csv_representation_missing")
    product.ingestion.verify_ready_representation(aggregate)
    native = aggregate.representation.native_object
    manifest = aggregate.representation.manifest_object
    if native is None or manifest is None:
        raise CsvIngestionBenchmarkError("csv_artifacts_missing")
    native_bytes = b"".join(product.workspace.object_store.iter_chunks(native.object_id))
    source_bytes = source.read_bytes()
    blocks: list[ContentBlock] = []
    projections: list[Any] = []
    ranges: list[list[int]] = []
    for item in aggregate.blocks:
        payload = b"".join(product.workspace.object_store.iter_chunks(item.object.object_id))
        block = validate_json(ContentBlock, payload)
        if block.text is None:
            raise CsvIngestionBenchmarkError("csv_block_not_text")
        blocks.append(block)
        projections.append(json.loads(block.text))
        ranges.append([item.line_start, item.line_end])
    source_records, source_ranges = _source_records(source)
    source_table_id = canonical_sha256(source_records)
    product_table_id = canonical_sha256(projections)
    block_set_id = canonical_sha256(
        [
            {
                "canonical_hash": block.canonical_hash,
                "extraction_method": block.source.extraction_method,
                "record": block.source.extensions.get("openardp.csv"),
            }
            for block in blocks
        ]
    )
    cache = product.ingestion.ingest(source)
    return {
        "block_count": len(blocks),
        "block_set_id": block_set_id,
        "cache_hit": cache.disposition is IngestionDisposition.CACHE_HIT,
        "canonical_derived_bytes": manifest.byte_length
        + sum(item.object.byte_length for item in aggregate.blocks),
        "cell_count": sum(
            len(record.get("header", record.get("fields", []))) for record in source_records
        ),
        "logical_records_complete": projections == source_records,
        "native_bytes": len(native_bytes),
        "native_id": native.object_id,
        "native_matches_source": native_bytes == source_bytes,
        "product_line_ranges_id": canonical_sha256(ranges),
        "product_table_id": product_table_id,
        "record_count": len(source_records),
        "source_id": "sha256:" + hashlib.sha256(source_bytes).hexdigest(),
        "source_line_ranges_id": canonical_sha256(source_ranges),
        "source_table_id": source_table_id,
    }


def _result_row(row: dict[str, Any]) -> dict[str, Any]:
    """Retain only body-free semantic and allocation facts."""
    return {
        "abstained": row["abstained"],
        "citation_integrity_complete": row["citation_integrity_complete"],
        "covered_source_keys": row["covered_source_keys"],
        "first_relevant_rank": row["first_relevant_rank"],
        "failure_category": row["failure_category"],
        "full_support": row["full_support"],
        "outcome": row["outcome"],
        "question_id": row["question_id"],
        "relevant_count": row["relevant_count"],
        "required_source_count": row["required_source_count"],
        "selected_count": row["selected_count"],
        "treatment": row["treatment"],
    }


def _compose_csv(source: Path, workspace_root: Path) -> _CsvProduct:
    workspace = LocalWorkspace.initialize(workspace_root, now=FIXED_TIME)
    ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        IsolatedParserAdapter(parser_kind="csv"),
        source_factory=LocalSource,
        clock=lambda: FIXED_TIME,
        owner_id_factory=lambda: "csv-benchmark",
        lease_token_factory=lambda: "5" * 64,
        random_bits=lambda: 1,
    )
    result = ingestion.ingest(source)
    query = DocumentQueryService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
        representation_verifier=ingestion.verify_ready_representation,
        clock=lambda: FIXED_TIME,
    )
    return _CsvProduct(
        workspace=workspace,
        ingestion=ingestion,
        query=query,
        search=SearchService(
            workspace.object_store,
            workspace.catalog,
            source_factory=LocalSource,
            clock=lambda: FIXED_TIME,
        ),
        result=result,
    )


def _search_rows(inputs: Any, product: _CsvProduct) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    document = str(product.result.scope.document_id)
    for question_id in sorted(CSV_QUESTIONS):
        question = inputs.by_id[question_id]
        for treatment in ("openardp_direct", "openardp_operator"):
            raw_query = (
                question["question"]
                if treatment == "openardp_direct"
                else question["operator_query"]
            )
            outcome = product.search.search(raw_query, document=document, limit=100)
            selected: list[dict[str, Any]] = []
            for order, hit in enumerate(outcome.hits):
                block = product.query.get(hit.block_id)
                body = block.text or canonical_json_bytes(block.structured).decode("utf-8")
                selected.append(
                    selected_observation(
                        order=order,
                        evidence_id=str(block.block_id),
                        source_key=CSV_SOURCE_KEY,
                        representation="exact",
                        anchor_type="line_range",
                        body=body,
                        question=question,
                        citation_valid=True,
                    )
                )
            rows.append(make_observation(question, treatment, selected))
    return rows


def _run_once(
    root: Path,
    asset: dict[str, Any],
    workspace_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    inputs = load_inputs(root)
    source = root / "corpora/realworld/v0.1.0" / str(asset["path"])
    source_body = source.read_text(encoding="utf-8-sig")
    for question_id in CSV_QUESTIONS:
        for atom in inputs.by_id[question_id]["support_atoms"]:
            if not atom_matches(source_body, atom["variants"]):
                raise CsvIngestionBenchmarkError("csv_oracle_atom_missing")
    product = _compose_csv(source, workspace_root)
    return _product_csv_facts(product, source), _search_rows(inputs, product)


def _gates(
    csv_facts: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    deterministic: bool,
) -> dict[str, bool]:
    operator = {
        str(row["question_id"]): row for row in rows if row["treatment"] == "openardp_operator"
    }
    return {
        "cache_reused": csv_facts["cache_hit"] is True,
        "citation_integrity_complete": set(operator) == CSV_QUESTIONS
        and all(row["citation_integrity_complete"] is True for row in operator.values()),
        "logical_records_complete": csv_facts["logical_records_complete"] is True
        and csv_facts["product_table_id"] == csv_facts["source_table_id"],
        "native_source_exact": csv_facts["native_matches_source"] is True
        and csv_facts["native_id"] == csv_facts["source_id"],
        "operator_support_complete": set(operator) == CSV_QUESTIONS
        and all(row["full_support"] is True for row in operator.values()),
        "physical_line_provenance_complete": csv_facts["product_line_ranges_id"]
        == csv_facts["source_line_ranges_id"],
        "realworld_record_coverage": csv_facts["record_count"] == 1_656
        and csv_facts["block_count"] == 1_656,
        "required_source_complete": set(operator) == CSV_QUESTIONS
        and all(row["covered_source_keys"] == [CSV_SOURCE_KEY] for row in operator.values()),
        "semantic_runs_identical": deterministic,
        "stable_product_outcomes": all(row["outcome"] == "pass" for row in rows),
    }


def _report(result: dict[str, Any]) -> str:
    rows = result["rows"]
    lines = [
        "# F028 Stable CSV Ingestion",
        "",
        f"Decision: `{result['decision']}`.",
        "",
        f"Logical records: {result['csv']['record_count']}; cells: {result['csv']['cell_count']}.",
        f"Source bytes: {result['csv']['native_bytes']}; canonical derived bytes: "
        f"{result['csv']['canonical_derived_bytes']}.",
        "",
        "| Question | Treatment | Full support | Selected | First relevant rank |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['question_id']} | {row['treatment']} | {row['full_support']} | "
            f"{row['selected_count']} | {row['first_relevant_rank']} |"
        )
    lines.extend(
        [
            "",
            "The exact F025 CSV questions and oracle are reused without changing their bytes. "
            "Direct outcomes are reported, while the acceptance gate requires the declared "
            "operator queries "
            "to retrieve exact verified source-backed evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def _publish(output: Path, result: dict[str, Any]) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        (stage / "result.json").write_bytes(canonical_json_bytes(result) + b"\n")
        (stage / "report.md").write_text(_report(result), encoding="utf-8")
        os.replace(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def execute(repository_root: Path, *, output: Path) -> dict[str, Any]:
    """Run F028 twice in fresh workspaces and publish body-free evidence."""
    root = repository_root.resolve(strict=True)
    inputs = load_inputs(root)
    corpus = verify_corpus(root / "corpora/realworld/v0.1.0")
    assets = load_corpus_lock(root / "corpora/realworld/v0.1.0")["assets"]
    csv_asset = next(item for item in assets if item["key"] == CSV_SOURCE_KEY)
    executions: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for suffix in ("a", "b"):
        with tempfile.TemporaryDirectory(prefix=f"openardp-f028-{suffix}-") as workspace:
            executions.append(_run_once(root, csv_asset, Path(workspace)))
    first_facts, first_rows = executions[0]
    second_facts, second_rows = executions[1]
    deterministic = first_facts == second_facts and [
        semantic_projection(row) for row in first_rows
    ] == [semantic_projection(row) for row in second_rows]
    gates = _gates(first_facts, first_rows, deterministic=deterministic)
    payload: dict[str, Any] = {
        "benchmark_version": BENCHMARK_VERSION,
        "corpus_id": corpus.corpus_id,
        "csv": first_facts,
        "decision": "CSV_INGESTION_READY" if all(gates.values()) else "CSV_INGESTION_NOT_READY",
        "gates": gates,
        "protocol_id": inputs.protocol["protocol_id"],
        "question_ids": sorted(CSV_QUESTIONS),
        "question_set_id": inputs.questions["question_set_id"],
        "rows": [_result_row(row) for row in first_rows],
    }
    payload["result_id"] = canonical_sha256(payload)
    _publish(output, payload)
    return payload


def main() -> int:
    """Parse explicit paths and emit one body-free completion line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = execute(
            arguments.repository_root,
            output=arguments.output,
        )
    except FileExistsError:
        print("csv_ingestion_benchmark_output_conflict")
        return 8
    except (OSError, ValueError):
        print("csv_ingestion_benchmark_failed")
        return 6
    print(f"decision={result['decision']} result_id={result['result_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
