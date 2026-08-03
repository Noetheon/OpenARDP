"""Run the paired F026/F027 ranking evaluation against frozen F025 inputs."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

from openardp.adapters.docling_bundle import verify_installation
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.rich_ingestion import ModelBundleManifest

try:
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.run_semantic_e2e_benchmark import (
        _compose_workspace,
        _execute_rows,
        _profile_compiler,
        _verify_oracle,
    )
    from scripts.semantic_e2e_benchmark import load_inputs, semantic_projection
except ModuleNotFoundError:
    from realworld_corpus import load_corpus_lock, verify_corpus
    from run_semantic_e2e_benchmark import (
        _compose_workspace,
        _execute_rows,
        _profile_compiler,
        _verify_oracle,
    )
    from semantic_e2e_benchmark import load_inputs, semantic_projection

BENCHMARK_VERSION = "0.1.0"
FOCUSED = frozenset({"Q02", "Q03", "Q06", "Q13", "Q14", "Q17", "Q18", "Q19"})
POSITIVE = frozenset({"Q02", "Q03", "Q06", "Q13", "Q14", "Q19"})
UNSUPPORTED = frozenset({"Q17", "Q18"})
MODEL_LOCK = Path("model-bundles/pdf-docling-2.114.0-v1/source-lock.json")


class RankingBenchmarkError(ValueError):
    """Stable paired ranking benchmark failure."""


def _semantic_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"cpu_ns", "wall_ns"}}


def _metric(value: Fraction) -> dict[str, int | str]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "ratio": f"{float(value):.6f}",
    }


def _metrics(rows: dict[str, dict[str, Any]]) -> dict[str, dict[str, int | str]]:
    positives = [rows[item] for item in sorted(POSITIVE)]
    selected = sum(int(row["selected_count"]) for row in positives)
    relevant = sum(int(row["relevant_count"]) for row in positives)
    reciprocal = sum(
        (Fraction(1, int(row["first_relevant_rank"])) if row["first_relevant_rank"] else Fraction())
        for row in positives
    )
    covered_sources = sum(len(row["covered_source_keys"]) for row in positives)
    required_sources = sum(int(row["required_source_count"]) for row in positives)
    return {
        "evidence_precision": _metric(Fraction(relevant, selected) if selected else Fraction()),
        "mrr": _metric(reciprocal / len(positives)),
        "source_recall": _metric(Fraction(covered_sources, required_sources)),
    }


def _at_least(left: dict[str, int | str], right: dict[str, int | str]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) >= int(right["numerator"]) * int(
        left["denominator"]
    )


def _profile_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {str(row["question_id"]): _semantic_row(row) for row in rows}
    if set(result) != FOCUSED:
        raise RankingBenchmarkError("focused_question_coverage")
    return result


def _result_row(row: dict[str, Any]) -> dict[str, Any]:
    """Project one observation to the minimal body-free independently scored facts."""
    return {
        "abstained": row["abstained"],
        "citation_integrity_complete": row["citation_integrity_complete"],
        "context_audit": row["context_audit"],
        "covered_source_keys": row["covered_source_keys"],
        "first_relevant_rank": row["first_relevant_rank"],
        "full_support": row["full_support"],
        "question_id": row["question_id"],
        "relevant_count": row["relevant_count"],
        "required_source_count": row["required_source_count"],
        "selected_count": row["selected_count"],
        "selected_source_keys": [item["source_key"] for item in row["selected"]],
    }


def _execute_profiles(
    root: Path,
    pdf_bundle: Path,
    manifest: ModelBundleManifest,
    assets: list[dict[str, Any]],
    workspace_root: Path,
    relevance: RelevancePolicy,
    allocation: LexicalAllocationPolicy,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    inputs = load_inputs(root)
    product = _compose_workspace(
        root,
        workspace_root,
        pdf_bundle,
        manifest,
        assets,
        relevance_policy=relevance,
    )
    _verify_oracle(inputs, product)
    f026 = _execute_rows(
        inputs,
        product,
        include_context_audit=True,
        question_ids=FOCUSED,
        treatments=("openardp_direct",),
    )
    ranked = replace(
        product,
        compiler=_profile_compiler(product, relevance, allocation),
    )
    f027 = _execute_rows(
        inputs,
        ranked,
        include_context_audit=True,
        question_ids=FOCUSED,
        treatments=("openardp_direct",),
    )
    return _profile_rows(f026), _profile_rows(f027)


def _gates(
    f026: dict[str, dict[str, Any]],
    f027: dict[str, dict[str, Any]],
    *,
    deterministic: bool,
) -> tuple[dict[str, bool], dict[str, Any]]:
    baseline_metrics = _metrics(f026)
    ranked_metrics = _metrics(f027)
    q03_sources = Counter(item["source_key"] for item in f027["Q03"]["selected"])
    gates = {
        "citation_integrity_preserved": all(
            f027[item]["citation_integrity_complete"] is True for item in POSITIVE
        ),
        "evidence_precision_non_regression": _at_least(
            ranked_metrics["evidence_precision"], baseline_metrics["evidence_precision"]
        ),
        "mrr_non_regression": _at_least(ranked_metrics["mrr"], baseline_metrics["mrr"]),
        "positive_support_preserved": all(f027[item]["full_support"] is True for item in POSITIVE),
        "q03_document_quota": bool(q03_sources)
        and max(q03_sources.values()) <= LexicalAllocationPolicy().max_per_document,
        "semantic_runs_identical": deterministic,
        "source_recall_non_regression": _at_least(
            ranked_metrics["source_recall"], baseline_metrics["source_recall"]
        ),
        "unsupported_abstained": all(
            f027[item]["abstained"] is True
            and f027[item]["selected_count"] == 0
            and f027[item]["context_audit"]["warnings"] == ["no_relevant_evidence"]
            for item in UNSUPPORTED
        ),
    }
    comparison = {
        "f026": baseline_metrics,
        "f027": ranked_metrics,
        "q03_selected_by_source": dict(sorted(q03_sources.items())),
    }
    return gates, comparison


def _report(result: dict[str, Any]) -> str:
    lines = [
        "# F027 Lexical Ranking and Diversity",
        "",
        f"Decision: `{result['decision']}`.",
        "",
        "| Metric | F026 | F027 |",
        "|---|---:|---:|",
    ]
    for name in ("evidence_precision", "mrr", "source_recall"):
        lines.append(
            f"| {name} | {result['comparison']['f026'][name]['ratio']} | "
            f"{result['comparison']['f027'][name]['ratio']} |"
        )
    lines.extend(
        [
            "",
            "The same frozen F025 questions and already-ingested workspace are evaluated "
            "by both profiles. No benchmark answer or expected source is available to "
            "runtime ranking.",
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


def execute(repository_root: Path, *, pdf_bundle: Path, output: Path) -> dict[str, Any]:
    """Run both profiles in two fresh workspaces and publish body-free evidence."""
    root = repository_root.resolve(strict=True)
    inputs = load_inputs(root)
    corpus = verify_corpus(root / "corpora/realworld/v0.1.0")
    assets = load_corpus_lock(root / "corpora/realworld/v0.1.0")["assets"]
    installation = verify_installation(pdf_bundle, expected_source_lock=root / MODEL_LOCK)
    manifest = ModelBundleManifest.model_validate_json((pdf_bundle / "manifest.json").read_bytes())
    relevance = RelevancePolicy()
    allocation = LexicalAllocationPolicy()
    executions = []
    for suffix in ("a", "b"):
        with tempfile.TemporaryDirectory(prefix=f"openardp-f027-{suffix}-") as workspace_root:
            executions.append(
                _execute_profiles(
                    root,
                    pdf_bundle,
                    manifest,
                    assets,
                    Path(workspace_root),
                    relevance,
                    allocation,
                )
            )
    deterministic = all(
        [semantic_projection(row) for row in executions[0][profile].values()]
        == [semantic_projection(row) for row in executions[1][profile].values()]
        for profile in (0, 1)
    )
    f026, f027 = executions[0]
    gates, comparison = _gates(f026, f027, deterministic=deterministic)
    payload: dict[str, Any] = {
        "allocation_policy": allocation.model_dump(mode="json"),
        "allocation_policy_id": allocation.policy_id,
        "benchmark_version": BENCHMARK_VERSION,
        "comparison": comparison,
        "corpus_id": corpus.corpus_id,
        "decision": "LEXICAL_RANKING_READY" if all(gates.values()) else "LEXICAL_RANKING_NOT_READY",
        "focused_question_ids": sorted(FOCUSED),
        "gates": gates,
        "model_bundle_id": installation.bundle_id,
        "profiles": {
            "f026": {key: _result_row(row) for key, row in f026.items()},
            "f027": {key: _result_row(row) for key, row in f027.items()},
        },
        "protocol_id": inputs.protocol["protocol_id"],
        "question_set_id": inputs.questions["question_set_id"],
        "relevance_policy_id": relevance.policy_id,
    }
    payload["result_id"] = canonical_sha256(payload)
    _publish(output, payload)
    return payload


def main() -> int:
    """Parse explicit paths and emit one body-free completion line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--pdf-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = execute(
            arguments.repository_root,
            pdf_bundle=arguments.pdf_bundle,
            output=arguments.output,
        )
    except FileExistsError:
        print("ranking_benchmark_output_conflict")
        return 8
    except (OSError, ValueError):
        print("ranking_benchmark_failed")
        return 6
    print(f"decision={result['decision']} result_id={result['result_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
