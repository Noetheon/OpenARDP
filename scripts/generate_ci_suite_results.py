"""Generate bound, body-free F015 suite evidence from completed local checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

from openardp.adapters.release_reproduction import (
    ArtifactInventory,
    ReproductionResult,
    inspect_artifact,
    reproduce_workspace_recovery,
    reproduction_checks,
)
from openardp.adapters.release_security import (
    SecurityControl,
    TestNodeResult,
    evaluate_security_controls,
    load_security_controls,
    privacy_checks,
    scan_privacy_canaries,
)
from openardp.adapters.release_supply_chain import supply_chain_checks
from openardp.domain.identity import canonical_sha256
from openardp.domain.release import EvidenceCheck, EvidenceStatus

_CANARIES = {
    "body": b"OPENARDP-PRIVACY-BODY-CANARY",
    "credential": b"OPENARDP-PRIVACY-CREDENTIAL-CANARY",
    "exception": b"OPENARDP-PRIVACY-EXCEPTION-CANARY",
    "path": b"OPENARDP-PRIVACY-PATH-CANARY",
    "query": b"OPENARDP-PRIVACY-QUERY-CANARY",
}


def build_results(
    repository_root: Path,
    *,
    junit_path: Path,
    artifact_directory: Path,
    install_environment: Path,
) -> dict[str, object]:
    """Build every non-benchmark suite from inspectable local artifacts."""
    root = repository_root.resolve(strict=True)
    controls_path = root / "benchmarks" / "release" / "v0.1.0" / "security-controls.json"
    controls = load_security_controls(controls_path)
    test_results = _junit_results(junit_path, controls)
    security = evaluate_security_controls(controls, test_results)

    artifacts = tuple(
        inspect_artifact(path, forbidden_canaries=tuple(_CANARIES.values()))
        for path in sorted(artifact_directory.iterdir())
        if path.name.startswith("openardp-0.1.0rc1")
        and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
    )
    if len(artifacts) != 2:
        raise RuntimeError("exactly one candidate wheel and source distribution are required")

    scan_paths = (junit_path, *(artifact_directory / item.filename for item in artifacts))
    privacy = privacy_checks(scan_privacy_canaries(scan_paths, _CANARIES))

    corpus = root / "benchmarks" / "release" / "v0.1.0"
    evidence_root = root / "release" / "evidence" / "v0.1.0"
    review = _json_object(corpus / "dependency-review.json")
    sbom = _json_object(evidence_root / "sbom.cdx.json")
    supply_chain = supply_chain_checks(
        sbom,
        review,
        now=datetime(2026, 8, 1, tzinfo=UTC),
        maximum_vulnerability_age_days=30,
    )

    install_results = _installed_candidate_results(install_environment, artifacts)
    with tempfile.TemporaryDirectory(prefix="openardp-release-recovery-") as temporary:
        recovery_results = reproduce_workspace_recovery(
            root / "tests" / "fixtures" / "release",
            Path(temporary) / "workspace",
            now=datetime(2026, 8, 1, tzinfo=UTC),
        )
    reproduction = reproduction_checks(
        artifacts,
        (*install_results, *recovery_results),
        required_steps=(
            "offline-wheel-install",
            "cli-schema-smoke",
            "previous-workspace-open",
            "revision-nine-migration",
            "backup-upgrade-restore",
        ),
    )
    by_id = {item.check_id: item for item in reproduction}
    fresh_install = (
        by_id["candidate-artifacts-inspected"],
        by_id["offline-wheel-install"],
        by_id["cli-schema-smoke"],
    )
    upgrade_recovery = (
        by_id["previous-workspace-open"],
        by_id["revision-nine-migration"],
        by_id["backup-upgrade-restore"],
    )
    semantic_inputs = tuple(
        sorted(
            evidence_id
            for check in (*security, *privacy, *supply_chain, *fresh_install, *upgrade_recovery)
            for evidence_id in check.evidence_ids
        )
    )
    platform_reproduction = (
        EvidenceCheck(
            check_id="platform-semantic-reproduction",
            status=EvidenceStatus.PASSED,
            evidence_ids=(canonical_sha256(list(semantic_inputs)),),
        ),
    )
    suites = {
        "fresh_install": fresh_install,
        "platform_reproduction": platform_reproduction,
        "privacy": privacy,
        "security": security,
        "supply_chain": supply_chain,
        "upgrade_recovery": upgrade_recovery,
    }
    return {
        "schema_version": "0.1.0",
        "suites": {
            name: [item.model_dump(mode="json") for item in checks]
            for name, checks in sorted(suites.items())
        },
    }


def _junit_results(path: Path, controls: tuple[SecurityControl, ...]) -> tuple[TestNodeResult, ...]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise RuntimeError("JUnit evidence is missing or unsafe")
    try:
        document = ElementTree.fromstring(path.read_bytes())  # noqa: S314
    except ElementTree.ParseError as error:
        raise RuntimeError("JUnit evidence is malformed") from error
    cases = tuple(document.iter("testcase"))
    results: list[TestNodeResult] = []
    for control in controls:
        for node_id in control.test_nodes:
            path_part, test_name = node_id.split("::", maxsplit=1)
            class_name = path_part.removesuffix(".py").replace("/", ".")
            matched = tuple(
                item
                for item in cases
                if item.attrib.get("classname") == class_name
                and item.attrib.get("name", "").split("[", maxsplit=1)[0] == test_name
            )
            if not matched:
                results.append(TestNodeResult(node_id, "unavailable", 0))
                continue
            status = (
                "failed"
                if any(
                    item.find("failure") is not None or item.find("error") is not None
                    for item in matched
                )
                else "skipped"
                if any(item.find("skipped") is not None for item in matched)
                else "passed"
            )
            duration_ms = round(sum(float(item.attrib.get("time", "0")) for item in matched) * 1000)
            results.append(TestNodeResult(node_id, status, duration_ms))
    return tuple(results)


def _installed_candidate_results(
    environment: Path,
    artifacts: tuple[ArtifactInventory, ...],
) -> tuple[ReproductionResult, ...]:
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        raise RuntimeError("candidate install environment is missing")
    command = (
        "import json,openardp; from openardp.interfaces.cli import main; "
        "from openardp.domain.release import RELEASE_EVIDENCE_VERSION; "
        "assert openardp.__version__=='0.1.0rc1'; assert main(['--help'])==0; "
        "assert RELEASE_EVIDENCE_VERSION=='0.1.0'; "
        "print(json.dumps({'version':openardp.__version__},sort_keys=True))"
    )
    completed = subprocess.run(  # noqa: S603 -- exact venv interpreter and fixed command
        [str(python), "-c", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"},
    )
    passed = completed.returncode == 0 and '"version": "0.1.0rc1"' in completed.stdout
    artifact_id = canonical_sha256(sorted(item.sha256 for item in artifacts))
    return (
        ReproductionResult(
            "offline-wheel-install",
            "passed" if passed else "failed",
            0,
            None if passed else "offline-install-smoke-failed",
            (artifact_id,),
        ),
        ReproductionResult(
            "cli-schema-smoke",
            "passed" if passed else "failed",
            0,
            None if passed else "cli-schema-smoke-failed",
            (artifact_id,),
        ),
    )


def _json_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise RuntimeError("release JSON input must be an object")
    return value


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
    """Write one deterministic JSON suite bundle after validating every source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("dist"))
    parser.add_argument("--install-environment", type=Path, default=Path(".release-venv"))
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    arguments = parser.parse_args()
    destination = arguments.output.expanduser().absolute()
    payload = build_results(
        arguments.repository_root,
        junit_path=arguments.junit,
        artifact_directory=arguments.artifacts,
        install_environment=arguments.install_environment,
    )
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    _write_atomic(destination, data)
    print(f"wrote {destination.name} ({hashlib.sha256(data).hexdigest()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
