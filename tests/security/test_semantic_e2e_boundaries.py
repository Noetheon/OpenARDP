"""Privacy, independence and product-claim boundaries for F025."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
RESULT = ROOT / "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64"


def test_independent_validator_imports_only_standard_library() -> None:
    """Keep validation independent from producer, evaluator and project modules."""
    tree = ast.parse(
        (ROOT / "scripts/validate_semantic_e2e_benchmark.py").read_text(encoding="utf-8")
    )
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports <= {
        "__future__",
        "argparse",
        "decimal",
        "fractions",
        "hashlib",
        "json",
        "pathlib",
        "re",
        "sys",
        "typing",
    }


def test_reference_result_is_body_free_and_path_free() -> None:
    """Do not retain questions, evidence bodies, host paths or user identifiers."""
    forbidden = {
        "body",
        "content",
        "hostname",
        "path",
        "query",
        "question",
        "reference_answer",
        "username",
    }
    corpus_phrase = "Humans must remain in charge"
    for path in RESULT.iterdir():
        text = path.read_text(encoding="utf-8")
        assert "/Users/" not in text
        assert "\\Users\\" not in text
        assert corpus_phrase not in text
        if path.suffix == ".json":
            value = json.loads(text)
            stack = [value]
            while stack:
                current = stack.pop()
                if isinstance(current, dict):
                    assert not (set(current) & forbidden)
                    stack.extend(current.values())
                elif isinstance(current, list):
                    stack.extend(current)


def test_frozen_questions_separate_operator_help_from_direct_queries() -> None:
    """Ensure the manually curated query never silently replaces product input."""
    fixture = json.loads(
        (ROOT / "benchmarks/semantic-e2e/v0.1.0/questions.json").read_text(encoding="utf-8")
    )
    assert all(item["question"] != item["operator_query"] for item in fixture["questions"])
    assert any(item["language"] == "de" for item in fixture["questions"])
