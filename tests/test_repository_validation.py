"""Tests for deterministic, offline repository documentation validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_repository import (
    Diagnostic,
    validate_governance,
    validate_markdown,
    validate_repository,
)


def _write(path: Path, content: str, *, newline: str | None = None) -> Path:
    """Write a UTF-8 synthetic fixture and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline=newline)
    return path


def _codes(diagnostics: list[Diagnostic]) -> list[str]:
    """Return diagnostic codes in emitted order."""
    return [diagnostic.code for diagnostic in diagnostics]


def test_valid_markdown_variants_pass_without_network(tmp_path: Path) -> None:
    """Accept portable local evidence and skip genuine external targets offline."""
    _write(tmp_path / "asset.png", "synthetic image bytes")
    _write(tmp_path / "with space.md", "# Encoded Target\n")
    _write(
        tmp_path / "target.md",
        "# Section\n\n# Section\n\n## Unicode Überschrift\n",
        newline="\r\n",
    )
    source = _write(
        tmp_path / "README.md",
        "\n".join(
            (
                "[first](target.md#section)",
                "[duplicate](target.md#section-1)",
                "[unicode](target.md#unicode-überschrift)",
                "[encoded](with%20space.md#encoded-target)",
                "![asset](asset.png)",
                "[reference][target]",
                "[target]: target.md#section",
                "[external](https://example.invalid/not-fetched)",
                "[mail](mailto:security@example.invalid)",
            )
        ),
    )
    assert validate_markdown(tmp_path, [source]) == []


def test_link_examples_in_inline_and_fenced_code_are_ignored(tmp_path: Path) -> None:
    """Ignore instructional examples that are not live Markdown links."""
    source = _write(
        tmp_path / "README.md",
        "`[inline](/not-real)`\n\n```markdown\n[block](missing.md)\n```\n",
    )
    assert validate_markdown(tmp_path, [source]) == []


def test_vendored_realworld_markdown_payload_is_not_rewritten_or_link_checked(
    tmp_path: Path,
) -> None:
    """Exclude exact external corpus payloads while retaining owned-doc checks."""
    _write(
        tmp_path / "corpora/realworld/v0.1.0/sources/vendor.md",
        "[upstream-relative-link](not-in-corpus.md)\n",
    )
    owned = _write(tmp_path / "README.md", "[missing-owned-target](missing.md)\n")

    diagnostics = validate_markdown(tmp_path)

    assert len(diagnostics) == 1
    assert diagnostics[0].path == owned
    assert diagnostics[0].code == "MD006"


@pytest.mark.parametrize(
    ("target", "expected_code"),
    (
        ("", "MD001"),
        ("missing.md", "MD006"),
        ("target.md#absent", "MD008"),
        ("../outside.md", "MD009"),
        ("/absolute.md", "MD004"),
        (r"C:\\temp\\file.md", "MD005"),
        (r"folder\\file.md", "MD005"),
        ("file:///tmp/source.md", "MD003"),
        ("sandbox:/mnt/data/file.md", "MD003"),
    ),
)
def test_unsafe_or_missing_target_is_rejected(
    tmp_path: Path,
    target: str,
    expected_code: str,
) -> None:
    """Reject unsafe, missing and non-portable local targets deterministically."""
    _write(tmp_path / "target.md", "# Present\n")
    source = _write(tmp_path / "README.md", f"[target]({target})\n")
    assert _codes(validate_markdown(tmp_path, [source])) == [expected_code]


def test_case_mismatch_is_rejected_on_case_insensitive_hosts(tmp_path: Path) -> None:
    """Check exact repository spelling independently of host filesystem behavior."""
    _write(tmp_path / "ExactName.md", "# Exact\n")
    source = _write(tmp_path / "README.md", "[wrong](exactname.md)\n")
    assert _codes(validate_markdown(tmp_path, [source])) == ["MD007"]


def test_external_symlink_is_rejected(tmp_path: Path) -> None:
    """Prevent a repository-local link from escaping through a symlink."""
    outside = _write(tmp_path.parent / f"{tmp_path.name}-outside.md", "# Outside\n")
    link = tmp_path / "linked.md"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    source = _write(tmp_path / "README.md", "[escape](linked.md)\n")
    assert _codes(validate_markdown(tmp_path, [source])) == ["MD009"]


def test_missing_reference_definition_is_rejected(tmp_path: Path) -> None:
    """Report unresolved explicit Markdown reference links."""
    source = _write(tmp_path / "README.md", "[evidence][missing]\n")
    assert _codes(validate_markdown(tmp_path, [source])) == ["MD002"]


def test_diagnostics_are_stably_sorted_and_rendered(tmp_path: Path) -> None:
    """Keep validator output reproducible across repeated runs."""
    second = _write(tmp_path / "b.md", "[missing](z.md)\n")
    first = _write(tmp_path / "a.md", "[missing](y.md)\n")
    first_run = validate_markdown(tmp_path, [second, first])
    second_run = validate_markdown(tmp_path, [first, second])
    assert first_run == second_run
    assert [diagnostic.render(tmp_path) for diagnostic in first_run] == [
        "a.md:1: MD006: y.md: local target does not exist",
        "b.md:1: MD006: z.md: local target does not exist",
    ]


def test_governance_reports_missing_required_files(tmp_path: Path) -> None:
    """Produce one stable diagnostic for each missing governance artifact."""
    diagnostics = validate_governance(tmp_path)
    assert "GOV001" in _codes(diagnostics)
    assert any(diagnostic.target == "LICENSE" for diagnostic in diagnostics)


def test_f005a_governance_rejects_drift_and_source_package(tmp_path: Path) -> None:
    """Detect missing overlay files, authority drift and uncurated platform metadata."""
    _write(tmp_path / ".specify/memory/constitution.md", "managed\n")
    _write(tmp_path / "spec-kit/CONSTITUTION_SOURCE.md", "drifted\n")
    _write(tmp_path / "spec-kit/CONSTITUTION_V3_SOURCE.md", "# unlabeled\n")
    _write(tmp_path / "openardp_codex_blueprint_v3_1/.DS_Store", "metadata")

    codes = set(_codes(validate_governance(tmp_path)))
    assert {"GOV007", "GOV008", "GOV009"} <= codes


def test_real_repository_contract_is_clean(repository_root: Path) -> None:
    """Validate all real Markdown and governance contracts offline."""
    assert validate_repository(repository_root) == []
