"""Frozen contracts and body-free observation helpers for F025."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from openardp.domain.identity import canonical_json_bytes, canonical_sha256

BENCHMARK_VERSION = "0.1.0"
CORPUS_ID = "sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd"
PRODUCT_TREATMENTS = ("openardp_direct", "openardp_operator")
QUESTION_IDS = tuple(f"Q{value:02d}" for value in range(1, 20))
STRATA = (
    "cross_language",
    "direct",
    "multi_source",
    "paraphrase",
    "source_discrimination",
    "unsupported",
)
FORMATS = ("csv", "docx", "md", "pdf", "pptx", "txt")
RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SPACE = re.compile(r"\s+")


class SemanticBenchmarkError(ValueError):
    """Stable input, execution or evaluation contract failure."""


@dataclass(frozen=True, slots=True)
class SemanticInputs:
    """Exact validated protocol and question fixture."""

    protocol: dict[str, Any]
    questions: dict[str, Any]
    by_id: dict[str, dict[str, Any]]


def load_json(path: Path, *, maximum_bytes: int = 1_048_576) -> dict[str, Any]:
    """Load a bounded duplicate-key-rejecting JSON object."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise SemanticBenchmarkError("json_file")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise SemanticBenchmarkError("json_duplicate_key")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                SemanticBenchmarkError("json_non_finite")
            ),
        )
    except SemanticBenchmarkError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SemanticBenchmarkError("json_invalid") from error
    if not isinstance(value, dict):
        raise SemanticBenchmarkError("json_shape")
    return value


def normalize_atom(value: str) -> str:
    """Apply only the frozen NFC, casefold and whitespace normalization."""
    return _SPACE.sub(" ", unicodedata.normalize("NFC", value).casefold()).strip()


def atom_matches(body: str, variants: list[str]) -> bool:
    """Return whether any frozen exact variant occurs in one evidence body."""
    normalized = normalize_atom(body)
    return any(normalize_atom(variant) in normalized for variant in variants)


def _identity(value: dict[str, Any], field: str) -> str:
    declared = value.get(field)
    if not isinstance(declared, str) or _SHA256.fullmatch(declared) is None:
        raise SemanticBenchmarkError(f"{field}_shape")
    payload = dict(value)
    payload.pop(field)
    if declared != canonical_sha256(payload):
        raise SemanticBenchmarkError(f"{field}_mismatch")
    return declared


def _ordered_unique(values: Any, *, code: str) -> list[str]:
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise SemanticBenchmarkError(code)
    if values != sorted(set(values)):
        raise SemanticBenchmarkError(code)
    return values


def _validate_question_semantics(questions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = questions.get("questions")
    if not isinstance(records, list) or len(records) != len(QUESTION_IDS):
        raise SemanticBenchmarkError("question_count")
    identifiers = [record.get("question_id") for record in records if isinstance(record, dict)]
    if tuple(identifiers) != QUESTION_IDS:
        raise SemanticBenchmarkError("question_order")
    by_id: dict[str, dict[str, Any]] = {}
    formats: set[str] = set()
    strata: set[str] = set()
    languages: set[str] = set()
    for raw in records:
        if not isinstance(raw, dict):
            raise SemanticBenchmarkError("question_shape")
        question_id = str(raw["question_id"])
        required_sources = _ordered_unique(raw["required_sources"], code="source_order")
        acceptable_sources = _ordered_unique(raw["acceptable_sources"], code="source_order")
        required_formats = _ordered_unique(raw["required_formats"], code="format_order")
        if not set(required_sources).issubset(acceptable_sources):
            raise SemanticBenchmarkError("source_coverage")
        atoms = raw["support_atoms"]
        fitness = raw["source_fitness"]
        if not isinstance(atoms, list) or not isinstance(fitness, list):
            raise SemanticBenchmarkError("question_shape")
        atom_ids = [item.get("atom_id") for item in atoms if isinstance(item, dict)]
        fitness_keys = [item.get("source_key") for item in fitness if isinstance(item, dict)]
        if atom_ids != sorted(set(atom_ids)) or fitness_keys != sorted(set(fitness_keys)):
            raise SemanticBenchmarkError("question_record_order")
        answerable = raw["answerable"]
        if answerable is True:
            if not atoms or not required_sources or fitness_keys != acceptable_sources:
                raise SemanticBenchmarkError("answerable_contract")
            if {str(item["source_key"]) for item in atoms} != set(required_sources):
                raise SemanticBenchmarkError("atom_source_coverage")
        elif answerable is False:
            if atoms or required_sources or acceptable_sources or fitness:
                raise SemanticBenchmarkError("unsupported_contract")
        else:
            raise SemanticBenchmarkError("answerable_contract")
        by_id[question_id] = raw
        formats.update(required_formats)
        strata.add(str(raw["stratum"]))
        languages.add(str(raw["language"]))
    if formats != set(FORMATS) or strata != set(STRATA) or languages != {"de", "en"}:
        raise SemanticBenchmarkError("closed_question_coverage")
    return by_id


def load_inputs(root: Path) -> SemanticInputs:
    """Load and validate frozen schema, questions, coverage and protocol identity."""
    benchmark = root / "benchmarks/semantic-e2e/v0.1.0"
    questions = load_json(benchmark / "questions.json")
    schema = load_json(benchmark / "questions.schema.json")
    protocol = load_json(benchmark / "protocol.json")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(questions),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        raise SemanticBenchmarkError("question_schema")
    _identity(questions, "question_set_id")
    _identity(protocol, "protocol_id")
    if (
        questions.get("benchmark_version") != BENCHMARK_VERSION
        or protocol.get("benchmark_version") != BENCHMARK_VERSION
        or questions.get("corpus_id") != CORPUS_ID
        or protocol.get("corpus_id") != CORPUS_ID
        or protocol.get("question_count") != len(QUESTION_IDS)
        or tuple(protocol.get("product_treatments", ())) != PRODUCT_TREATMENTS
        or tuple(protocol.get("product_formats", ())) != ("docx", "md", "pdf", "pptx", "txt")
        or protocol.get("unsupported_product_formats") != ["csv"]
    ):
        raise SemanticBenchmarkError("protocol_contract")
    by_id = _validate_question_semantics(questions)
    return SemanticInputs(protocol=protocol, questions=questions, by_id=by_id)


def selected_observation(
    *,
    order: int,
    evidence_id: str,
    source_key: str,
    representation: str,
    anchor_type: str,
    body: str,
    question: dict[str, Any],
    citation_valid: bool,
) -> dict[str, Any]:
    """Evaluate one reverified selected body and discard the body immediately."""
    covered = sorted(
        str(atom["atom_id"])
        for atom in question["support_atoms"]
        if atom["source_key"] == source_key and atom_matches(body, atom["variants"])
    )
    fitness_by_source = {item["source_key"]: item for item in question["source_fitness"]}
    fitness = fitness_by_source.get(source_key)
    relevant = bool(covered) and source_key in question["acceptable_sources"]
    score = 0
    maximum = 0
    if relevant and fitness is not None:
        score = sum(
            int(fitness[field])
            for field in (
                "publisher_authority",
                "directness",
                "temporal_fit",
                "integrity",
                "reuse_basis",
            )
        )
        maximum = 10
    return {
        "order": order,
        "evidence_id": evidence_id,
        "source_key": source_key,
        "representation": representation,
        "anchor_type": anchor_type,
        "covered_atom_ids": covered,
        "relevant": relevant,
        "citation_valid": citation_valid,
        "source_fitness_score": score,
        "source_fitness_max": maximum,
    }


def make_observation(
    question: dict[str, Any],
    treatment: str,
    selected: list[dict[str, Any]],
    *,
    outcome: str = "pass",
    failure_category: str | None = None,
    wall_ns: int = 0,
    cpu_ns: int = 0,
) -> dict[str, Any]:
    """Create one exact body-free row with a timing-independent semantic identity."""
    covered_atoms = sorted(
        set().union(*(set(item["covered_atom_ids"]) for item in selected)) if selected else set()
    )
    covered_sources = sorted(
        {
            item["source_key"]
            for item in selected
            if item["relevant"] and item["source_key"] in question["required_sources"]
        }
    )
    answerable = bool(question["answerable"])
    full_support = (
        outcome == "pass"
        and answerable
        and len(covered_atoms) == len(question["support_atoms"])
        and len(covered_sources) == len(question["required_sources"])
    )
    semantic = {
        "question_id": question["question_id"],
        "treatment": treatment,
        "outcome": outcome,
        "failure_category": failure_category,
        "selected": selected,
        "required_atom_count": len(question["support_atoms"]),
        "covered_atom_ids": covered_atoms,
        "required_source_count": len(question["required_sources"]),
        "covered_source_keys": covered_sources,
        "full_support": full_support,
        "abstained": not selected,
        "citation_integrity_complete": bool(selected)
        and all(bool(item["citation_valid"]) for item in selected),
        "relevant_count": sum(bool(item["relevant"]) for item in selected),
        "selected_count": len(selected),
        "first_relevant_rank": next(
            (index + 1 for index, item in enumerate(selected) if item["relevant"]), None
        ),
        "source_fitness_score": sum(int(item["source_fitness_score"]) for item in selected),
        "source_fitness_max": sum(int(item["source_fitness_max"]) for item in selected),
    }
    semantic["observation_id"] = canonical_sha256(semantic)
    return {**semantic, "wall_ns": wall_ns, "cpu_ns": cpu_ns}


def semantic_projection(row: dict[str, Any]) -> bytes:
    """Return canonical timing-free row bytes for fresh-run determinism checks."""
    return canonical_json_bytes(
        {key: value for key, value in row.items() if key not in {"wall_ns", "cpu_ns"}}
    )


def file_digest(path: Path) -> tuple[str, int]:
    """Return exact SHA-256 identity and byte length for one result file."""
    payload = path.read_bytes()
    return "sha256:" + hashlib.sha256(payload).hexdigest(), len(payload)


__all__ = [
    "BENCHMARK_VERSION",
    "CORPUS_ID",
    "FORMATS",
    "PRODUCT_TREATMENTS",
    "QUESTION_IDS",
    "RESULT_NAMES",
    "STRATA",
    "SemanticBenchmarkError",
    "SemanticInputs",
    "atom_matches",
    "file_digest",
    "load_inputs",
    "make_observation",
    "normalize_atom",
    "selected_observation",
    "semantic_projection",
]
