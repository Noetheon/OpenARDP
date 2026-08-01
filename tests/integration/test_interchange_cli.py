"""Trusted-operator CLI tests for experimental package exchange."""

from __future__ import annotations

import json
from pathlib import Path

from openardp.interfaces.cli import main
from tests.interchange_factory import synthetic_package


def test_package_cli_export_verify_and_import_are_body_free(
    tmp_path: Path,
    capsys: object,
) -> None:
    """Exercise all explicit commands without requiring or mutating a workspace."""
    data = b"OpenARDP synthetic evidence\n"
    source = tmp_path / "private-user-file.txt"
    source.write_bytes(data)
    package = synthetic_package(data)
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "package": package.model_dump(mode="json"),
                "asset_sources": {package.assets[0].object_id: str(source)},
            }
        )
    )
    archive = tmp_path / "package.zip"
    snapshot = tmp_path / "snapshot"

    assert (
        main(["package-export", "--request", str(request), "--destination", str(archive), "--json"])
        == 0
    )
    export_output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert package.package_id in export_output
    assert str(source) not in export_output
    assert "instruction" not in export_output

    assert main(["package-verify", "--package", str(archive), "--json"]) == 0
    verify_output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert package.package_id in verify_output
    assert str(archive) not in verify_output

    assert (
        main(
            [
                "package-import",
                "--package",
                str(archive),
                "--destination",
                str(snapshot),
                "--json",
            ]
        )
        == 0
    )
    import_output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert package.package_id in import_output
    assert str(snapshot) not in import_output


def test_package_cli_returns_stable_sanitized_error_category(
    tmp_path: Path,
    capsys: object,
) -> None:
    """Classify malformed input without echoing its local path or bytes."""
    hostile = tmp_path / "private-malformed.zip"
    hostile.write_bytes(b"not a zip and secret body")
    assert main(["package-verify", "--package", str(hostile), "--json"]) == 2
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "malformed_package" in output
    assert str(hostile) not in output
    assert "secret body" not in output
