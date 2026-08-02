"""Closed offline verification and explicit reproduction for the F024 corpus."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import unicodedata
import urllib.request
import zipfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from openardp.domain.identity import canonical_sha256

CORPUS_VERSION = "0.1.0"
DEFAULT_CORPUS = Path(__file__).parents[1] / "corpora/realworld/v0.1.0"
_LOCK_NAME = "corpus-lock.json"
_CONTROL_FILES = frozenset(
    {"README.md", "THIRD_PARTY_NOTICES.md", _LOCK_NAME, "corpus-lock.schema.json"}
)
_LOCK_FIELDS = frozenset(
    {
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
)
_ASSET_FIELDS = frozenset(
    {
        "authors",
        "byte_length",
        "expected_content_types",
        "format",
        "key",
        "media_type",
        "path",
        "publication_date",
        "publisher",
        "rights_id",
        "sha256",
        "source_record_url",
        "source_revision",
        "source_url",
        "title",
    }
)
_RIGHTS_FIELDS = frozenset(
    {
        "basis",
        "evidence_url",
        "notice",
        "publisher",
        "restrictions",
        "review_assertion",
        "rights_id",
    }
)
_EVIDENCE_FIELDS = frozenset({"byte_length", "media_type", "path", "sha256"})
_SHA_PREFIX = "sha256:"


class CorpusError(ValueError):
    """One stable body-free corpus failure category."""


@dataclass(frozen=True, slots=True)
class CorpusVerification:
    """Body-free facts for one completely verified corpus tree."""

    corpus_id: str
    formats: tuple[str, ...]
    payload_bytes: int
    payload_count: int
    rights_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DownloadStream:
    """One connected response reduced to reviewable authority and bounded chunks."""

    chunks: Iterable[bytes]
    content_type: str
    final_url: str


Fetch = Callable[[str], DownloadStream]


def _closed_json(payload: bytes) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise CorpusError("duplicate_json_key")
            value[key] = item
        return value

    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(CorpusError("json_value")),
        )
    except CorpusError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CorpusError("json_invalid") from error


def _mapping(value: Any, category: str = "lock_shape") -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CorpusError(category)
    return value


def _sequence(value: Any, category: str = "lock_shape") -> list[Any]:
    if not isinstance(value, list):
        raise CorpusError(category)
    return value


def _text(value: Any, category: str = "lock_shape") -> str:
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        raise CorpusError(category)
    return value


def _positive_int(value: Any, category: str = "lock_shape") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CorpusError(category)
    return value


def _sha256(value: Any, category: str = "lock_shape") -> str:
    text = _text(value, category)
    if len(text) != 71 or not text.startswith(_SHA_PREFIX):
        raise CorpusError(category)
    try:
        int(text.removeprefix(_SHA_PREFIX), 16)
    except ValueError as error:
        raise CorpusError(category) from error
    return text


def _relative_path(value: Any, prefix: str) -> str:
    text = _text(value, "lock_path")
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or path.as_posix() != text
        or "\\" in text
        or any(part in {"", ".", ".."} for part in text.split("/"))
        or not text.startswith(prefix)
    ):
        raise CorpusError("lock_path")
    return text


def _https_url(value: Any, category: str = "lock_url") -> str:
    text = _text(value, category)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise CorpusError(category)
    return text


def load_corpus_lock(corpus_root: Path = DEFAULT_CORPUS) -> dict[str, Any]:
    """Load one duplicate-key-safe corpus lock without accessing any provider."""
    path = corpus_root / _LOCK_NAME
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_048_576:
        raise CorpusError("lock_file")
    return _mapping(_closed_json(path.read_bytes()))


def corpus_identity(lock: Mapping[str, Any]) -> str:
    """Return the RFC 8785/SHA-256 identity excluding the declared self field."""
    projection = dict(lock)
    projection.pop("corpus_id", None)
    try:
        return canonical_sha256(projection)
    except (TypeError, ValueError) as error:
        raise CorpusError("identity") from error


def _validate_lock(lock: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if set(lock) != _LOCK_FIELDS:
        raise CorpusError("lock_fields")
    if (
        lock.get("schema_version") != CORPUS_VERSION
        or lock.get("corpus_version") != CORPUS_VERSION
        or lock.get("corpus_name") != "openardp-realworld"
        or lock.get("payload_root") != "sources"
    ):
        raise CorpusError("lock_version")
    if _sha256(lock.get("corpus_id"), "identity") != corpus_identity(lock):
        raise CorpusError("identity")

    assets = [_mapping(item) for item in _sequence(lock.get("assets"))]
    if len(assets) != 6:
        raise CorpusError("lock_count")
    for asset in assets:
        if set(asset) != _ASSET_FIELDS:
            raise CorpusError("asset_fields")
        _relative_path(asset.get("path"), "sources/")
        _sha256(asset.get("sha256"))
        _positive_int(asset.get("byte_length"))
        _text(asset.get("key"))
        _text(asset.get("format"))
        _text(asset.get("media_type"))
        _text(asset.get("title"))
        _text(asset.get("publisher"))
        _text(asset.get("publication_date"))
        _text(asset.get("source_revision"))
        _text(asset.get("rights_id"))
        _https_url(asset.get("source_url"))
        _https_url(asset.get("source_record_url"))
        authors = _sequence(asset.get("authors"))
        types = _sequence(asset.get("expected_content_types"))
        if not authors or not types:
            raise CorpusError("asset_fields")
        for value in (*authors, *types):
            _text(value, "asset_fields")

    paths = [str(asset["path"]) for asset in assets]
    keys = [str(asset["key"]) for asset in assets]
    if paths != sorted(paths) or keys != sorted(keys):
        raise CorpusError("lock_order")
    if len(set(paths)) != len(paths) or len(set(keys)) != len(keys):
        raise CorpusError("lock_duplicate")
    normalized = [unicodedata.normalize("NFC", value).casefold() for value in paths]
    if len(normalized) != len(set(normalized)):
        raise CorpusError("path_collision")
    formats = sorted(str(asset["format"]) for asset in assets)
    required_formats = _sequence(lock.get("required_formats"))
    if formats != ["csv", "docx", "md", "pdf", "pptx", "txt"] or required_formats != formats:
        raise CorpusError("format_coverage")
    if lock.get("aggregate_payload_bytes") != sum(int(item["byte_length"]) for item in assets):
        raise CorpusError("aggregate_bytes")

    rights = [_mapping(item) for item in _sequence(lock.get("rights"))]
    for record in rights:
        if set(record) != _RIGHTS_FIELDS:
            raise CorpusError("rights_fields")
        _https_url(record.get("evidence_url"), "rights_fields")
        if record.get("review_assertion") != "human_review_required_not_legal_advice":
            raise CorpusError("rights_fields")
        for field in ("basis", "notice", "publisher", "rights_id"):
            _text(record.get(field), "rights_fields")
        restrictions = _sequence(record.get("restrictions"), "rights_fields")
        if not restrictions:
            raise CorpusError("rights_fields")
        for value in restrictions:
            _text(value, "rights_fields")
    rights_ids = [str(item["rights_id"]) for item in rights]
    if rights_ids != sorted(rights_ids) or len(rights_ids) != len(set(rights_ids)):
        raise CorpusError("rights_order")
    if sorted({str(asset["rights_id"]) for asset in assets}) != rights_ids:
        raise CorpusError("rights_mapping")

    evidence = [_mapping(item) for item in _sequence(lock.get("evidence_files"))]
    if len(evidence) != 4:
        raise CorpusError("evidence_mapping")
    for record in evidence:
        if set(record) != _EVIDENCE_FIELDS or record.get("media_type") != "application/json":
            raise CorpusError("evidence_fields")
        _relative_path(record.get("path"), "evidence/")
        _sha256(record.get("sha256"))
        _positive_int(record.get("byte_length"))
    evidence_paths = [str(item["path"]) for item in evidence]
    if evidence_paths != sorted(evidence_paths) or len(set(evidence_paths)) != len(evidence_paths):
        raise CorpusError("evidence_order")

    extensions = _mapping(lock.get("extensions"))
    if set(extensions) != {"https://openardp.org/ns/corpus/reproduction-v1"}:
        raise CorpusError("extensions")
    reproduction = _mapping(extensions["https://openardp.org/ns/corpus/reproduction-v1"])
    if set(reproduction) != {
        "allowed_hosts",
        "maximum_aggregate_bytes",
        "maximum_file_bytes",
        "redirect_hosts",
    }:
        raise CorpusError("extensions")
    for key in ("allowed_hosts", "redirect_hosts"):
        hosts = _sequence(reproduction.get(key), "extensions")
        if hosts != sorted(set(hosts)) or not hosts:
            raise CorpusError("extensions")
        for host in hosts:
            _text(host, "extensions")
    _positive_int(reproduction.get("maximum_aggregate_bytes"), "extensions")
    _positive_int(reproduction.get("maximum_file_bytes"), "extensions")
    allowed = set(reproduction["allowed_hosts"])
    if any(urlparse(str(asset["source_url"])).hostname not in allowed for asset in assets):
        raise CorpusError("source_host")
    return assets, evidence


def _walk_closed_tree(root: Path, expected_files: set[str]) -> None:
    if root.is_symlink() or not root.is_dir():
        raise CorpusError("unsafe_tree")
    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    for entry in root.rglob("*"):
        relative = entry.relative_to(root).as_posix()
        metadata = entry.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise CorpusError("unsafe_tree")
        if stat.S_ISDIR(metadata.st_mode):
            observed_directories.add(relative)
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise CorpusError("unsafe_tree")
        observed_files.add(relative)
    if observed_directories != {"evidence", "sources"} or observed_files != expected_files:
        raise CorpusError("tree_inventory")


def _digest_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1_048_576):
            digest.update(chunk)
            length += len(chunk)
    return _SHA_PREFIX + digest.hexdigest(), length


def _verify_payload_shape(path: Path, format_name: str) -> None:
    if format_name == "pdf":
        with path.open("rb") as handle:
            if not handle.read(5).startswith(b"%PDF-"):
                raise CorpusError("payload_format")
    elif format_name in {"docx", "pptx"}:
        if not zipfile.is_zipfile(path):
            raise CorpusError("payload_format")
        required = "word/document.xml" if format_name == "docx" else "ppt/presentation.xml"
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
        except (OSError, zipfile.BadZipFile) as error:
            raise CorpusError("payload_format") from error
        if required not in names or any(
            name.casefold().endswith("vbaproject.bin") for name in names
        ):
            raise CorpusError("payload_format")
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise CorpusError("payload_format") from error
        if "\x00" in text:
            raise CorpusError("payload_format")


def _verify_evidence(root: Path, assets: list[dict[str, Any]]) -> None:
    cisa = _mapping(_closed_json((root / "evidence/cisa-kev-revision.json").read_bytes()))
    cisa_assets = [item for item in assets if str(item["source_revision"]).startswith("564b")]
    if (
        cisa.get("commit") != "564b8c59f9039926e2d9548ba5b334db45cb6b50"
        or cisa.get("license") != "CC0-1.0"
        or len(cisa_assets) != 3
    ):
        raise CorpusError("evidence_mapping")
    cisa_files = {
        str(_mapping(item).get("path")): _mapping(item)
        for item in _sequence(cisa.get("files"), "evidence_mapping")
    }
    expected_upstream = {Path(str(item["source_url"])).name: item for item in cisa_assets}
    if set(cisa_files) != set(expected_upstream):
        raise CorpusError("evidence_mapping")
    if any(
        _positive_int(cisa_files[name].get("size"), "evidence_mapping")
        != int(expected_upstream[name]["byte_length"])
        for name in cisa_files
    ):
        raise CorpusError("evidence_mapping")

    nasa_assets = [item for item in assets if str(item["source_revision"]).startswith("NTRS:")]
    if len(nasa_assets) != 3:
        raise CorpusError("evidence_mapping")
    for asset in nasa_assets:
        ntrs_id = str(asset["source_revision"]).removeprefix("NTRS:")
        snapshot = _mapping(
            _closed_json((root / f"evidence/nasa-ntrs-{ntrs_id}.json").read_bytes())
        )
        copyright_value = _mapping(snapshot.get("copyright"), "evidence_mapping")
        download = _mapping(snapshot.get("download"), "evidence_mapping")
        if (
            snapshot.get("ntrs_id") != ntrs_id
            or snapshot.get("title") != asset["title"]
            or snapshot.get("record_url") != asset["source_record_url"]
            or download.get("url") != asset["source_url"]
            or download.get("media_type") != asset["media_type"]
            or download.get("draft") is not False
            or copyright_value.get("determination_type")
            not in {"PUBLIC_USE_PERMITTED", "GOV_PUBLIC_USE_PERMITTED"}
            or copyright_value.get("contains_third_party_material") is not False
        ):
            raise CorpusError("evidence_mapping")


def verify_corpus(corpus_root: Path = DEFAULT_CORPUS) -> CorpusVerification:
    """Verify the complete closed corpus tree without network or parser imports."""
    root = corpus_root.absolute()
    lock = load_corpus_lock(root)
    assets, evidence = _validate_lock(lock)
    expected_files = set(_CONTROL_FILES)
    expected_files.update(str(item["path"]) for item in assets)
    expected_files.update(str(item["path"]) for item in evidence)
    _walk_closed_tree(root, expected_files)
    total = 0
    for record in (*assets, *evidence):
        path = root / str(record["path"])
        digest, length = _digest_file(path)
        if digest != record["sha256"] or length != record["byte_length"]:
            raise CorpusError("byte_mismatch")
        if record in assets:
            total += length
            _verify_payload_shape(path, str(record["format"]))
    if total != lock["aggregate_payload_bytes"]:
        raise CorpusError("aggregate_bytes")
    schema = _mapping(_closed_json((root / "corpus-lock.schema.json").read_bytes()))
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise CorpusError("schema")
    _verify_evidence(root, assets)
    return CorpusVerification(
        corpus_id=str(lock["corpus_id"]),
        formats=tuple(sorted(str(item["format"]) for item in assets)),
        payload_bytes=total,
        payload_count=len(assets),
        rights_ids=tuple(sorted(str(item["rights_id"]) for item in _sequence(lock["rights"]))),
    )


class _ReviewedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts: frozenset[str]) -> None:
        self._hosts = hosts

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> urllib.request.Request | None:
        parsed = urlparse(newurl)
        if parsed.scheme != "https":
            raise CorpusError("redirect_scheme")
        if parsed.hostname not in self._hosts:
            raise CorpusError("redirect_host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _network_fetcher(redirect_hosts: frozenset[str]) -> Fetch:
    opener = urllib.request.build_opener(_ReviewedRedirectHandler(redirect_hosts))

    def fetch(url: str) -> DownloadStream:
        _https_url(url, "source_url")
        request = urllib.request.Request(  # noqa: S310 - HTTPS was validated above.
            url,
            headers={"User-Agent": "OpenARDP-F024/0.1.0"},
        )
        try:
            response = opener.open(request, timeout=60.0)
        except CorpusError:
            raise
        except OSError as error:
            raise CorpusError("transport") from error

        def chunks() -> Iterable[bytes]:
            with response:
                while chunk := response.read(1_048_576):
                    yield chunk

        return DownloadStream(
            chunks=chunks(),
            content_type=response.headers.get_content_type(),
            final_url=response.geturl(),
        )

    return fetch


def _atomic_write(path: Path, chunks: Iterable[bytes], *, maximum: int) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    length = 0
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as file:
        temporary = Path(file.name)
        try:
            for chunk in chunks:
                if not isinstance(chunk, bytes) or not chunk:
                    raise CorpusError("response_chunk")
                length += len(chunk)
                if length > maximum:
                    raise CorpusError("response_size")
                digest.update(chunk)
                file.write(chunk)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, path)
    return _SHA_PREFIX + digest.hexdigest(), length


def reproduce_corpus(
    template_root: Path,
    destination: Path,
    *,
    fetcher: Fetch | None = None,
) -> CorpusVerification:
    """Fetch exact reviewed payloads and atomically publish one fresh verified tree."""
    template = template_root.resolve(strict=True)
    template_result = verify_corpus(template)
    lock = load_corpus_lock(template)
    assets, evidence = _validate_lock(lock)
    target = destination.absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise FileExistsError("corpus destination already exists")
    reproduction = _mapping(
        _mapping(lock["extensions"])["https://openardp.org/ns/corpus/reproduction-v1"]
    )
    redirect_hosts = frozenset(str(item) for item in _sequence(reproduction["redirect_hosts"]))
    selected_fetcher = fetcher or _network_fetcher(redirect_hosts)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-stage-", dir=target.parent))
    try:
        for relative in sorted(_CONTROL_FILES):
            payload = (template / relative).read_bytes()
            _atomic_write(stage / relative, (payload,), maximum=1_048_576)
        for record in evidence:
            payload = (template / str(record["path"])).read_bytes()
            _atomic_write(stage / str(record["path"]), (payload,), maximum=1_048_576)

        aggregate = 0
        maximum_file = int(reproduction["maximum_file_bytes"])
        maximum_aggregate = int(reproduction["maximum_aggregate_bytes"])
        for asset in assets:
            source_url = str(asset["source_url"])
            response = selected_fetcher(source_url)
            parsed = urlparse(response.final_url)
            if parsed.scheme != "https":
                raise CorpusError("redirect_scheme")
            if parsed.hostname not in redirect_hosts:
                raise CorpusError("redirect_host")
            content_type = response.content_type.partition(";")[0].strip().lower()
            expected_types = {str(item).lower() for item in asset["expected_content_types"]}
            if content_type not in expected_types:
                raise CorpusError("response_type")
            digest, length = _atomic_write(
                stage / str(asset["path"]),
                response.chunks,
                maximum=maximum_file,
            )
            aggregate += length
            if aggregate > maximum_aggregate:
                raise CorpusError("response_aggregate_size")
            if digest != asset["sha256"] or length != asset["byte_length"]:
                raise CorpusError("response_identity")

        result = verify_corpus(stage)
        if result != template_result:
            raise CorpusError("reproduction_mismatch")
        if target.exists() or target.is_symlink():
            raise FileExistsError("corpus destination already exists")
        os.replace(stage, target)
        return result
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


__all__ = [
    "CORPUS_VERSION",
    "DEFAULT_CORPUS",
    "CorpusError",
    "CorpusVerification",
    "DownloadStream",
    "corpus_identity",
    "load_corpus_lock",
    "reproduce_corpus",
    "verify_corpus",
]
