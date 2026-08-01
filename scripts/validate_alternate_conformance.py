"""Run and drift-check the independent F016 alternate-parser conformance spike."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from openardp.domain.evidence import (
    EvidenceProjection,
    EvidenceReference,
    NativeRepresentation,
    validate_evidence_records,
)
from openardp.domain.identity import canonical_json_bytes, canonical_sha256

ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_ROOT = ROOT / "conformance"
DEFAULT_MANIFEST = CONFORMANCE_ROOT / "alternate-parser" / "v0.1.0" / "manifest.json"
PROFILE_VERSION = "0.1.0"


class AlternateConformanceError(RuntimeError):
    """Stable coordinator failure with no source-body diagnostic."""


def _raw_sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise AlternateConformanceError("manifest_invalid") from error
    if not isinstance(value, dict):
        raise AlternateConformanceError("manifest_invalid")
    return value


def _mapping(value: object, *, category: str = "manifest_invalid") -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise AlternateConformanceError(category)
    return value


def _sequence(value: object, *, category: str = "manifest_invalid") -> Sequence[Any]:
    if not isinstance(value, list):
        raise AlternateConformanceError(category)
    return value


def _text(value: object, *, category: str = "manifest_invalid") -> str:
    if not isinstance(value, str) or not value:
        raise AlternateConformanceError(category)
    return value


def _confined(root: Path, relative: object) -> Path:
    value = _text(relative)
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts or "." in pure.parts:
        raise AlternateConformanceError("path_invalid")
    candidate = root.joinpath(*pure.parts)
    current = root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise AlternateConformanceError("path_invalid")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as error:
        raise AlternateConformanceError("path_invalid") from error
    if not resolved.is_file():
        raise AlternateConformanceError("path_invalid")
    return resolved


def _script_path(manifest: Mapping[str, Any]) -> tuple[Path, str]:
    implementation = _mapping(manifest.get("implementation"))
    path = _confined(ROOT, implementation.get("path"))
    declared = _text(implementation.get("sha256"))
    observed = _raw_sha256(path.read_bytes())
    if declared != observed:
        raise AlternateConformanceError("implementation_digest_mismatch")
    return path, observed


def _subprocess_environment() -> dict[str, str]:
    environment = {
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
    }
    if "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    if "WINDIR" in os.environ:
        environment["WINDIR"] = os.environ["WINDIR"]
    return environment


def _invoke(
    script: Path,
    command: str | None,
    request: Mapping[str, Any] | None,
    *,
    timeout: int,
) -> tuple[dict[str, Any], bytes]:
    with tempfile.TemporaryDirectory(prefix="openardp-f016-") as directory:
        work = Path(directory)
        arguments = [sys.executable, "-I", "-S", str(script)]
        if command is None:
            arguments.append("--self-check")
        else:
            request_path = work / "request.json"
            request_path.write_bytes(canonical_json_bytes(dict(request or {})))
            arguments.extend((command, "--request", str(request_path.resolve())))
        try:
            completed = subprocess.run(  # noqa: S603 - exact interpreter and digest-pinned script
                arguments,
                cwd=work,
                env=_subprocess_environment(),
                capture_output=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise AlternateConformanceError("process_timeout") from error
    if completed.returncode != 0:
        category = completed.stderr.decode("utf-8", errors="replace").strip()
        if not category.startswith("ALTERNATE_CONFORMANCE_ERROR:"):
            category = "process_failed"
        raise AlternateConformanceError(category)
    if completed.stderr:
        raise AlternateConformanceError("unexpected_diagnostic")
    if len(completed.stdout) > 1_048_576 or not completed.stdout.endswith(b"\n"):
        raise AlternateConformanceError("response_invalid")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AlternateConformanceError("response_invalid") from error
    if not isinstance(value, dict):
        raise AlternateConformanceError("response_invalid")
    canonical = canonical_json_bytes(value) + b"\n"
    if completed.stdout != canonical:
        raise AlternateConformanceError("response_noncanonical")
    return value, canonical


def _request_base(manifest: Mapping[str, Any]) -> dict[str, Any]:
    limits = dict(_mapping(manifest.get("limits")))
    return {
        "limits": {
            "max_file_bytes": limits["max_file_bytes"],
            "max_files": limits["max_files"],
            "max_total_bytes": limits["max_total_bytes"],
        },
        "profile_version": PROFILE_VERSION,
        "root": str(CONFORMANCE_ROOT.resolve()),
    }


def _consume_request(manifest: Mapping[str, Any]) -> dict[str, Any]:
    inputs = _mapping(manifest.get("inputs"))
    evidence = _mapping(inputs.get("evidence_manifest"))
    vectors = _mapping(inputs.get("identity_vectors"))
    return {
        **_request_base(manifest),
        "evidence_manifest": evidence["path"],
        "evidence_manifest_sha256": evidence["sha256"],
        "identity_vectors_sha256": vectors["sha256"],
        "invalid_categories": dict(_mapping(manifest.get("invalid_categories"))),
    }


def _produce_request(manifest: Mapping[str, Any]) -> dict[str, Any]:
    inputs = _mapping(manifest.get("inputs"))
    return {
        **_request_base(manifest),
        "sources": list(_sequence(inputs.get("sources"))),
    }


def _artifact_payload(value: object) -> bytes:
    artifact = _mapping(value, category="alternate_artifact_invalid")
    try:
        payload = bytes.fromhex(_text(artifact.get("payload_hex")))
    except ValueError as error:
        raise AlternateConformanceError("alternate_artifact_invalid") from error
    if artifact.get("byte_length") != len(payload) or artifact.get("artifact_id") != _raw_sha256(
        payload
    ):
        raise AlternateConformanceError("alternate_artifact_invalid")
    return payload


def _validate_alternate_outputs(produce: Mapping[str, Any]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    outputs = _mapping(produce.get("outputs"), category="alternate_output_invalid")
    if set(outputs) != {"table", "text"}:
        raise AlternateConformanceError("alternate_output_incomplete")
    for key in sorted(outputs):
        output = _mapping(outputs[key], category="alternate_output_invalid")
        native = NativeRepresentation.model_validate_json(
            canonical_json_bytes(output.get("native"))
        )
        references = [
            EvidenceReference.model_validate_json(canonical_json_bytes(item))
            for item in _sequence(output.get("references"), category="alternate_output_invalid")
        ]
        projections = [
            EvidenceProjection.model_validate_json(canonical_json_bytes(item))
            for item in _sequence(output.get("projections"), category="alternate_output_invalid")
        ]
        validate_evidence_records(
            native,
            references,
            projections,
            expected_source_version_id=_text(output.get("source_version_id")),
        )
        native_payload = _artifact_payload(output.get("native_artifact"))
        if native.native_artifact_byte_length != len(
            native_payload
        ) or native.native_artifact_id != _raw_sha256(native_payload):
            raise AlternateConformanceError("alternate_native_invalid")
        retrieval = {
            _text(_mapping(item, category="alternate_artifact_invalid").get("artifact_id")): item
            for item in _sequence(
                output.get("retrieval_artifacts"), category="alternate_output_invalid"
            )
        }
        for projection in projections:
            artifact = retrieval.get(projection.retrieval.artifact_id)
            if artifact is None:
                raise AlternateConformanceError("alternate_artifact_missing")
            payload = _artifact_payload(artifact)
            if len(payload) != projection.retrieval.byte_length:
                raise AlternateConformanceError("alternate_artifact_invalid")
        rendered = canonical_json_bytes(output).decode("utf-8").casefold()
        if "docling" in rendered:
            raise AlternateConformanceError("provider_leakage")
        observations.append(
            {
                "case_id": f"reference:{key}",
                "direction": "alternate_to_reference",
                "expected": "accept",
                "kind": "reference_consumer",
                "observed": "accept",
                "status": "pass",
            }
        )
    return observations


def _combined_coverage(
    consume: Mapping[str, Any],
    produce: Mapping[str, Any],
    reference_observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    consumed = _mapping(consume.get("coverage"), category="coverage_invalid")
    produced = _mapping(produce.get("coverage"), category="coverage_invalid")
    directions = {
        *(
            _text(item.get("direction"), category="coverage_invalid")
            for item in reference_observations
        ),
        *(
            _text(item.get("direction"), category="coverage_invalid")
            for item in _sequence(consume.get("observations"), category="coverage_invalid")
        ),
    }
    return {
        "anchors": sorted(
            set(_sequence(consumed.get("anchors"))) | set(_sequence(produced.get("anchors")))
        ),
        "directions": sorted(directions),
        "identity_vectors": consumed.get("identity_vectors"),
        "invalid_roots": consumed.get("invalid_roots"),
        "models": sorted(_sequence(consumed.get("models"))),
        "record_sets": consumed.get("record_sets"),
        "source_kinds": sorted(_sequence(produced.get("source_kinds"))),
        "valid_roots": consumed.get("valid_roots"),
    }


def build_decision(
    manifest: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    *,
    deterministic: bool,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Build the closed, no-waiver decision from exact conformance facts."""
    failures: list[str] = []
    keys = [
        (
            item.get("direction"),
            item.get("kind"),
            item.get("case_id"),
        )
        for item in observations
    ]
    if len(keys) != len(set(keys)):
        failures.append("duplicate_observation")
    if any(
        item.get("status") != "pass" or item.get("expected") != item.get("observed")
        for item in observations
    ):
        failures.append("failed_observation")
    required = _mapping(manifest.get("required_coverage"))
    for key in sorted(set(required) - {"observations"}):
        if coverage.get(key) != required.get(key):
            failures.append(f"coverage:{key}")
    if len(observations) != required.get("observations"):
        failures.append("coverage:observations")
    if not deterministic:
        failures.append("nondeterministic_output")
    failures = sorted(set(failures))
    inputs = _mapping(manifest.get("inputs"))
    implementation = _mapping(manifest.get("implementation"))
    input_projection = {
        "evidence_manifest_sha256": _mapping(inputs.get("evidence_manifest"))["sha256"],
        "identity_vectors_sha256": _mapping(inputs.get("identity_vectors"))["sha256"],
        "implementation_sha256": implementation["sha256"],
        "manifest_sha256": manifest_sha256,
        "source_sha256": [_mapping(item)["sha256"] for item in _sequence(inputs.get("sources"))],
    }
    body: dict[str, Any] = {
        "contract_stability": "experimental",
        "coverage": dict(coverage),
        "failures": failures,
        "friction": [
            {
                "disposition": "document_validation_layers",
                "severity": "medium",
                "surface": "semantic invariants exceed JSON Schema",
            },
            {
                "disposition": "retain_explicit_identity_profile",
                "severity": "medium",
                "surface": "purpose-specific RFC8785 identity allowlists",
            },
            {
                "disposition": "retain_profile_scope",
                "severity": "low",
                "surface": (
                    "page geometry and table/provider pointers require provider-profile semantics"
                ),
            },
        ],
        "input_id": canonical_sha256(input_projection),
        "limitations": [
            "Internal independent process; no external organization adoption evidence.",
            "Synthetic TXT/CSV scope does not measure production parser quality.",
            "Declared page geometry does not establish cross-parser visual equivalence.",
            "Canonicalization evidence covers the current no-float identity payload domain.",
        ],
        "observations": [dict(item) for item in observations],
        "observation_set_id": canonical_sha256([dict(item) for item in observations]),
        "profile_version": PROFILE_VERSION,
        "prohibited_claims": [
            "arbitrary parsers are interchangeable",
            "anchors are semantically equivalent across providers",
            "the evidence contract is stable or standardized",
            "the alternate parser is production ready",
        ],
        "provider_leakage": [],
        "required_changes": [],
        "status": "supported_for_scoped_claim" if not failures else "not_supported",
        "verified_claims": [
            "An isolated stdlib consumer matches the complete F006 evidence corpus.",
            "A non-Docling TXT/CSV producer emits reference-valid thin evidence.",
            (
                "Text, page-region, table-cell and opaque-pointer contract shapes "
                "interoperate in the measured scope."
            ),
        ]
        if not failures
        else [],
    }
    body["decision_id"] = canonical_sha256(body)
    return body


def run_conformance(
    manifest_path: Path = DEFAULT_MANIFEST,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute both directions and return generated record-set and decision documents."""
    manifest_path = manifest_path.resolve(strict=True)
    if manifest_path.is_symlink() or manifest_path != DEFAULT_MANIFEST.resolve():
        raise AlternateConformanceError("manifest_path_invalid")
    manifest_bytes = manifest_path.read_bytes()
    manifest = _load_object(manifest_path)
    if manifest.get("profile_version") != PROFILE_VERSION:
        raise AlternateConformanceError("profile_version")
    script, implementation_id = _script_path(manifest)
    timeout = int(_mapping(manifest.get("limits"))["max_execution_seconds"])
    self_check, _ = _invoke(script, None, None, timeout=timeout)
    if (
        self_check.get("isolated") is not True
        or self_check.get("no_site") is not True
        or self_check.get("implementation_sha256") != implementation_id
    ):
        raise AlternateConformanceError("isolation_failed")
    consume, _ = _invoke(script, "consume", _consume_request(manifest), timeout=timeout)
    produce, first_bytes = _invoke(script, "produce", _produce_request(manifest), timeout=timeout)
    second, second_bytes = _invoke(script, "produce", _produce_request(manifest), timeout=timeout)
    third, third_bytes = _invoke(script, "produce", _produce_request(manifest), timeout=timeout)
    deterministic = first_bytes == second_bytes == third_bytes and produce == second == third
    reference_observations = _validate_alternate_outputs(produce)
    observations = [
        *[
            dict(item)
            for item in _sequence(consume.get("observations"), category="response_invalid")
        ],
        *[
            dict(item)
            for item in _sequence(produce.get("observations"), category="response_invalid")
        ],
        *reference_observations,
    ]
    observations.sort(
        key=lambda item: (str(item["direction"]), str(item["kind"]), str(item["case_id"]))
    )
    coverage = _combined_coverage(consume, produce, reference_observations)
    decision = build_decision(
        manifest,
        observations,
        coverage,
        deterministic=deterministic,
        manifest_sha256=_raw_sha256(manifest_bytes),
    )
    record_set = {
        "implementation_sha256": implementation_id,
        "outputs": produce["outputs"],
        "profile_version": PROFILE_VERSION,
    }
    return record_set, decision


def _expected_paths(manifest: Mapping[str, Any]) -> tuple[Path, Path]:
    expected = _mapping(manifest.get("expected"))
    return (
        _confined(CONFORMANCE_ROOT, expected.get("record_set")),
        _confined(CONFORMANCE_ROOT, expected.get("decision")),
    )


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Generate or drift-check the canonical F016 conformance artifacts."""
    arguments = _parser().parse_args(argv)
    try:
        record_set, decision = run_conformance()
        manifest = _load_object(DEFAULT_MANIFEST)
        expected = _mapping(manifest.get("expected"))
        record_path = CONFORMANCE_ROOT.joinpath(*PurePosixPath(_text(expected["record_set"])).parts)
        decision_path = CONFORMANCE_ROOT.joinpath(*PurePosixPath(_text(expected["decision"])).parts)
        record_bytes = canonical_json_bytes(record_set) + b"\n"
        decision_bytes = canonical_json_bytes(decision) + b"\n"
        if arguments.write:
            _atomic_write(record_path, record_bytes)
            _atomic_write(decision_path, decision_bytes)
        else:
            if not record_path.is_file() or record_path.read_bytes() != record_bytes:
                raise AlternateConformanceError("record_set_drift")
            if not decision_path.is_file() or decision_path.read_bytes() != decision_bytes:
                raise AlternateConformanceError("decision_drift")
        print(
            "Alternate conformance passed: "
            f"{len(record_set['outputs'])} sources, "
            f"status={decision['status']}, decision={decision['decision_id']}."
        )
        return 0
    except AlternateConformanceError as error:
        print(f"Alternate conformance failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
