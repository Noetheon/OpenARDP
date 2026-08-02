"""Independent stdlib-only offline validator for the F024 corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

DEFAULT_CORPUS = Path(__file__).parents[1] / "corpora/realworld/v0.1.0"
EXPECTED_FORMATS = ("csv", "docx", "md", "pdf", "pptx", "txt")
CONTROL_FILES = {
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "corpus-lock.json",
    "corpus-lock.schema.json",
}


class ValidationFailure(ValueError):
    """One deliberately body-free independent validation failure."""


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_048_576:
        raise ValidationFailure("json_file")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValidationFailure("json_duplicate")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValidationFailure("json_value")),
        )
    except ValidationFailure:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationFailure("json_invalid") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationFailure("json_shape")
    return value


def _safe_json(value: Any) -> None:
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValidationFailure("json_value")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise ValidationFailure("json_value")
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
    raise ValidationFailure("json_value")


def _canonical_bytes(value: Any) -> bytes:
    _safe_json(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _sha_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1_048_576):
                digest.update(chunk)
                length += len(chunk)
    except OSError as error:
        raise ValidationFailure("file_read") from error
    return "sha256:" + digest.hexdigest(), length


def _records(value: Any, count: int | None = None) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (count is not None and len(value) != count):
        raise ValidationFailure("record_shape")
    if not all(isinstance(item, dict) for item in value):
        raise ValidationFailure("record_shape")
    return value


def _path(value: Any, prefix: str) -> str:
    if not isinstance(value, str) or not value.startswith(prefix) or "\\" in value:
        raise ValidationFailure("path")
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or parsed.as_posix() != value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValidationFailure("path")
    return value


def _sha(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValidationFailure("sha256")
    try:
        int(value[7:], 16)
    except ValueError as error:
        raise ValidationFailure("sha256") from error
    return value


def _positive(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationFailure("integer")
    return value


def _tree(root: Path, expected: set[str]) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValidationFailure("root")
    files: set[str] = set()
    directories: set[str] = set()
    for entry in root.rglob("*"):
        relative = entry.relative_to(root).as_posix()
        metadata = entry.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValidationFailure("tree_type")
        if stat.S_ISDIR(metadata.st_mode):
            directories.add(relative)
        elif stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
            files.add(relative)
        else:
            raise ValidationFailure("tree_type")
    if directories != {"evidence", "sources"} or files != expected:
        raise ValidationFailure("tree_inventory")


def _payload_shape(path: Path, format_name: str) -> None:
    if format_name == "pdf":
        if not path.read_bytes()[:5].startswith(b"%PDF-"):
            raise ValidationFailure("payload_format")
        return
    if format_name in {"docx", "pptx"}:
        if not zipfile.is_zipfile(path):
            raise ValidationFailure("payload_format")
        required = "word/document.xml" if format_name == "docx" else "ppt/presentation.xml"
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
        except (OSError, zipfile.BadZipFile) as error:
            raise ValidationFailure("payload_format") from error
        if required not in names or any(
            name.casefold().endswith("vbaproject.bin") for name in names
        ):
            raise ValidationFailure("payload_format")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValidationFailure("payload_format") from error
    if "\x00" in text:
        raise ValidationFailure("payload_format")


def _metadata(root: Path, assets: list[dict[str, Any]]) -> None:
    cisa = _load_json(root / "evidence/cisa-kev-revision.json")
    cisa_assets = [item for item in assets if item.get("source_revision") == cisa.get("commit")]
    if (
        cisa.get("commit") != "564b8c59f9039926e2d9548ba5b334db45cb6b50"
        or cisa.get("license") != "CC0-1.0"
        or len(cisa_assets) != 3
    ):
        raise ValidationFailure("cisa_evidence")
    upstream = {Path(str(item["source_url"])).name: item for item in cisa_assets}
    files = _records(cisa.get("files"), 3)
    if {item.get("path") for item in files} != set(upstream):
        raise ValidationFailure("cisa_evidence")
    for record in files:
        name = str(record["path"])
        if record.get("size") != upstream[name].get("byte_length"):
            raise ValidationFailure("cisa_evidence")

    nasa_assets = [
        item for item in assets if str(item.get("source_revision", "")).startswith("NTRS:")
    ]
    if len(nasa_assets) != 3:
        raise ValidationFailure("nasa_evidence")
    for asset in nasa_assets:
        ntrs_id = str(asset["source_revision"])[5:]
        snapshot = _load_json(root / f"evidence/nasa-ntrs-{ntrs_id}.json")
        copyright_value = snapshot.get("copyright")
        download = snapshot.get("download")
        if not isinstance(copyright_value, dict) or not isinstance(download, dict):
            raise ValidationFailure("nasa_evidence")
        if (
            snapshot.get("ntrs_id") != ntrs_id
            or snapshot.get("title") != asset.get("title")
            or snapshot.get("record_url") != asset.get("source_record_url")
            or download.get("url") != asset.get("source_url")
            or download.get("media_type") != asset.get("media_type")
            or download.get("draft") is not False
            or copyright_value.get("determination_type")
            not in {"PUBLIC_USE_PERMITTED", "GOV_PUBLIC_USE_PERMITTED"}
            or copyright_value.get("contains_third_party_material") is not False
        ):
            raise ValidationFailure("nasa_evidence")


def validate(root: Path) -> tuple[str, int, int]:
    """Independently validate the closed corpus and return body-free facts."""
    corpus = root.absolute()
    lock = _load_json(corpus / "corpus-lock.json")
    required_lock_fields = {
        "aggregate_payload_bytes",
        "assets",
        "corpus_id",
        "corpus_name",
        "corpus_version",
        "evidence_files",
        "extensions",
        "payload_root",
        "required_formats",
        "rights",
        "schema_version",
    }
    if set(lock) != required_lock_fields:
        raise ValidationFailure("lock_fields")
    declared_id = _sha(lock.get("corpus_id"))
    projection = dict(lock)
    projection.pop("corpus_id")
    if declared_id != _sha_bytes(_canonical_bytes(projection)):
        raise ValidationFailure("corpus_identity")
    if (
        lock.get("schema_version") != "0.1.0"
        or lock.get("corpus_version") != "0.1.0"
        or lock.get("corpus_name") != "openardp-realworld"
        or lock.get("payload_root") != "sources"
        or lock.get("required_formats") != list(EXPECTED_FORMATS)
    ):
        raise ValidationFailure("lock_version")

    assets = _records(lock.get("assets"), 6)
    evidence = _records(lock.get("evidence_files"), 4)
    rights = _records(lock.get("rights"), 2)
    paths = [_path(item.get("path"), "sources/") for item in assets]
    evidence_paths = [_path(item.get("path"), "evidence/") for item in evidence]
    formats = sorted(str(item.get("format")) for item in assets)
    if paths != sorted(paths) or evidence_paths != sorted(evidence_paths):
        raise ValidationFailure("record_order")
    folded = [unicodedata.normalize("NFC", path).casefold() for path in paths]
    if len(set(paths)) != 6 or len(set(folded)) != 6 or formats != list(EXPECTED_FORMATS):
        raise ValidationFailure("record_collision")
    rights_ids = sorted(str(item.get("rights_id")) for item in rights)
    if (
        rights_ids != ["cisa-kev-cc0-1.0", "nasa-ntrs-public-use"]
        or sorted({str(item.get("rights_id")) for item in assets}) != rights_ids
    ):
        raise ValidationFailure("rights_mapping")
    if any(
        item.get("review_assertion") != "human_review_required_not_legal_advice"
        or urlparse(str(item.get("evidence_url"))).scheme != "https"
        for item in rights
    ):
        raise ValidationFailure("rights_record")

    expected = set(CONTROL_FILES) | set(paths) | set(evidence_paths)
    _tree(corpus, expected)
    total = 0
    for item in (*assets, *evidence):
        expected_digest = _sha(item.get("sha256"))
        expected_length = _positive(item.get("byte_length"))
        digest, length = _sha_file(corpus / str(item["path"]))
        if digest != expected_digest or length != expected_length:
            raise ValidationFailure("byte_mismatch")
        if item in assets:
            total += length
            _payload_shape(corpus / str(item["path"]), str(item["format"]))
    if total != lock.get("aggregate_payload_bytes") or total > 16_777_216:
        raise ValidationFailure("aggregate")
    schema = _load_json(corpus / "corpus-lock.schema.json")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValidationFailure("schema")
    _metadata(corpus, assets)
    return declared_id, len(assets), total


def main() -> int:
    """Validate one selected corpus and emit only stable body-free status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    arguments = parser.parse_args()
    try:
        corpus_id, count, size = validate(arguments.corpus)
    except (OSError, ValidationFailure, ValueError):
        print("corpus_invalid")
        return 6
    print(f"corpus_id={corpus_id} payloads={count} bytes={size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
