"""Independently validate one body-free F028 CSV benchmark result."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
QUESTIONS = ("Q15", "Q16")
SOURCE_KEY = "cisa-known-exploited-vulnerabilities"
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_KEYS = {"body", "content", "hostname", "path", "query", "question", "username"}
TOP_FIELDS = {
    "benchmark_version",
    "corpus_id",
    "csv",
    "decision",
    "gates",
    "protocol_id",
    "question_ids",
    "question_set_id",
    "result_id",
    "rows",
}


class ValidationFailure(ValueError):
    """Stable independent F028 validation failure."""


def _load(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4_194_304:
        raise ValidationFailure("json_file")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValidationFailure("json_duplicate")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValidationFailure("json_shape")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _identity(value: Any, identity: Any) -> None:
    expected = "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()
    if not isinstance(identity, str) or SHA.fullmatch(identity) is None or identity != expected:
        raise ValidationFailure("identity")


def _source_facts(repository_root: Path) -> tuple[str, str, str, int, int, int]:
    source = (
        repository_root
        / "corpora/realworld/v0.1.0/sources/cisa-known-exploited-vulnerabilities.csv"
    )
    payload = source.read_bytes()
    reader = csv.reader(io.StringIO(payload.decode("utf-8-sig"), newline=""), strict=True)
    header: list[str] | None = None
    projections: list[dict[str, Any]] = []
    ranges: list[list[int]] = []
    prior_line = 0
    cell_count = 0
    for record_number, row in enumerate(reader, start=1):
        cell_count += len(row)
        ranges.append([prior_line + 1, reader.line_num])
        prior_line = reader.line_num
        if header is None:
            header = list(row)
            projections.append({"header": header, "record": record_number, "type": "csv_header"})
        else:
            projections.append(
                {
                    "fields": [
                        [header[index] if index < len(header) else None, value]
                        for index, value in enumerate(row)
                    ],
                    "record": record_number,
                    "type": "csv_record",
                }
            )
    return (
        "sha256:" + hashlib.sha256(payload).hexdigest(),
        "sha256:" + hashlib.sha256(_canonical(projections)).hexdigest(),
        "sha256:" + hashlib.sha256(_canonical(ranges)).hexdigest(),
        len(payload),
        len(projections),
        cell_count,
    )


def _privacy(value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            _privacy(item)
    elif isinstance(value, dict):
        if FORBIDDEN_KEYS & set(value):
            raise ValidationFailure("privacy")
        for item in value.values():
            _privacy(item)


def validate(result_root: Path, repository_root: Path) -> str:
    """Recompute frozen-source facts, gates, identity, privacy and decision."""
    result = _load(result_root / "result.json")
    if set(result) != TOP_FIELDS or result.get("benchmark_version") != VERSION:
        raise ValidationFailure("fields")
    projection = dict(result)
    result_id = projection.pop("result_id", None)
    _identity(projection, result_id)
    if result.get("question_ids") != list(QUESTIONS):
        raise ValidationFailure("question_coverage")
    csv_facts = result.get("csv")
    if not isinstance(csv_facts, dict):
        raise ValidationFailure("csv_facts")
    source_id, table_id, ranges_id, byte_length, record_count, cell_count = _source_facts(
        repository_root
    )
    if (
        csv_facts.get("source_id") != source_id
        or csv_facts.get("native_id") != source_id
        or csv_facts.get("source_table_id") != table_id
        or csv_facts.get("product_table_id") != table_id
        or csv_facts.get("source_line_ranges_id") != ranges_id
        or csv_facts.get("product_line_ranges_id") != ranges_id
        or csv_facts.get("native_bytes") != byte_length
        or csv_facts.get("record_count") != record_count
        or csv_facts.get("block_count") != record_count
        or csv_facts.get("cell_count") != cell_count
    ):
        raise ValidationFailure("source_facts")
    rows = result.get("rows")
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValidationFailure("rows")
    keys = [(row.get("question_id"), row.get("treatment")) for row in rows]
    if keys != [
        ("Q15", "openardp_direct"),
        ("Q15", "openardp_operator"),
        ("Q16", "openardp_direct"),
        ("Q16", "openardp_operator"),
    ]:
        raise ValidationFailure("row_coverage")
    operator = {
        str(row["question_id"]): row for row in rows if row["treatment"] == "openardp_operator"
    }
    gates = {
        "cache_reused": csv_facts.get("cache_hit") is True,
        "citation_integrity_complete": all(
            row.get("citation_integrity_complete") is True for row in operator.values()
        ),
        "logical_records_complete": csv_facts.get("logical_records_complete") is True,
        "native_source_exact": csv_facts.get("native_matches_source") is True,
        "operator_support_complete": all(
            row.get("full_support") is True for row in operator.values()
        ),
        "physical_line_provenance_complete": True,
        "realworld_record_coverage": record_count == 1_656,
        "required_source_complete": all(
            row.get("covered_source_keys") == [SOURCE_KEY] for row in operator.values()
        ),
        "semantic_runs_identical": result.get("gates", {}).get("semantic_runs_identical") is True,
        "stable_product_outcomes": all(row.get("outcome") == "pass" for row in rows),
    }
    if result.get("gates") != gates:
        raise ValidationFailure("gates")
    decision = "CSV_INGESTION_READY" if all(gates.values()) else "CSV_INGESTION_NOT_READY"
    if result.get("decision") != decision:
        raise ValidationFailure("decision")
    _privacy(result)
    report = (result_root / "report.md").read_text(encoding="utf-8")
    if decision not in report:
        raise ValidationFailure("report")
    return decision


def main() -> int:
    """Parse explicit paths and emit one stable validation category."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.result, arguments.repository_root)
    except (OSError, ValueError, ZeroDivisionError):
        print("csv_ingestion_benchmark_invalid")
        return 6
    print(f"csv_ingestion_benchmark_valid decision={decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
