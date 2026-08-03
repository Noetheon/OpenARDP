"""Security and privacy boundaries for the optional semantic runtime."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


def test_independent_validator_uses_only_standard_library(repository_root: Path) -> None:
    """Keep validation independent from OpenARDP, providers and optional model packages."""
    path = repository_root / "scripts/validate_provider_retrieval_benchmark.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {
        "__future__",
        "argparse",
        "decimal",
        "fractions",
        "hashlib",
        "json",
        "pathlib",
        "sys",
        "typing",
    }
    completed = subprocess.run(  # noqa: S603 - fixed interpreter/script and local paths
        [
            sys.executable,
            "-I",
            "-S",
            str(path),
            "--protocol-version",
            "0.3.0",
            "--repository-root",
            str(repository_root),
            "--result",
            str(
                repository_root
                / "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64"
            ),
        ],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == "provider_retrieval_result_valid decision=PROVIDER_RETRIEVAL_READY\n"
    assert completed.stderr == ""


def test_reference_results_exclude_bodies_queries_vectors_and_local_paths(
    repository_root: Path,
) -> None:
    """Retain evaluation facts without document content or machine-local identifiers."""
    result = repository_root / "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64"
    forbidden_keys = {
        "body",
        "content",
        "document_text",
        "embedding",
        "hostname",
        "path",
        "query",
        "username",
        "vector",
    }
    for path in result.glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                assert forbidden_keys.isdisjoint(str(key).casefold() for key in item)
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, str):
                assert not item.startswith("/Users/")
