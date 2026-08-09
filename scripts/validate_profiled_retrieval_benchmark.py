"""Independently validate one F035 result directory without importing its producer."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.profiled_retrieval_benchmark import (
        RESULT_NAMES,
        ProfiledRetrievalError,
        decide,
        load_json,
        load_protocol,
        render_report,
        summarize,
    )
    from scripts.retrieval_holdout import load_holdout
    from scripts.semantic_e2e_benchmark import load_inputs
except ModuleNotFoundError:
    from profiled_retrieval_benchmark import (
        RESULT_NAMES,
        ProfiledRetrievalError,
        decide,
        load_json,
        load_protocol,
        render_report,
        summarize,
    )
    from retrieval_holdout import load_holdout
    from semantic_e2e_benchmark import load_inputs

from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.semantic_retrieval import (
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticRetrievalPolicy,
)
from openardp.services.semantic_retrieval import semantic_algorithm_identity

_FORBIDDEN = frozenset({"body", "content", "hostname", "path", "query", "question", "username"})


class ProfiledRetrievalValidationError(ValueError):
    """Stable non-disclosing independent-validation failure."""


def _canonical(path: Path) -> dict[str, Any]:
    value = load_json(path)
    if path.read_bytes() != canonical_json_bytes(value) + b"\n":
        raise ProfiledRetrievalValidationError("json_not_canonical")
    return value


def _identity(value: dict[str, Any], field: str) -> str:
    declared = value.get(field)
    projected = dict(value)
    projected.pop(field, None)
    if declared != canonical_sha256(projected):
        raise ProfiledRetrievalValidationError("identity")
    return str(declared)


def _file_fact(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def _reject_forbidden(value: object) -> None:
    if isinstance(value, dict):
        if any(str(key).casefold() in _FORBIDDEN for key in value):
            raise ProfiledRetrievalValidationError("body_or_path_leak")
        for nested in value.values():
            _reject_forbidden(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden(nested)


def validate(root: Path, result: Path) -> dict[str, Any]:
    """Recompute every identity, phase relation, metric and verdict."""
    root = root.resolve(strict=True)
    protocol = load_protocol(root)
    f025 = load_inputs(root)
    f034 = load_holdout(root)
    if result.is_symlink() or not result.is_dir():
        raise ProfiledRetrievalValidationError("result_directory")
    entries = tuple(result.iterdir())
    if {path.name for path in entries} != set(RESULT_NAMES) or any(
        path.is_symlink() or not path.is_file() for path in entries
    ):
        raise ProfiledRetrievalValidationError("result_inventory")
    if sum(path.stat().st_size for path in entries) > int(protocol["result_max_bytes"]):
        raise ProfiledRetrievalValidationError("result_size")
    observations = _canonical(result / "observations.json")
    phases = _canonical(result / "phases.json")
    summary = _canonical(result / "summary.json")
    decision = _canonical(result / "decision.json")
    manifest = _canonical(result / "run-manifest.json")
    for value in (observations, phases, summary, decision, manifest):
        _reject_forbidden(value)
    if set(observations) != {"protocol_id", "rows"} or set(phases) != {
        "protocol_id",
        "rows",
    }:
        raise ProfiledRetrievalValidationError("result_shape")
    if (
        observations["protocol_id"] != protocol["protocol_id"]
        or phases["protocol_id"] != protocol["protocol_id"]
    ):
        raise ProfiledRetrievalValidationError("protocol_binding")
    if not isinstance(observations["rows"], list) or not isinstance(phases["rows"], list):
        raise ProfiledRetrievalValidationError("row_shape")
    recomputed = summarize(observations["rows"], phases["rows"], protocol, f025.by_id, f034.by_id)
    if summary != recomputed:
        raise ProfiledRetrievalValidationError("summary_mismatch")
    failures = tuple(
        str(row["observation"].get("failure_category") or "product_runtime_failure")
        for row in observations["rows"]
        if row["observation"].get("outcome") == "failed"
    )
    recomputed_decision = decide(summary, failures)
    if decision != recomputed_decision:
        raise ProfiledRetrievalValidationError("decision_mismatch")
    if (result / "report.md").read_text(encoding="utf-8") != render_report(summary, decision):
        raise ProfiledRetrievalValidationError("report_mismatch")
    if (
        manifest.get("protocol_id") != protocol["protocol_id"]
        or manifest.get("profile_order") != protocol["profile_order"]
    ):
        raise ProfiledRetrievalValidationError("manifest_binding")
    _identity(manifest, "run_id")
    expected_files = {
        name: _file_fact(result / name) for name in RESULT_NAMES if name != "run-manifest.json"
    }
    if manifest.get("files") != expected_files:
        raise ProfiledRetrievalValidationError("manifest_digest")
    algorithms = manifest.get("algorithms")
    recipes = manifest.get("provider_recipes")
    metrics = manifest.get("provider_metrics")
    if (
        not isinstance(algorithms, dict)
        or set(algorithms) != {"f029_baseline", "f035_candidate"}
        or not isinstance(recipes, list)
        or len(recipes) != 2 + int(protocol["holdout_runs"])
        or any(recipe != recipes[0] for recipe in recipes)
        or not isinstance(metrics, list)
        or len(metrics) != len(recipes)
    ):
        raise ProfiledRetrievalValidationError("provider_binding")
    raw_recipe = dict(recipes[0])
    declared_recipe_id = raw_recipe.pop("recipe_id", None)
    recipe = SemanticProviderRecipe.model_validate(raw_recipe)
    if declared_recipe_id != recipe.recipe_id:
        raise ProfiledRetrievalValidationError("provider_recipe_identity")
    parent = protocol["f025_parent"]
    limits = SemanticRetrievalLimits(**parent["provider_limits"])
    allocation = LexicalAllocationPolicy()
    expected_baseline = semantic_algorithm_identity(
        recipe,
        SemanticRetrievalPolicy(**parent["semantic_policy"]),
        limits,
        allocation,
        hybrid_lexical_fallback=True,
        source_balanced=True,
        semantic_max_per_document=int(parent["retrieval_profile"]["semantic_max_per_document"]),
        semantic_ranked_prefix=int(parent["retrieval_profile"]["semantic_ranked_prefix"]),
        rich_first=True,
    )
    candidate = protocol["candidate"]
    expected_candidate = semantic_algorithm_identity(
        recipe,
        SemanticRetrievalPolicy(**candidate["semantic_policy"]),
        limits,
        allocation,
        hybrid_lexical_fallback=True,
        source_balanced=True,
        semantic_max_per_document=int(candidate["retrieval_profile"]["semantic_max_per_document"]),
        semantic_ranked_prefix=int(candidate["retrieval_profile"]["semantic_ranked_prefix"]),
        rich_first=True,
        prepared_corpus=True,
    )
    expected_algorithms = {
        "f029_baseline": expected_baseline.model_dump(mode="json"),
        "f035_candidate": expected_candidate.model_dump(mode="json"),
    }
    if algorithms != expected_algorithms:
        raise ProfiledRetrievalValidationError("algorithm_binding")
    return decision


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    return parser.parse_args()


def main() -> int:
    """Validate with one stable public success/failure line."""
    arguments = _arguments()
    try:
        decision = validate(Path.cwd(), arguments.result)
    except (ProfiledRetrievalError, ProfiledRetrievalValidationError, OSError, ValueError):
        print("profiled_retrieval_validation_failed", file=sys.stderr)
        return 2
    print(
        f"profiled_retrieval_valid development={decision['development_candidate']} "
        f"holdout={decision['holdout_generalization']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
