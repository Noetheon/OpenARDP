"""Spawned-process and strict IPC tests for the F007 rich adapter."""

from __future__ import annotations

import multiprocessing
import os
import socket
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from openardp.adapters.isolated_docling import (
    _SINGLE_THREAD_ENVIRONMENT,
    IsolatedDoclingAdapter,
    _apply_offline_environment,
    _apply_resource_limits,
    _apply_thread_environment,
    _decode_worker_result,
    _error_from_code,
    _memory_limit_resource,
    _parser_error_code,
    _WorkerConfig,
)
from openardp.domain.rich_ingestion import (
    ComponentVersion,
    RichMediaType,
    RichParseOutput,
    RichParserLimits,
)
from openardp.ports.parser import (
    InvalidRichParserOutput,
    ParserError,
    ParserProcessCrashed,
    ParserTimedOut,
    RichParserCancelled,
    RichParserDependencyUnavailable,
    RichParserMalformedDocument,
    RichParserModelAssetsInvalid,
    RichParserModelAssetsRequired,
    RichParserNetworkDenied,
    RichParserPartialConversion,
    RichParserResourceLimitExceeded,
    UnsupportedRichMedia,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "rich"


def test_offline_environment_uses_one_fresh_explicit_cache_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect provider caches and force offline mode before provider import."""
    for name in (
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "HF_HOME",
        "HF_HUB_CACHE",
        "TRANSFORMERS_CACHE",
        "XDG_CACHE_HOME",
    ):
        monkeypatch.delenv(name, raising=False)

    _apply_offline_environment(tmp_path)

    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
    for name in ("HF_HOME", "HF_HUB_CACHE", "TRANSFORMERS_CACHE", "XDG_CACHE_HOME"):
        assert Path(os.environ[name]).is_relative_to(tmp_path)


def test_thread_environment_pins_every_numeric_pool_to_one_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep worker memory independent of the host core count before provider import."""
    for name in _SINGLE_THREAD_ENVIRONMENT:
        monkeypatch.setenv(name, "64")

    _apply_thread_environment()

    assert {name: os.environ[name] for name in _SINGLE_THREAD_ENVIRONMENT} == dict.fromkeys(
        _SINGLE_THREAD_ENVIRONMENT, "1"
    )
    assert {"OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"} <= set(
        _SINGLE_THREAD_ENVIRONMENT
    )


class _ResourceStub:
    RLIMIT_AS = 9
    RLIMIT_DATA = 2


class _AddressOnlyStub:
    RLIMIT_AS = 9


def test_memory_limit_bounds_writable_memory_on_linux_and_address_space_elsewhere() -> None:
    """Select RLIMIT_DATA on Linux, RLIMIT_AS on other POSIX and nothing when unsupported."""
    assert _memory_limit_resource(_ResourceStub(), "linux") == _ResourceStub.RLIMIT_DATA
    assert _memory_limit_resource(_AddressOnlyStub(), "linux") == _AddressOnlyStub.RLIMIT_AS
    assert _memory_limit_resource(_ResourceStub(), "darwin") == _ResourceStub.RLIMIT_AS
    assert _memory_limit_resource(object(), "linux") is None


@pytest.mark.skipif(os.name == "nt", reason="POSIX resource limits are not applied on Windows")
def test_resource_limits_apply_the_platform_memory_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply CPU, descriptor and exactly one memory limit without raising hard limits."""
    import resource

    applied: dict[int, tuple[int, int]] = {}
    monkeypatch.setattr(resource, "getrlimit", lambda kind: (0, resource.RLIM_INFINITY))
    monkeypatch.setattr(resource, "setrlimit", lambda kind, value: applied.__setitem__(kind, value))
    limits = RichParserLimits(max_address_space_bytes=123_456_789)
    config = _WorkerConfig(
        limits_json=limits.model_dump_json(),
        model_root=None,
        model_manifest_json=None,
    )

    _apply_resource_limits(config, 2.5)

    memory = _memory_limit_resource(resource, sys.platform)
    assert memory is not None
    assert applied[memory] == (123_456_789, resource.RLIM_INFINITY)
    assert applied[resource.RLIMIT_CPU] == (4, resource.RLIM_INFINITY)
    assert applied[resource.RLIMIT_NOFILE] == (limits.max_open_files, resource.RLIM_INFINITY)
    if sys.platform.startswith("linux"):
        assert resource.RLIMIT_AS not in applied


def _network_probe(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    try:
        socket.socket()
    except RuntimeError:
        result_sender.send(("error", "network_denied"))  # type: ignore[attr-defined]
        return
    result_sender.send(("error", "worker_failed"))  # type: ignore[attr-defined]


def _malformed_result(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    result_sender.send(("ok", '{"secret-body":true}'))  # type: ignore[attr-defined]


def _valid_result(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    while True:
        message = input_receiver.recv()  # type: ignore[attr-defined]
        if message[0] == "end":
            break
    result = RichParseOutput(
        media_type=RichMediaType.DOCX,
        native_document={"schema_name": "DoclingDocument"},
        candidates=(),
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
    )
    result_sender.send(("ok", result.model_dump_json()))  # type: ignore[attr-defined]


def _hanging_worker(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    time.sleep(5)


def _crashing_worker(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    os._exit(19)


def _closed_result_worker(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    result_sender.close()  # type: ignore[attr-defined]


def _secret_error_worker(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    raise RuntimeError("/private/secret.docx secret-body provider traceback")


def _instant_valid_result(
    input_receiver: object,
    result_sender: object,
    config: object,
) -> None:
    result = RichParseOutput(
        media_type=RichMediaType.DOCX,
        native_document={"schema_name": "DoclingDocument"},
        candidates=(),
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
    )
    result_sender.send(("ok", result.model_dump_json()))  # type: ignore[attr-defined]


def _failing_chunks() -> Iterator[bytes]:
    yield b"first"
    raise RuntimeError("/private/secret.docx secret-body")


def test_spawned_adapter_converts_bytes_and_reaps_its_child() -> None:
    """Use spawn, return strict output and leave no parser process behind."""
    before = {process.pid for process in multiprocessing.active_children()}
    adapter = IsolatedDoclingAdapter(
        limits=RichParserLimits(timeout_seconds=30.0),
        _worker_behavior=_valid_result,
    )
    output = adapter.parse(
        ((FIXTURES / "synthetic.docx").read_bytes(),),
        media_type=RichMediaType.DOCX.value,
    )
    after = {process.pid for process in multiprocessing.active_children()}

    assert output.native_document == {"schema_name": "DoclingDocument"}
    assert adapter.recipe.provider.version == "2.114.0"
    assert after == before


def test_isolated_adapter_denies_network_before_selected_worker_behavior() -> None:
    """Prove socket denial is active before provider-side behavior executes."""
    adapter = IsolatedDoclingAdapter(_worker_behavior=_network_probe)
    with pytest.raises(RichParserNetworkDenied, match="network denied"):
        adapter.parse((), media_type=RichMediaType.DOCX.value)


def test_isolated_adapter_rejects_media_and_malformed_body_without_reflection() -> None:
    """Keep unsupported and malformed worker results typed and body-free."""
    adapter = IsolatedDoclingAdapter()
    with pytest.raises(UnsupportedRichMedia, match="unsupported rich media"):
        adapter.parse((), media_type="text/html")

    malformed = IsolatedDoclingAdapter(_worker_behavior=_malformed_result)
    with pytest.raises(InvalidRichParserOutput, match="output invalid") as error:
        malformed.parse((), media_type=RichMediaType.DOCX.value)
    assert "secret-body" not in str(error.value)


def test_isolated_adapter_times_out_crashes_and_enforces_source_limit() -> None:
    """Terminate hostile workers and classify bounded source overflow without bodies."""
    before = {process.pid for process in multiprocessing.active_children()}
    started = time.monotonic()
    timeout = IsolatedDoclingAdapter(
        limits=RichParserLimits(timeout_seconds=0.05),
        _worker_behavior=_hanging_worker,
    )
    with pytest.raises(ParserTimedOut, match="timed out"):
        timeout.parse((), media_type=RichMediaType.DOCX.value)
    assert time.monotonic() - started < 5.0

    crash = IsolatedDoclingAdapter(_worker_behavior=_crashing_worker)
    with pytest.raises(ParserProcessCrashed, match="crashed"):
        crash.parse((), media_type=RichMediaType.DOCX.value)

    bounded = IsolatedDoclingAdapter(
        limits=RichParserLimits(max_source_bytes=1),
    )
    with pytest.raises(RichParserResourceLimitExceeded, match="limit"):
        bounded.parse((b"secret-body",), media_type=RichMediaType.DOCX.value)
    assert {process.pid for process in multiprocessing.active_children()} == before


def test_ipc_close_input_failure_cancellation_and_worker_details_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Classify every parent/child interruption and retain no secret diagnostic text."""
    before = {process.pid for process in multiprocessing.active_children()}
    closed = IsolatedDoclingAdapter(_worker_behavior=_closed_result_worker)
    with pytest.raises(ParserProcessCrashed, match="crashed"):
        closed.parse((), media_type=RichMediaType.DOCX.value)

    secret = IsolatedDoclingAdapter(_worker_behavior=_secret_error_worker)
    with pytest.raises(ParserProcessCrashed, match="crashed") as secret_error:
        secret.parse((), media_type=RichMediaType.DOCX.value)
    assert "secret" not in str(secret_error.value)
    assert "private" not in str(secret_error.value)

    input_failure = IsolatedDoclingAdapter(_worker_behavior=_instant_valid_result)
    with pytest.raises(ParserProcessCrashed, match="input stream failed") as input_error:
        input_failure.parse(
            _failing_chunks(),
            media_type=RichMediaType.DOCX.value,
        )
    assert "secret" not in str(input_error.value)

    cancelled = IsolatedDoclingAdapter(_worker_behavior=_instant_valid_result)
    monkeypatch.setattr(
        "openardp.adapters.isolated_docling._decode_worker_result",
        lambda _message: (_ for _ in ()).throw(KeyboardInterrupt),
    )
    with pytest.raises(RichParserCancelled, match="cancelled"):
        cancelled.parse((), media_type=RichMediaType.DOCX.value)
    assert {process.pid for process in multiprocessing.active_children()} == before


@pytest.mark.parametrize(
    ("code", "error_type"),
    (
        ("unsupported_media", UnsupportedRichMedia),
        ("dependency_unavailable", RichParserDependencyUnavailable),
        ("model_assets_required", RichParserModelAssetsRequired),
        ("model_assets_invalid", RichParserModelAssetsInvalid),
        ("malformed_document", RichParserMalformedDocument),
        ("partial_conversion", RichParserPartialConversion),
        ("network_denied", RichParserNetworkDenied),
        ("resource_limit", RichParserResourceLimitExceeded),
        ("cancelled", RichParserCancelled),
        ("invalid_output", InvalidRichParserOutput),
        ("worker_failed", ParserProcessCrashed),
    ),
)
def test_worker_error_codes_are_closed_and_sanitized(
    code: str,
    error_type: type[ParserError],
) -> None:
    """Round-trip every allowlisted worker category without provider exception text."""
    error = _error_from_code(code)
    assert isinstance(error, error_type)
    assert _parser_error_code(error) == code
    with pytest.raises(error_type):
        _decode_worker_result(("error", code))


@pytest.mark.parametrize(
    "message",
    (
        None,
        ("ok",),
        ("unknown", "{}"),
        ("ok", 1),
        ("error", "unknown_code"),
    ),
)
def test_worker_decoder_rejects_every_unreviewed_shape(message: object) -> None:
    """Fail closed on malformed tuples, types, result kinds and error codes."""
    with pytest.raises(InvalidRichParserOutput, match="output invalid"):
        _decode_worker_result(message)
