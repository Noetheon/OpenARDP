"""End-to-end deterministic package export, verification and import tests."""

from __future__ import annotations

import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from openardp.adapters.bagit_interchange import BagItPackageAdapter, LocalAssetSource
from openardp.domain.interchange import (
    AssetDisposition,
    InterchangeLimits,
    InterchangeOutcome,
    InterchangePackage,
    VerifiedPackage,
)
from openardp.ports.interchange import (
    InterchangeDestinationConflict,
    InterchangePolicyRejected,
    InterchangePublicationFailed,
    InterchangeResourceExceeded,
    InterchangeSourceChanged,
)
from openardp.services.interchange import InterchangeService
from tests.interchange_factory import synthetic_package

CORPUS = Path(__file__).parents[2] / "conformance" / "interchange" / "v0.1.0" / "valid"


def _export(tmp_path: Path, *, name: str = "package.zip") -> tuple[Path, bytes]:
    data = b"OpenARDP synthetic evidence\n"
    source = tmp_path / "private-local-name.txt"
    source.write_bytes(data)
    package = synthetic_package(data)
    destination = tmp_path / name
    InterchangeService().export(
        package,
        LocalAssetSource({package.assets[0].object_id: source}),
        destination,
    )
    return destination, data


def test_export_is_byte_deterministic_and_does_not_leak_local_path(tmp_path: Path) -> None:
    """Produce identical canonical transport bytes from identical semantic input."""
    first, _ = _export(tmp_path, name="first.zip")
    second, _ = _export(tmp_path, name="second.zip")
    assert first.read_bytes() == second.read_bytes()
    assert b"private-local-name" not in first.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == sorted(archive.namelist())
        assert all(item.compress_type == zipfile.ZIP_STORED for item in archive.infolist())


def test_verify_and_import_publish_one_complete_snapshot(tmp_path: Path) -> None:
    """Verify before publication and converge an exact repeated import."""
    package, _ = _export(tmp_path)
    service = InterchangeService()
    verified = service.verify(package)
    destination = tmp_path / "snapshot"
    first = service.import_snapshot(package, destination)
    second = service.import_snapshot(package, destination)
    assert verified.package_id == first.package_id == second.package_id
    assert first.outcome is InterchangeOutcome.COMPLETE
    assert second.outcome is InterchangeOutcome.CONVERGED
    assert (destination / "openardp-package.json").is_file()


def test_changed_source_fails_without_visible_destination(tmp_path: Path) -> None:
    """Fail export closed when selected bytes disagree with declared identity."""
    package = synthetic_package()
    source = tmp_path / "source.txt"
    source.write_bytes(b"different")
    destination = tmp_path / "package.zip"
    with pytest.raises(InterchangeSourceChanged):
        InterchangeService().export(
            package,
            LocalAssetSource({package.assets[0].object_id: source}),
            destination,
        )
    assert not destination.exists()


def test_resource_limit_fails_before_publication(tmp_path: Path) -> None:
    """Stop at the first configured expanded-byte boundary."""
    source = tmp_path / "source.txt"
    destination = tmp_path / "package.zip"
    limits = InterchangeLimits(max_expanded_bytes=1_048_576, max_entry_bytes=1_024)
    # The installed lower ranges prevent unsafe near-zero limits; use a declared
    # asset exceeding the configured per-entry bound.
    oversized = synthetic_package(b"x" * 2_000)
    source.write_bytes(b"x" * 2_000)
    with pytest.raises(InterchangeResourceExceeded):
        InterchangeService().export(
            oversized,
            LocalAssetSource({oversized.assets[0].object_id: source}),
            destination,
            limits=limits,
        )
    assert not destination.exists()


def test_foreign_existing_import_destination_is_never_modified(tmp_path: Path) -> None:
    """Reject rather than merge with a foreign snapshot destination."""
    package, _ = _export(tmp_path)
    destination = tmp_path / "snapshot"
    destination.mkdir()
    marker = destination / "foreign.txt"
    marker.write_text("preserve")
    with pytest.raises(InterchangeDestinationConflict):
        InterchangeService().import_snapshot(package, destination)
    assert marker.read_text() == "preserve"


def test_compressed_profile_member_is_policy_rejected(tmp_path: Path) -> None:
    """Reject non-profile compression before reading expanded payload bytes."""
    package, _ = _export(tmp_path)
    hostile = tmp_path / "compressed.zip"
    with (
        zipfile.ZipFile(package) as source,
        zipfile.ZipFile(hostile, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        for name in source.namelist():
            target.writestr(name, source.read(name))
    with pytest.raises(InterchangePolicyRejected):
        InterchangeService().verify(hostile)


def test_twenty_concurrent_exact_exports_converge(tmp_path: Path) -> None:
    """Publish one deterministic result under same-identity races."""
    data = b"OpenARDP synthetic evidence\n"
    source = tmp_path / "source.txt"
    source.write_bytes(data)
    package = synthetic_package(data)
    destination = tmp_path / "package.zip"

    def run() -> InterchangeOutcome:
        return (
            InterchangeService()
            .export(
                package,
                LocalAssetSource({package.assets[0].object_id: source}),
                destination,
            )
            .outcome
        )

    with ThreadPoolExecutor(max_workers=20) as pool:
        outcomes = tuple(pool.map(lambda _: run(), range(20)))
    assert outcomes.count(InterchangeOutcome.COMPLETE) == 1
    assert outcomes.count(InterchangeOutcome.CONVERGED) == 19
    InterchangeService().verify(destination)


def test_twenty_concurrent_exact_imports_converge(tmp_path: Path) -> None:
    """Publish one immutable snapshot under same-package import races."""
    package, _ = _export(tmp_path)
    destination = tmp_path / "snapshot"

    def run() -> InterchangeOutcome:
        return InterchangeService().import_snapshot(package, destination).outcome

    with ThreadPoolExecutor(max_workers=20) as pool:
        outcomes = tuple(pool.map(lambda _: run(), range(20)))
    assert outcomes.count(InterchangeOutcome.COMPLETE) == 1
    assert outcomes.count(InterchangeOutcome.CONVERGED) == 19
    adapter = BagItPackageAdapter()
    verified = adapter.verify(package, limits=InterchangeLimits())
    assert adapter.verify_snapshot(destination, verified)


@pytest.mark.parametrize(
    "vector_name",
    ["minimal.zip", "preserved-extension.zip", "referenced-only.zip"],
)
def test_three_representative_scopes_repeat_and_roundtrip(
    tmp_path: Path,
    vector_name: str,
) -> None:
    """Prove two identical exports and one complete import for every valid scope."""
    adapter = BagItPackageAdapter()
    golden = CORPUS / vector_name
    expected = adapter.verify(golden, limits=InterchangeLimits())
    scope = tmp_path / vector_name.removesuffix(".zip")
    scope.mkdir()
    sources: dict[str, Path] = {}
    with zipfile.ZipFile(golden) as archive:
        for asset in expected.package.assets:
            if asset.disposition is AssetDisposition.INCLUDED:
                assert asset.payload_path is not None
                source = scope / f"source-{len(sources)}.bin"
                source.write_bytes(archive.read(asset.payload_path))
                sources[asset.object_id] = source
    first = scope / "first.zip"
    second = scope / "second.zip"
    service = InterchangeService(adapter)
    service.export(expected.package, LocalAssetSource(sources), first)
    service.export(expected.package, LocalAssetSource(sources), second)
    assert first.read_bytes() == second.read_bytes() == golden.read_bytes()
    snapshot = scope / "snapshot"
    imported = service.import_snapshot(first, snapshot)
    replay = adapter.verify(first, limits=InterchangeLimits())
    assert imported.package_id == expected.package.package_id
    assert replay.package == expected.package
    assert adapter.verify_snapshot(snapshot, replay)


class _InterruptedCopyAdapter(BagItPackageAdapter):
    """Fail after creating operation-owned import residue."""

    def copy_verified_snapshot(
        self,
        package: Path,
        verified: VerifiedPackage,
        staging: Path,
        *,
        limits: InterchangeLimits,
    ) -> None:
        del package, verified, limits
        (staging / "partial.bin").write_bytes(b"partial")
        raise InterchangePublicationFailed("synthetic interruption")


def test_import_interruption_removes_only_owned_staging(tmp_path: Path) -> None:
    """Leave no destination or staging residue after a copy interruption."""
    package, _ = _export(tmp_path)
    unrelated = tmp_path / ".snapshot.import-unrelated"
    unrelated.mkdir()
    marker = unrelated / "preserve.txt"
    marker.write_text("preserve")
    destination = tmp_path / "snapshot"
    with pytest.raises(InterchangePublicationFailed, match="synthetic interruption"):
        InterchangeService(_InterruptedCopyAdapter()).import_snapshot(package, destination)
    assert not destination.exists()
    assert marker.read_text() == "preserve"
    assert sorted(tmp_path.glob(".snapshot.import-*")) == [unrelated]


def test_concurrent_conflicting_exports_publish_exactly_one_package(tmp_path: Path) -> None:
    """Resolve conflicting export publication without mixed or partial bytes."""
    inputs: list[tuple[InterchangePackage, Path]] = []
    for index, data in enumerate((b"first package", b"second package")):
        package = synthetic_package(data)
        source = tmp_path / f"source-{index}.txt"
        source.write_bytes(data)
        inputs.append((package, source))
    destination = tmp_path / "conflict.zip"
    barrier = Barrier(2)

    def run(item: tuple[InterchangePackage, Path]) -> tuple[str, str]:
        package, source = item
        barrier.wait()
        try:
            result = InterchangeService().export(
                package,
                LocalAssetSource({package.assets[0].object_id: source}),
                destination,
            )
            return package.package_id, result.outcome.value
        except InterchangeDestinationConflict:
            return package.package_id, "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(run, inputs))
    assert sorted(outcome for _, outcome in outcomes) == ["complete", "conflict"]
    published = BagItPackageAdapter().verify(destination, limits=InterchangeLimits())
    assert published.package.package_id in {item[0] for item in outcomes}


def test_concurrent_conflicting_imports_publish_exactly_one_snapshot(tmp_path: Path) -> None:
    """Resolve conflicting snapshot publication without mixing package members."""
    first, _ = _export(tmp_path, name="first-import.zip")
    second = tmp_path / "second-import.zip"
    different_data = b"distinct imported package"
    different_source = tmp_path / "different.txt"
    different_source.write_bytes(different_data)
    different = synthetic_package(different_data)
    InterchangeService().export(
        different,
        LocalAssetSource({different.assets[0].object_id: different_source}),
        second,
    )
    packages = (first, second)
    destination = tmp_path / "snapshot"
    barrier = Barrier(2)

    def run(package: Path) -> tuple[str, str]:
        verified = BagItPackageAdapter().verify(package, limits=InterchangeLimits())
        barrier.wait()
        try:
            result = InterchangeService().import_snapshot(package, destination)
            return verified.package.package_id, result.outcome.value
        except InterchangeDestinationConflict:
            return verified.package.package_id, "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(run, packages))
    assert sorted(outcome for _, outcome in outcomes) == ["complete", "conflict"]
    published_ids = []
    adapter = BagItPackageAdapter()
    for package in packages:
        verified = adapter.verify(package, limits=InterchangeLimits())
        if adapter.verify_snapshot(destination, verified):
            published_ids.append(verified.package.package_id)
    assert published_ids == [
        next(identity for identity, outcome in outcomes if outcome == "complete")
    ]
