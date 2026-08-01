"""Capture once and drift-check the truthful F015 candidate evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import JsonValue

from openardp.adapters.release_benchmarks import (
    NativeRetrievalTreatment,
    NativeReuseTreatment,
    OpenArdpCompilerTreatment,
    OpenArdpRetrievalTreatment,
    RawReparseTreatment,
)
from openardp.adapters.release_evidence import inventory_source_tree
from openardp.adapters.release_reproduction import inspect_artifact
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.release import (
    EvidenceCheck,
    PlatformEvidence,
    ReleaseEvidenceBundle,
    ReleaseGatePolicy,
    SuiteName,
)
from openardp.services.release_benchmarks import (
    build_platform_evidence,
    load_benchmark_cases,
    run_benchmarks,
)
from openardp.services.release_gate import build_claim_map, evaluate_release, render_release_report

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks" / "release" / "v0.1.0"
DESTINATION = ROOT / "release" / "evidence" / "v0.1.0"
_DECISION_AT = datetime(2026, 8, 1, tzinfo=UTC)


def build_files(
    evidence: PlatformEvidence,
    artifacts: dict[str, object],
) -> dict[Path, bytes]:
    """Project one immutable raw capture into every deterministic release file."""
    policy = ReleaseGatePolicy.model_validate_json((CORPUS / "gate-policy.json").read_bytes())
    evidence.verify_identity()
    decision = evaluate_release(policy=policy, evidence=(evidence,), decision_at=_DECISION_AT)
    bundle = ReleaseEvidenceBundle(
        policy=policy,
        platform_evidence=(evidence,),
        decision=decision,
    )
    files = {
        DESTINATION / "release-evidence.json": _canonical(bundle.model_dump(mode="json")),
        DESTINATION / "platform-evidence.json": _canonical(evidence.model_dump(mode="json")),
        DESTINATION / "decision.json": _canonical(decision.model_dump(mode="json")),
        DESTINATION / "claim-map.json": _canonical(build_claim_map(decision)),
        DESTINATION / "report.md": render_release_report(decision),
        DESTINATION / "artifacts.json": _pretty(artifacts),
    }
    sbom = DESTINATION / "sbom.cdx.json"
    if not sbom.is_file():
        raise RuntimeError("normalized release SBOM must be generated first")
    files[sbom] = sbom.read_bytes()
    checksums = {
        "schema_version": "0.1.0",
        "files": [
            {
                "path": path.name,
                "byte_length": len(data),
                "sha256": _digest(data),
            }
            for path, data in sorted(files.items(), key=lambda item: item[0].name)
        ],
    }
    files[DESTINATION / "checksums.json"] = _pretty(checksums)
    manifest = {
        "schema_version": "0.1.0",
        "decision_id": decision.decision_id,
        "source_tree_id": decision.source_tree_id,
        "files": [
            {
                "path": path.name,
                "byte_length": len(data),
                "sha256": _digest(data),
            }
            for path, data in sorted(files.items(), key=lambda item: item[0].name)
        ],
    }
    files[DESTINATION / "manifest.json"] = _pretty(manifest)
    return files


def capture_platform(suite_results_path: Path) -> PlatformEvidence:
    """Run the real benchmark treatments and bind reviewed suite evidence once."""
    cases = load_benchmark_cases(ROOT, CORPUS)
    observations = run_benchmarks(
        cases,
        (
            RawReparseTreatment(),
            NativeReuseTreatment(),
            NativeRetrievalTreatment(),
            OpenArdpRetrievalTreatment(),
            OpenArdpCompilerTreatment(),
        ),
        repetitions=7,
        warmups=1,
    )
    return build_platform_evidence(
        repository_root=ROOT,
        corpus=CORPUS,
        observations=observations,
        suite_results=_load_suite_results(suite_results_path),
        reference_timing=True,
    )


def capture_artifacts(directory: Path) -> dict[str, object]:
    """Inspect the exact candidate wheel and sdist without retaining member bodies."""
    selected = tuple(
        path
        for path in sorted(directory.iterdir())
        if path.name.startswith("openardp-0.1.0rc1")
        and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
    )
    inventories = tuple(inspect_artifact(path) for path in selected)
    if {item.artifact_type for item in inventories} != {"wheel", "sdist"}:
        raise RuntimeError("candidate artifact set is incomplete")
    return {
        "schema_version": "0.1.0",
        "candidate_version": "0.1.0rc1",
        "previous_version": "0.0.1",
        "status": "passed",
        "artifacts": [
            {
                "artifact_type": item.artifact_type,
                "byte_length": item.byte_length,
                "filename": item.filename,
                "member_count": item.member_count,
                "member_inventory_id": item.member_inventory_id,
                "sha256": item.sha256,
                "status": item.status,
            }
            for item in inventories
        ],
    }


def _load_suite_results(path: Path) -> dict[SuiteName, tuple[EvidenceCheck, ...]]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict) or set(value) != {"schema_version", "suites"}:
        raise RuntimeError("suite evidence root is malformed")
    suites = value.get("suites")
    if value.get("schema_version") != "0.1.0" or not isinstance(suites, dict):
        raise RuntimeError("suite evidence root is malformed")
    return {
        SuiteName(name): tuple(
            EvidenceCheck.model_validate_json(canonical_json_bytes(cast(JsonValue, item)))
            for item in checks
        )
        for name, checks in suites.items()
        if isinstance(checks, list)
    }


def _current_source_tree_id() -> str:
    policy = json.loads((CORPUS / "source-tree-policy.json").read_bytes())
    paths = policy.get("allowed_paths")
    if not isinstance(paths, list) or any(not isinstance(item, str) for item in paths):
        raise RuntimeError("source tree policy is malformed")
    return inventory_source_tree(ROOT, tuple(paths)).source_tree_id


def _canonical(value: JsonValue) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def _pretty(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    """Capture new raw evidence explicitly or verify committed projections read-only."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--suite-results", type=Path)
    parser.add_argument("--artifacts", type=Path, default=Path("dist"))
    arguments = parser.parse_args()
    if arguments.write:
        if arguments.suite_results is None:
            parser.error("--write requires --suite-results")
        evidence = capture_platform(arguments.suite_results)
        artifacts = capture_artifacts(arguments.artifacts)
    else:
        evidence = PlatformEvidence.model_validate_json(
            (DESTINATION / "platform-evidence.json").read_bytes()
        )
        artifacts = json.loads((DESTINATION / "artifacts.json").read_bytes())
        if not isinstance(artifacts, dict):
            raise RuntimeError("committed artifact evidence is malformed")
        if evidence.source_tree_id != _current_source_tree_id():
            print("release evidence drift: source tree identity changed")
            return 1
    expected = build_files(evidence, artifacts)
    if arguments.write:
        for path, data in expected.items():
            _write_atomic(path, data)
        print(
            f"wrote {len(expected)} release evidence files from "
            f"{len(evidence.observations)} raw observations"
        )
        return 0
    drift = [
        path.name
        for path, data in expected.items()
        if not path.is_file() or path.read_bytes() != data
    ]
    if drift:
        print("release evidence drift: " + ", ".join(sorted(drift)))
        return 1
    print(f"all {len(expected)} release evidence files are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
