"""Generate or reproduce-check the exact F034 XQuAD holdout."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

try:
    from scripts.retrieval_holdout import HoldoutError, compare_generated, generate_holdout
except ModuleNotFoundError:
    from retrieval_holdout import HoldoutError, compare_generated, generate_holdout


def main() -> int:
    """Generate fresh inputs or compare them to the repository."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--upstream", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.check:
            with tempfile.TemporaryDirectory(prefix="openardp-f034-generate-") as temporary:
                generated = Path(temporary)
                verification = generate_holdout(arguments.upstream, generated)
                if not compare_generated(generated, arguments.repository_root.resolve(strict=True)):
                    print("holdout_drift_detected")
                    return 8
        else:
            assert arguments.output is not None
            verification = generate_holdout(arguments.upstream, arguments.output)
    except FileExistsError:
        print("holdout_output_conflict")
        return 8
    except HoldoutError as error:
        if str(error) in {"output_not_empty", "output_path"}:
            print("holdout_output_conflict")
            return 8
        print("holdout_input_rejected")
        return 4
    except (OSError, ValueError):
        print("holdout_input_rejected")
        return 4
    print(
        f"corpus_id={verification.corpus_id} question_set_id={verification.question_set_id} "
        f"sources={verification.source_count} questions={verification.question_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
