from uuid import uuid4

import pytest

from openardp.domain.models import (
    BlockKind,
    ContentBlock,
    SourceLocation,
)


def test_block_requires_content() -> None:
    with pytest.raises(ValueError):
        ContentBlock(
            document_id=uuid4(),
            version_id="sha256:" + "0" * 64,
            kind=BlockKind.PARAGRAPH,
            order=0,
            canonical_hash="sha256:" + "1" * 64,
            source=SourceLocation(extraction_method="test"),
        )
