"""F036 atomic publication and independent-validation tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _validate(root: Path, result: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [
            sys.executable,
            "-I",
            "-S",
            "scripts/validate_downstream_utility_benchmark.py",
            str(result),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def test_reference_inputs_publish_and_validate_offline(tmp_path: Path) -> None:
    """Derive the complete result without model execution and validate in isolated Python."""
    root = Path.cwd()
    output = tmp_path / "result"
    producer = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, "scripts/run_downstream_utility_benchmark.py", "--output", str(output)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert producer.returncode == 0, producer.stderr
    validation = _validate(root, output)
    assert validation.returncode == 0, validation.stderr
    assert validation.stdout.startswith("downstream_utility_valid ")


def test_independent_validator_rejects_tampered_summary(tmp_path: Path) -> None:
    """A self-consistent-looking aggregate cannot replace reconstruction from raw inputs."""
    root = Path.cwd()
    source = root / "benchmarks/downstream-utility/v0.1.0/results/reference-macos-arm64"
    result = tmp_path / "result"
    shutil.copytree(source, result)
    summary_path = result / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["development"]["primary_budget"] = 5
    summary_path.write_text(json.dumps(summary, separators=(",", ":"), sort_keys=True) + "\n")

    validation = _validate(root, result)

    assert validation.returncode == 2
    assert validation.stderr == "downstream_utility_validation_failed\n"


def test_independent_validator_rejects_duplicate_json_members(tmp_path: Path) -> None:
    """Duplicate object members cannot select an attacker-controlled interpretation."""
    root = Path.cwd()
    source = root / "benchmarks/downstream-utility/v0.1.0/results/reference-macos-arm64"
    result = tmp_path / "result"
    shutil.copytree(source, result)
    path = result / "observations.json"
    payload = path.read_text(encoding="utf-8")
    path.write_text(payload.replace("{", '{"protocol_id":"duplicate",', 1), encoding="utf-8")

    validation = _validate(root, result)

    assert validation.returncode == 2
    assert validation.stderr == "downstream_utility_validation_failed\n"


def test_producer_refuses_to_overwrite_existing_output_without_path_disclosure(
    tmp_path: Path,
) -> None:
    """Atomic publication never replaces an existing evidence directory."""
    root = Path.cwd()
    output = tmp_path / "existing"
    output.mkdir()
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, "scripts/run_downstream_utility_benchmark.py", "--output", str(output)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert completed.stderr == "downstream_utility_execution_failed\n"
    assert str(tmp_path) not in completed.stderr


def test_validator_is_a_separate_stdlib_only_implementation() -> None:
    """Prevent accidental replacement of independent reconstruction with producer imports."""
    source = Path("scripts/validate_downstream_utility_benchmark.py").read_text(encoding="utf-8")

    assert "from scripts.downstream_utility_benchmark" not in source
    assert "from downstream_utility_benchmark" not in source
