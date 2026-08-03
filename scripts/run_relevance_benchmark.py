"""Run the focused F026 minimum-relevance comparison against frozen F025 inputs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from openardp.adapters.docling_bundle import verify_installation
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.rich_ingestion import ModelBundleManifest

try:
    from scripts.realworld_corpus import load_corpus_lock, verify_corpus
    from scripts.run_semantic_e2e_benchmark import (
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from scripts.semantic_e2e_benchmark import load_inputs, semantic_projection
except ModuleNotFoundError:
    from realworld_corpus import load_corpus_lock, verify_corpus
    from run_semantic_e2e_benchmark import (
        _compose_workspace,
        _execute_rows,
        _verify_oracle,
    )
    from semantic_e2e_benchmark import load_inputs, semantic_projection

BENCHMARK_VERSION = "0.1.0"
FOCUSED_QUESTIONS = frozenset({"Q02", "Q03", "Q06", "Q13", "Q14", "Q17", "Q18", "Q19"})
PRIOR_SUCCESS = frozenset({"Q02", "Q03", "Q06", "Q13", "Q14", "Q19"})
UNSUPPORTED = frozenset({"Q17", "Q18"})
BASELINE = Path("benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64")
MODEL_LOCK = Path("model-bundles/pdf-docling-2.114.0-v1/source-lock.json")


class RelevanceBenchmarkError(ValueError):
    """Stable focused comparison failure."""


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RelevanceBenchmarkError("json_shape")
    return value


def _semantic_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"cpu_ns", "wall_ns"}}


def _comparison(
    baseline_rows: dict[str, dict[str, Any]],
    treatment_rows: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for question_id in sorted(FOCUSED_QUESTIONS):
        baseline = baseline_rows[question_id]
        treatment = treatment_rows[question_id]
        result.append(
            {
                "question_id": question_id,
                "baseline": {
                    "abstained": baseline["abstained"],
                    "covered_atom_ids": baseline["covered_atom_ids"],
                    "full_support": baseline["full_support"],
                    "selected_count": baseline["selected_count"],
                },
                "minimum_relevance": {
                    "abstained": treatment["abstained"],
                    "citation_integrity_complete": treatment["citation_integrity_complete"],
                    "covered_atom_ids": treatment["covered_atom_ids"],
                    "full_support": treatment["full_support"],
                    "selected_count": treatment["selected_count"],
                },
            }
        )
    return result


def _evaluate(rows: dict[str, dict[str, Any]], identical: bool) -> dict[str, bool]:
    prior_success_preserved = all(rows[item]["full_support"] is True for item in PRIOR_SUCCESS)
    unsupported_abstained = all(
        rows[item]["abstained"] is True
        and rows[item]["context_audit"]["warnings"] == ["no_relevant_evidence"]
        and "no_relevant_evidence" in rows[item]["context_audit"]["notices"]
        for item in UNSUPPORTED
    )
    citation_integrity_preserved = all(
        rows[item]["citation_integrity_complete"] is True for item in PRIOR_SUCCESS
    )
    return {
        "citation_integrity_preserved": citation_integrity_preserved,
        "prior_success_preserved": prior_success_preserved,
        "semantic_runs_identical": identical,
        "unsupported_abstained": unsupported_abstained,
    }


def _report(result: dict[str, Any]) -> str:
    lines = [
        "# F026 Minimum-Relevance Comparison",
        "",
        f"Decision: `{result['decision']}`.",
        "",
        "| Question | Baseline selected | F026 selected | Baseline support | "
        "F026 support | F026 abstained |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["comparison"]:
        baseline = row["baseline"]
        treatment = row["minimum_relevance"]
        lines.append(
            f"| {row['question_id']} | {baseline['selected_count']} | "
            f"{treatment['selected_count']} | {baseline['full_support']} | "
            f"{treatment['full_support']} | {treatment['abstained']} |"
        )
    lines.extend(
        [
            "",
            "The comparison uses the unchanged F025 corpus, question-set and protocol identities. "
            "It evaluates only the six frozen prior-success questions and two frozen "
            "unsupported questions.",
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
    """Run two fresh focused product workspaces and publish a body-free comparison."""
    root = repository_root.resolve(strict=True)
    inputs = load_inputs(root)
    corpus = verify_corpus(root / "corpora/realworld/v0.1.0")
    assets = load_corpus_lock(root / "corpora/realworld/v0.1.0")["assets"]
    installation = verify_installation(pdf_bundle, expected_source_lock=root / MODEL_LOCK)
    manifest = ModelBundleManifest.model_validate_json((pdf_bundle / "manifest.json").read_bytes())
    policy = RelevancePolicy()
    executions: list[list[dict[str, Any]]] = []
    for suffix in ("a", "b"):
        with tempfile.TemporaryDirectory(prefix=f"openardp-f026-{suffix}-") as workspace_root:
            product = _compose_workspace(
                root,
                Path(workspace_root),
                pdf_bundle,
                manifest,
                assets,
                relevance_policy=policy,
            )
            _verify_oracle(inputs, product)
            executions.append(
                _execute_rows(
                    inputs,
                    product,
                    include_context_audit=True,
                    question_ids=FOCUSED_QUESTIONS,
                    treatments=("openardp_direct",),
                )
            )
    identical = [semantic_projection(row) for row in executions[0]] == [
        semantic_projection(row) for row in executions[1]
    ]
    rows = {_row["question_id"]: _semantic_row(_row) for _row in executions[0]}
    baseline_result = _load_json(root / BASELINE / "observations.json")
    baseline_rows = {
        row["question_id"]: row
        for row in baseline_result["rows"]
        if row["treatment"] == "openardp_direct" and row["question_id"] in FOCUSED_QUESTIONS
    }
    if set(rows) != FOCUSED_QUESTIONS or set(baseline_rows) != FOCUSED_QUESTIONS:
        raise RelevanceBenchmarkError("focused_question_coverage")
    gates = _evaluate(rows, identical)
    payload: dict[str, Any] = {
        "benchmark_version": BENCHMARK_VERSION,
        "baseline_run_id": _load_json(root / BASELINE / "run-manifest.json")["run_id"],
        "corpus_id": corpus.corpus_id,
        "question_set_id": inputs.questions["question_set_id"],
        "protocol_id": inputs.protocol["protocol_id"],
        "model_bundle_id": installation.bundle_id,
        "relevance_policy": policy.model_dump(mode="json"),
        "relevance_policy_id": policy.policy_id,
        "focused_question_ids": sorted(FOCUSED_QUESTIONS),
        "rows": [rows[item] for item in sorted(rows)],
        "comparison": _comparison(baseline_rows, rows),
        "gates": gates,
        "decision": (
            "RELEVANCE_ABSTENTION_READY"
            if all(gates.values())
            else "RELEVANCE_ABSTENTION_NOT_READY"
        ),
    }
    payload["result_id"] = canonical_sha256(payload)
    _publish(output, payload)
    return payload


def main() -> int:
    """Parse explicit benchmark paths and emit one body-free completion line."""
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
        print("relevance_benchmark_output_conflict")
        return 8
    except (OSError, ValueError):
        print("relevance_benchmark_failed")
        return 6
    print(f"decision={result['decision']} result_id={result['result_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
