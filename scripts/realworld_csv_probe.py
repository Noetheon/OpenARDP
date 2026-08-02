"""Isolated stdlib-only body-free CSV structural probe for F024."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path, PurePosixPath

PROFILE_VERSION = "0.1.0"
MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 1_048_576


class ProbeFailure(ValueError):
    """One stable body-free CSV probe failure."""


def _fail(category: str) -> None:
    raise ProbeFailure(category)


def _load_json(payload: bytes) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in items:
            if key in value:
                _fail("duplicate_json_key")
            value[key] = item
        return value

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: _fail("json_value"),
        )
    except ProbeFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("json")
    if not isinstance(value, dict):
        _fail("request")
    return value


def _safe_json(value: object) -> None:
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            _fail("json_value")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            _fail("json_value")
        return
    if isinstance(value, list):
        for item in value:
            _safe_json(item)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for key, item in value.items():
            _safe_json(key)
            _safe_json(item)
        return
    _fail("json_value")


def _canonical(value: object) -> bytes:
    _safe_json(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _text(value: object) -> str:
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        _fail("request")
    return value


def _positive(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _fail("request")
    return value


def _read_source(request: dict[str, object]) -> bytes:
    root_value = Path(_text(request.get("root")))
    if not root_value.is_absolute() or root_value.is_symlink():
        _fail("root")
    try:
        root = root_value.resolve(strict=True)
    except OSError:
        _fail("root")
    relative_text = _text(request.get("path"))
    relative = PurePosixPath(relative_text)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        _fail("path")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            _fail("path")
    try:
        source = current.resolve(strict=True)
        source.relative_to(root)
        before = source.stat()
    except (OSError, ValueError):
        _fail("path")
    maximum = _positive(request.get("max_file_bytes"))
    if not source.is_file() or before.st_size > maximum:
        _fail("resource_limit")
    try:
        payload = source.read_bytes()
        after = source.stat()
    except OSError:
        _fail("read")
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if len(payload) != before.st_size or before_identity != after_identity:
        _fail("read_race")
    if _sha(payload) != _text(request.get("sha256")):
        _fail("digest_mismatch")
    return payload


def _probe(request: dict[str, object], implementation_id: str) -> dict[str, object]:
    required = {
        "key",
        "max_cells",
        "max_characters",
        "max_file_bytes",
        "max_rows",
        "path",
        "profile_version",
        "root",
        "sha256",
    }
    if set(request) != required or request.get("profile_version") != PROFILE_VERSION:
        _fail("request")
    payload = _read_source(request)
    try:
        text = payload.decode("utf-8", errors="strict")
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error):
        _fail("csv")
    if not rows or not rows[0]:
        _fail("csv")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        _fail("csv_shape")
    characters = sum(len(cell) for row in rows for cell in row)
    cells = len(rows) * width
    if (
        len(rows) > _positive(request.get("max_rows"))
        or cells > _positive(request.get("max_cells"))
        or characters > _positive(request.get("max_characters"))
    ):
        _fail("resource_limit")
    native = {
        "dialect": {"delimiter": ",", "doublequote": True, "quotechar": '"'},
        "format": "rfc4180-table",
        "rows": rows,
        "source_byte_length": len(payload),
    }
    native_payload = _canonical(native)
    block_ids = [_sha(_canonical({"ordinal": index, "row": row})) for index, row in enumerate(rows)]
    recipe = {
        "dialect": native["dialect"],
        "name": "stdlib-csv-body-free-probe",
        "profile_version": PROFILE_VERSION,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    return {
        "anchor_classes": ["page_region", "provider_pointer", "table_cell", "text_span"],
        "block_count": len(rows),
        "block_set_id": _sha(_canonical(block_ids)),
        "column_count": width,
        "implementation_sha256": implementation_id,
        "key": _text(request.get("key")),
        "native_bytes": len(native_payload),
        "native_id": _sha(native_payload),
        "profile_version": PROFILE_VERSION,
        "recipe_id": _sha(_canonical(recipe)),
        "retrieval_complete": True,
        "row_count": len(rows),
        "source_id": _sha(payload),
    }


def main() -> int:
    """Probe one confined CSV and emit canonical body-free JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        request_path = arguments.request
        if (
            not request_path.is_absolute()
            or request_path.is_symlink()
            or not request_path.is_file()
            or request_path.stat().st_size > MAX_REQUEST_BYTES
        ):
            _fail("request")
        request = _load_json(request_path.read_bytes())
        result = _probe(request, _sha(Path(__file__).resolve().read_bytes()))
        output = _canonical(result) + b"\n"
        if len(output) > MAX_RESPONSE_BYTES:
            _fail("resource_limit")
    except (OSError, ProbeFailure):
        sys.stderr.buffer.write(b"REALWORLD_CSV_PROBE_ERROR\n")
        return 2
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
