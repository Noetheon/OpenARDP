"""Filesystem, identity and privacy boundaries for release evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.adapters.release_evidence import (
    LocalReleaseEvidenceStore,
    inventory_source_tree,
)
from openardp.adapters.release_security import (
    SecurityEvidenceMalformed,
    TestNodeResult,
    evaluate_security_controls,
    load_security_controls,
)
from openardp.domain.release import (
    Baseline,
    EnvironmentProfile,
    PlatformEvidence,
    platform_evidence_id,
)
from openardp.ports.release import (
    ReleaseEvidenceConflict,
    ReleaseEvidenceIntegrityError,
)

SHA = "sha256:" + "3" * 64


def _evidence() -> PlatformEvidence:
    provisional = PlatformEvidence(
        evidence_id=SHA,
        source_tree_id=SHA,
        protocol_id=SHA,
        corpus_id=SHA,
        configuration_id=SHA,
        lockfile_id=SHA,
        environment=EnvironmentProfile(
            platform_id="linux-x86_64",
            os_family="linux",
            architecture="x86_64",
            python_version="3.12.11",
            logical_cpu_bucket="5-8",
            memory_gib_bucket="8-15",
            timer_resolution_ns=1,
        ),
        baselines=tuple(Baseline),
        observations=(),
        suites=(),
    )
    return provisional.model_copy(
        update={"evidence_id": platform_evidence_id(provisional.identity_projection)}
    )


def test_evidence_publication_converges_only_for_exact_verified_bytes(tmp_path: Path) -> None:
    """An exact retry converges while tampering is never overwritten."""
    store = LocalReleaseEvidenceStore()
    destination = tmp_path / "evidence"
    evidence = _evidence()
    store.publish(destination, evidence)
    store.publish(destination, evidence)
    assert store.load(destination) == evidence

    (destination / "evidence.json").write_bytes(b"{}\n")
    with pytest.raises(ReleaseEvidenceIntegrityError, match="manifest"):
        store.load(destination)
    with pytest.raises(ReleaseEvidenceConflict, match="conflicts"):
        store.publish(destination, evidence)


def test_evidence_loader_rejects_extra_files_and_links(tmp_path: Path) -> None:
    """A directory is authoritative only with its exact regular-file inventory."""
    store = LocalReleaseEvidenceStore()
    destination = tmp_path / "evidence"
    store.publish(destination, _evidence())
    (destination / "extra.txt").write_text("not evidence", encoding="utf-8")
    with pytest.raises(ReleaseEvidenceIntegrityError, match="inventory"):
        store.load(destination)

    link = tmp_path / "evidence-link"
    link.symlink_to(destination, target_is_directory=True)
    with pytest.raises(ReleaseEvidenceIntegrityError, match="unsafe"):
        store.load(link)


def test_source_tree_identity_is_path_relative_and_detects_drift(tmp_path: Path) -> None:
    """The source identity includes allowlisted bytes but never its absolute root."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        (root / "src").mkdir(parents=True)
        (root / "src" / "module.py").write_bytes(b"value = 1\n")
        (root / "uv.lock").write_bytes(b"version = 1\n")
        (root / "ignored.secret").write_bytes(b"credential-sentinel\n")
    first_inventory = inventory_source_tree(first, ("src", "uv.lock"))
    second_inventory = inventory_source_tree(second, ("src", "uv.lock"))
    assert first_inventory == second_inventory
    assert str(first) not in first_inventory.model_dump_json()
    assert "credential-sentinel" not in first_inventory.model_dump_json()

    (second / "src" / "module.py").write_bytes(b"value = 2\n")
    assert inventory_source_tree(second, ("src", "uv.lock")) != first_inventory


def test_source_tree_ignores_declared_cache_and_build_output(tmp_path: Path) -> None:
    """Keep derived local caches outside the canonical source identity."""
    root = tmp_path / "root"
    (root / "src" / "__pycache__").mkdir(parents=True)
    (root / "src" / "module.py").write_text("value = 1\n", encoding="utf-8")
    (root / "src" / "__pycache__" / "module.pyc").write_bytes(b"derived")
    before = inventory_source_tree(root, ("src",))
    (root / "src" / "__pycache__" / "module.pyc").write_bytes(b"changed")
    assert inventory_source_tree(root, ("src",)) == before


def test_source_tree_rejects_traversal_and_symlinks(tmp_path: Path) -> None:
    """The inventory allowlist cannot expand authority outside the declared root."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file.txt").write_text("safe", encoding="utf-8")
    with pytest.raises(ReleaseEvidenceIntegrityError, match="portable"):
        inventory_source_tree(root, ("../file.txt",))
    (root / "link.txt").symlink_to(root / "file.txt")
    with pytest.raises(ReleaseEvidenceIntegrityError, match="unsafe"):
        inventory_source_tree(root, ("link.txt",))


def test_security_manifest_requires_every_exact_passing_node() -> None:
    """Make missing, renamed, skipped and unallowlisted test evidence fail closed."""
    manifest = (
        Path(__file__).resolve().parents[2]
        / "benchmarks"
        / "release"
        / "v0.1.0"
        / "security-controls.json"
    )
    controls = load_security_controls(manifest)
    results = tuple(
        TestNodeResult(node_id=node, status="passed", duration_ms=1)
        for control in controls
        for node in control.test_nodes
    )
    assert all(
        check.status.value == "passed" for check in evaluate_security_controls(controls, results)
    )
    skipped = (TestNodeResult(results[0].node_id, "skipped", 0), *results[1:])
    assert evaluate_security_controls(controls, skipped)[0].status.value == "failed"
    with pytest.raises(SecurityEvidenceMalformed, match="not allowlisted"):
        evaluate_security_controls(
            controls,
            (*results, TestNodeResult("tests/security/renamed.py::test_old", "passed", 1)),
        )


def test_security_manifest_rejects_duplicate_nodes_and_unknown_status(tmp_path: Path) -> None:
    """Reject ambiguous control ownership and result vocabularies."""
    manifest = tmp_path / "controls.json"
    control = {
        "control_id": "sec-one",
        "invariant": "exact-invariant",
        "test_nodes": ["tests/test_one.py::test_one"],
        "threat": "exact-threat",
    }
    manifest.write_text(
        json.dumps({"manifest_version": "0.1.0", "controls": [control, control]}),
        encoding="utf-8",
    )
    with pytest.raises(SecurityEvidenceMalformed, match="duplicate"):
        load_security_controls(manifest)

    manifest.write_text(
        json.dumps({"manifest_version": "0.1.0", "controls": [control]}),
        encoding="utf-8",
    )
    controls = load_security_controls(manifest)
    with pytest.raises(SecurityEvidenceMalformed, match="status"):
        evaluate_security_controls(
            controls,
            (TestNodeResult("tests/test_one.py::test_one", "warning", 1),),
        )


def test_security_manifest_rejects_non_strict_and_invalid_content(tmp_path: Path) -> None:
    """Keep malformed JSON and unsafe identifiers outside release authority."""
    manifest = tmp_path / "controls.json"
    manifest.write_text(
        '{"manifest_version":"0.1.0","manifest_version":"0.1.0","controls":[]}',
        encoding="utf-8",
    )
    with pytest.raises(SecurityEvidenceMalformed, match="duplicate JSON key"):
        load_security_controls(manifest)

    invalid_control = {
        "control_id": "SEC INVALID",
        "invariant": "exact-invariant",
        "test_nodes": ["tests/test_one.py::test_one"],
        "threat": "exact-threat",
    }
    manifest.write_text(
        json.dumps({"manifest_version": "0.1.0", "controls": [invalid_control]}),
        encoding="utf-8",
    )
    with pytest.raises(SecurityEvidenceMalformed, match="identifier"):
        load_security_controls(manifest)


def test_security_results_reject_duplicate_or_negative_duration(tmp_path: Path) -> None:
    """Do not accept ambiguous or nonsensical timing evidence."""
    manifest = tmp_path / "controls.json"
    node = "tests/test_one.py::test_one"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "0.1.0",
                "controls": [
                    {
                        "control_id": "sec-one",
                        "invariant": "exact-invariant",
                        "test_nodes": [node],
                        "threat": "exact-threat",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    controls = load_security_controls(manifest)
    with pytest.raises(SecurityEvidenceMalformed, match="duplicate or malformed"):
        evaluate_security_controls(controls, (TestNodeResult(node, "passed", -1),))
    with pytest.raises(SecurityEvidenceMalformed, match="duplicate or malformed"):
        evaluate_security_controls(
            controls,
            (TestNodeResult(node, "passed", 1), TestNodeResult(node, "passed", 1)),
        )
