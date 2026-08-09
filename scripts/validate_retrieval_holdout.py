"""Independently recompute and validate one F034 holdout result directory."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.retrieval_holdout import (
        RESULT_NAMES,
        HoldoutError,
        evaluate_verdict,
        load_holdout,
        load_json,
    )
    from scripts.retrieval_holdout_evaluation import (
        HoldoutEvaluationError,
        render_report,
        summarize,
        validate_rows,
        verdict_checks,
    )
    from scripts.semantic_e2e_benchmark import semantic_projection
except ModuleNotFoundError:
    from retrieval_holdout import (
        RESULT_NAMES,
        HoldoutError,
        evaluate_verdict,
        load_holdout,
        load_json,
    )
    from retrieval_holdout_evaluation import (
        HoldoutEvaluationError,
        render_report,
        summarize,
        validate_rows,
        verdict_checks,
    )
    from semantic_e2e_benchmark import semantic_projection

from openardp.domain.identity import canonical_json_bytes, canonical_sha256


class HoldoutValidationError(ValueError):
    """Stable non-disclosing result validation failure."""


def _canonical_json(path: Path) -> dict[str, Any]:
    value = load_json(path)
    if path.read_bytes() != canonical_json_bytes(value) + b"\n":
        raise HoldoutValidationError("json_not_canonical")
    return value


def _identity(value: dict[str, Any], field: str) -> str:
    declared = value.get(field)
    projected = dict(value)
    projected.pop(field, None)
    if declared != canonical_sha256(projected):
        raise HoldoutValidationError("identity")
    return str(declared)


def _file_fact(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def _projection_id(rows: list[dict[str, Any]]) -> str:
    payload = b"[" + b",".join(semantic_projection(row) for row in rows) + b"]"
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _reject_forbidden_keys(value: object, forbidden: frozenset[str]) -> None:
    if isinstance(value, dict):
        if any(str(key).casefold() in forbidden for key in value):
            raise HoldoutValidationError("body_leak")
        for nested in value.values():
            _reject_forbidden_keys(nested, forbidden)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_keys(nested, forbidden)


def _validate_manifest(
    manifest: dict[str, Any],
    result: Path,
    inputs: Any,
) -> None:
    _identity(manifest, "run_id")
    expected_bindings = {
        "benchmark_version": inputs.protocol["benchmark_version"],
        "corpus_id": inputs.corpus["corpus_id"],
        "question_set_id": inputs.question_set["question_set_id"],
        "protocol_id": inputs.protocol["protocol_id"],
        "offline": True,
        "fresh_runs": 2,
    }
    if any(manifest.get(key) != value for key, value in expected_bindings.items()):
        raise HoldoutValidationError("manifest_binding")
    files = manifest.get("files")
    expected_names = {name for name in RESULT_NAMES if name != "run-manifest.json"}
    if not isinstance(files, dict) or set(files) != expected_names:
        raise HoldoutValidationError("manifest_files")
    if any(files[name] != _file_fact(result / name) for name in expected_names):
        raise HoldoutValidationError("manifest_digest")


def validate(repository_root: Path, result: Path) -> dict[str, Any]:
    """Recompute all metrics, identities, bindings and both verdict axes."""
    inputs = load_holdout(repository_root.resolve(strict=True))
    if result.is_symlink() or not result.is_dir():
        raise HoldoutValidationError("result_directory")
    entries = list(result.iterdir())
    inventory = {path.name for path in entries}
    if inventory != set(RESULT_NAMES) or any(
        path.is_symlink() or not path.is_file() for path in entries
    ):
        raise HoldoutValidationError("result_inventory")
    if sum((result / name).stat().st_size for name in RESULT_NAMES) > int(
        inputs.protocol["result_max_bytes"]
    ):
        raise HoldoutValidationError("result_size")

    observations = _canonical_json(result / "observations.json")
    summary = _canonical_json(result / "summary.json")
    decision = _canonical_json(result / "decision.json")
    manifest = _canonical_json(result / "run-manifest.json")
    _validate_manifest(manifest, result, inputs)
    expected_observation_bindings = {
        "benchmark_version": inputs.protocol["benchmark_version"],
        "corpus_id": inputs.corpus["corpus_id"],
        "question_set_id": inputs.question_set["question_set_id"],
        "protocol_id": inputs.protocol["protocol_id"],
    }
    if set(observations) != {*expected_observation_bindings, "rows"} or any(
        observations.get(key) != value for key, value in expected_observation_bindings.items()
    ):
        raise HoldoutValidationError("observation_binding")
    rows = validate_rows(observations["rows"], inputs.questions)
    forbidden = frozenset(str(key).casefold() for key in inputs.protocol["forbidden_result_keys"])
    for value in (observations, summary, decision, manifest):
        _reject_forbidden_keys(value, forbidden)

    first_projection = _projection_id(rows)
    first_declared = manifest.get("first_projection_id")
    second_declared = manifest.get("second_projection_id")
    if not isinstance(first_declared, str) or not isinstance(second_declared, str):
        raise HoldoutValidationError("projection_shape")
    identical = first_declared == second_declared
    if first_declared != first_projection or manifest.get("all_runs_identical") is not identical:
        raise HoldoutValidationError("projection_binding")
    first_recipe = manifest.get("provider_recipe")
    second_recipe = manifest.get("second_provider_recipe")
    if not isinstance(first_recipe, dict) or not isinstance(second_recipe, dict):
        raise HoldoutValidationError("provider_recipe")
    model_matches = all(
        first_recipe.get(key) == value for key, value in inputs.protocol["model"].items()
    )
    first_metrics = manifest.get("first_provider_metrics")
    second_metrics = manifest.get("second_provider_metrics")
    if not isinstance(first_metrics, dict) or not isinstance(second_metrics, dict):
        raise HoldoutValidationError("provider_metrics")
    for metrics in (first_metrics, second_metrics):
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in metrics.values()
        ):
            raise HoldoutValidationError("provider_metrics")
    second_failure_count = manifest.get("second_failure_count")
    if (
        not isinstance(second_failure_count, int)
        or isinstance(second_failure_count, bool)
        or second_failure_count < 0
    ):
        raise HoldoutValidationError("second_failure_count")

    recomputed_summary = summarize(
        rows,
        inputs.questions,
        corpus_id=str(inputs.corpus["corpus_id"]),
        question_set_id=str(inputs.question_set["question_set_id"]),
        protocol_id=str(inputs.protocol["protocol_id"]),
        fresh_runs_identical=identical,
        provider_metrics=first_metrics,
    )
    if summary != recomputed_summary:
        raise HoldoutValidationError("summary_mismatch")
    failures: list[str] = []
    if any(row["outcome"] == "failed" for row in rows) or second_failure_count:
        failures.append("product_runtime_failure")
    if not identical:
        failures.append("fresh_run_mismatch")
    if first_recipe != second_recipe:
        failures.append("provider_recipe_mismatch")
    if not model_matches:
        failures.append("provider_model_mismatch")
    validity, quality = verdict_checks(summary)
    validity["provider_model_identity"] = model_matches
    validity["provider_recipe_identical"] = first_recipe == second_recipe
    recomputed_decision = evaluate_verdict(
        validity_checks=validity,
        quality_checks=quality,
        failures=tuple(failures),
        summary_id=str(summary["summary_id"]),
    )
    if decision != recomputed_decision:
        raise HoldoutValidationError("decision_mismatch")
    try:
        report = (result / "report.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise HoldoutValidationError("report_invalid") from error
    if report != render_report(summary, decision):
        raise HoldoutValidationError("report_mismatch")
    return decision


def main() -> int:
    """Emit exactly one stable body-free validator outcome."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.repository_root, arguments.result)
    except (OSError, HoldoutError, HoldoutEvaluationError, HoldoutValidationError, ValueError):
        print("holdout_evidence_invalid")
        return 6
    print(f"validity={decision['validity']} quality={decision['quality']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
