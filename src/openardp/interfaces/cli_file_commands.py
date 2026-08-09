"""Bounded local-file, interchange, and release commands for the CLI."""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict, JsonValue

from openardp.adapters.release_benchmarks import (
    NativeRetrievalTreatment,
    NativeReuseTreatment,
    OpenArdpCompilerTreatment,
    OpenArdpRetrievalTreatment,
    RawReparseTreatment,
)
from openardp.adapters.release_evidence import LocalReleaseEvidenceStore
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.interchange import AssetDisposition, InterchangeLimits, InterchangePackage
from openardp.domain.maintenance import ReclamationPlan
from openardp.domain.release import (
    EvidenceCheck,
    ReleaseDecision,
    ReleaseGatePolicy,
    SuiteName,
)
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.interfaces.cli_arguments import ContextCommandUsageError as _UsageError
from openardp.ports.release import ReleaseEvidenceConflict
from openardp.services.release_benchmarks import (
    build_platform_evidence,
    load_benchmark_cases,
    run_benchmarks,
)
from openardp.services.release_gate import build_claim_map, evaluate_release, render_release_report


class _PackageExportRequest(BaseModel):
    """Trusted local request envelope whose paths never enter package metadata."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    package: InterchangePackage
    asset_sources: dict[str, str]


def _load_model_manifest(path: Path) -> ModelBundleManifest:
    selected = path.expanduser().absolute()
    descriptor: int | None = None
    try:
        metadata = selected.lstat()
        if selected.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ValueError
        if metadata.st_size > 8_388_608:
            raise ValueError
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(selected, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (metadata.st_dev, metadata.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ):
            raise ValueError
        chunks: list[bytes] = []
        observed = 0
        while chunk := os.read(descriptor, 1_048_576):
            observed += len(chunk)
            if observed > 8_388_608:
                raise ValueError
            chunks.append(chunk)
        if observed != metadata.st_size:
            raise ValueError
        payload = b"".join(chunks)
        return ModelBundleManifest.model_validate_json(payload)
    except (OSError, ValueError):
        raise ValueError("local model manifest is invalid") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _load_reclamation_plan(path: Path) -> ReclamationPlan:
    """Load one bounded regular exact plan without following links."""
    selected = path.expanduser().absolute()
    descriptor: int | None = None
    try:
        metadata = selected.lstat()
        if selected.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ValueError
        if metadata.st_size > 16_777_216:
            raise ValueError
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(selected, flags)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (metadata.st_dev, metadata.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise ValueError
        chunks: list[bytes] = []
        observed = 0
        while chunk := os.read(descriptor, 1_048_576):
            observed += len(chunk)
            if observed > 16_777_216:
                raise ValueError
            chunks.append(chunk)
        if observed != metadata.st_size:
            raise ValueError
        return ReclamationPlan.model_validate_json(b"".join(chunks))
    except (OSError, ValueError):
        raise ValueError("reclamation plan is invalid") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _load_package_export_request(path: Path) -> _PackageExportRequest:
    """Load one bounded safe local export request without echoing its paths."""
    payload = _read_bounded_regular(path, max_bytes=16_777_216)
    try:
        request = _PackageExportRequest.model_validate_json(payload)
    except ValueError:
        raise ValueError("package export request is invalid") from None
    included = {
        asset.object_id
        for asset in request.package.assets
        if asset.disposition is AssetDisposition.INCLUDED
    }
    if set(request.asset_sources) != included:
        raise ValueError("package export request asset selection is incomplete")
    return request


def _read_bounded_regular(path: Path, *, max_bytes: int) -> bytes:
    """Read one stable regular file through a no-follow descriptor under a hard cap."""
    selected = path.expanduser().absolute()
    descriptor: int | None = None
    try:
        metadata = selected.lstat()
        if selected.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ValueError
        if metadata.st_size > max_bytes:
            raise ValueError
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(selected, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (metadata.st_dev, metadata.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ):
            raise ValueError
        chunks: list[bytes] = []
        observed = 0
        while chunk := os.read(descriptor, 1_048_576):
            observed += len(chunk)
            if observed > max_bytes:
                raise ValueError
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            observed != metadata.st_size
            or opened.st_size != after.st_size
            or (opened.st_dev, opened.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise ValueError
        return b"".join(chunks)
    except (OSError, ValueError):
        raise ValueError("bounded local input is invalid") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _release_evidence(arguments: argparse.Namespace) -> dict[str, object]:
    """Generate and immutably publish one local platform evidence bundle."""
    repository_root = Path(arguments.source_root)
    corpus = Path(arguments.corpus)
    cases = load_benchmark_cases(repository_root, corpus)
    treatments = (
        RawReparseTreatment(),
        NativeReuseTreatment(),
        NativeRetrievalTreatment(),
        OpenArdpRetrievalTreatment(),
        OpenArdpCompilerTreatment(),
    )
    observations = run_benchmarks(cases, treatments, repetitions=7, warmups=1)
    evidence = build_platform_evidence(
        repository_root=repository_root,
        corpus=corpus,
        observations=observations,
        suite_results=_load_suite_results(arguments.suite_results),
        reference_timing=bool(arguments.reference_timing),
    )
    destination = Path(arguments.output)
    LocalReleaseEvidenceStore().publish(destination, evidence)
    return {
        "evidence_id": evidence.evidence_id,
        "platform_id": evidence.environment.platform_id,
        "reference_timing": evidence.environment.reference_timing,
        "observation_count": len(evidence.observations),
        "suite_status": {suite.name.value: suite.status.value for suite in evidence.suites},
        "output": str(destination),
    }


def _release_gate(arguments: argparse.Namespace) -> dict[str, object]:
    """Load exact platform bundles and publish one exhaustive release decision."""
    policy_payload = _strict_json_object(
        _read_bounded_regular(Path(arguments.policy), max_bytes=1_048_576)
    )
    policy = ReleaseGatePolicy.model_validate_json(
        canonical_json_bytes(cast(JsonValue, policy_payload))
    )
    store = LocalReleaseEvidenceStore()
    evidence = tuple(store.load(Path(path)) for path in arguments.evidence)
    decision = evaluate_release(
        policy=policy,
        evidence=evidence,
        decision_at=_parse_release_time(str(arguments.decision_at)),
    )
    output = _release_output_directory(Path(arguments.output))
    decision_path = output / "decision.json"
    _publish_exact_file(
        decision_path,
        canonical_json_bytes(decision.model_dump(mode="json")) + b"\n",
    )
    return {
        "decision_id": decision.decision_id,
        "status": decision.status.value,
        "blockers": decision.blockers,
        "output": str(decision_path),
    }


def _release_report(arguments: argparse.Namespace) -> dict[str, object]:
    """Generate or check byte-stable human and claim projections."""
    decision_payload = _strict_json_object(
        _read_bounded_regular(Path(arguments.decision), max_bytes=8_388_608)
    )
    decision = ReleaseDecision.model_validate_json(
        canonical_json_bytes(cast(JsonValue, decision_payload))
    )
    decision.verify_identity()
    output = _release_output_directory(Path(arguments.output))
    projections = {
        output / "report.md": render_release_report(decision),
        output / "claim-map.json": canonical_json_bytes(build_claim_map(decision)) + b"\n",
    }
    if bool(arguments.check):
        drift = tuple(
            path.name
            for path, expected in projections.items()
            if not path.is_file() or _read_bounded_regular(path, max_bytes=8_388_608) != expected
        )
        if drift:
            raise ReleaseEvidenceConflict("release report projection drift")
    else:
        for path, expected in projections.items():
            _publish_exact_file(path, expected)
    return {
        "decision_id": decision.decision_id,
        "status": decision.status.value,
        "checked": bool(arguments.check),
        "outputs": tuple(str(path) for path in projections),
    }


def _load_suite_results(path: Path | None) -> dict[SuiteName, tuple[EvidenceCheck, ...]]:
    if path is None:
        return {}
    payload = _strict_json_object(_read_bounded_regular(path, max_bytes=4_194_304))
    if set(payload) != {"schema_version", "suites"} or payload["schema_version"] != "0.1.0":
        raise _UsageError("suite result root is invalid")
    raw_suites = payload["suites"]
    if not isinstance(raw_suites, dict):
        raise _UsageError("suite results must be an object")
    results: dict[SuiteName, tuple[EvidenceCheck, ...]] = {}
    try:
        for name, raw_checks in raw_suites.items():
            suite = SuiteName(name)
            if suite in {SuiteName.PERFORMANCE, SuiteName.CORRECTNESS}:
                raise _UsageError("derived benchmark suites cannot be supplied")
            if not isinstance(raw_checks, list):
                raise _UsageError("suite checks must be an array")
            results[suite] = tuple(
                EvidenceCheck.model_validate_json(canonical_json_bytes(item)) for item in raw_checks
            )
    except (TypeError, ValueError) as error:
        if isinstance(error, _UsageError):
            raise
        raise _UsageError("suite result is invalid") from error
    return results


def _strict_json_object(data: bytes) -> dict[str, object]:
    try:
        value = json.loads(data, object_pairs_hook=_unique_json_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise _UsageError("JSON input is invalid") from error
    if not isinstance(value, dict):
        raise _UsageError("JSON input must be an object")
    return cast(dict[str, object], value)


def _unique_json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _parse_release_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _UsageError("decision-at must be RFC 3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _UsageError("decision-at must include a UTC offset")
    return parsed.astimezone(UTC)


def _release_output_directory(path: Path) -> Path:
    target = path.expanduser().absolute()
    try:
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata = target.lstat()
    except OSError as error:
        raise ReleaseEvidenceConflict("release output directory is unavailable") from error
    if target.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise ReleaseEvidenceConflict("release output directory is unsafe")
    return target


def _publish_exact_file(path: Path, data: bytes) -> None:
    if path.exists():
        if _read_bounded_regular(path, max_bytes=8_388_608) == data:
            return
        raise ReleaseEvidenceConflict("release output conflicts")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if _read_bounded_regular(path, max_bytes=8_388_608) != data:
                raise ReleaseEvidenceConflict("release output conflicts") from None
    except OSError as error:
        raise ReleaseEvidenceConflict("release output publication failed") from error
    finally:
        temporary.unlink(missing_ok=True)


def _interchange_limits(arguments: argparse.Namespace) -> InterchangeLimits:
    """Construct one closed hostile-package limit policy from CLI integers."""
    return InterchangeLimits(
        max_archive_bytes=int(arguments.max_archive_bytes),
        max_expanded_bytes=int(arguments.max_expanded_bytes),
        max_entry_count=int(arguments.max_entry_count),
        max_entry_bytes=int(arguments.max_entry_bytes),
        max_metadata_bytes=int(arguments.max_metadata_bytes),
        max_path_bytes=int(arguments.max_path_bytes),
        max_path_depth=int(arguments.max_path_depth),
        max_relationships=int(arguments.max_relationships),
    )


__all__ = [
    "_interchange_limits",
    "_load_model_manifest",
    "_load_package_export_request",
    "_load_reclamation_plan",
    "_release_evidence",
    "_release_gate",
    "_release_report",
]
