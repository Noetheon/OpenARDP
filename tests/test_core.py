from io import BytesIO

import pytest

from openardp.core import canonical_json_bytes, safe_chunks, stream_sha256


def test_canonical_json_is_key_order_independent() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == canonical_json_bytes({"a": 1, "b": 2})


def test_stream_hash_and_length() -> None:
    digest, length = stream_sha256(BytesIO(b"openardp"))
    assert digest == "aa042604a10712971ee646737e4b054e49e13a4c5c947e869945a71d61fb9f86"
    assert length == 8


def test_safe_chunks_rejects_invalid_size() -> None:
    with pytest.raises(ValueError):
        list(safe_chunks("text", 0))
