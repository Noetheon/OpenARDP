"""Explicitly reproduce the frozen F024 corpus from reviewed publishers."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from realworld_corpus import DEFAULT_CORPUS, CorpusError, reproduce_corpus


def main() -> int:
    """Fetch, verify and atomically publish one absent external corpus root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    started = time.monotonic_ns()
    try:
        result = reproduce_corpus(arguments.template, arguments.destination)
    except FileExistsError:
        print("corpus_destination_conflict")
        return 8
    except (CorpusError, OSError):
        print("corpus_reproduction_failed")
        return 6
    print(
        f"corpus_id={result.corpus_id} payloads={result.payload_count} "
        f"bytes={result.payload_bytes} duration_ns={time.monotonic_ns() - started}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
