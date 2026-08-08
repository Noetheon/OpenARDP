"""Stable JSON and body-safe human renderers for OpenARDP CLI results."""

from __future__ import annotations

import json
import sys

from pydantic import BaseModel

from openardp.domain.common import SCHEMA_VERSION
from openardp.domain.maintenance import StorageOptimizationReport
from openardp.domain.search import SearchOutcome


def json_value(value: object) -> object:
    """Project supported result values into deterministic JSON-compatible values."""
    if isinstance(value, StorageOptimizationReport):
        payload = value.model_dump(mode="json")
        payload.update(
            {
                "completed_count": value.completed_count,
                "eligible_count": value.eligible_count,
                "failed_count": value.failed_count,
                "stored_bytes_saved": value.stored_bytes_saved,
            }
        )
        return payload
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    return value


def write_json(payload: dict[str, object]) -> None:
    """Write one compact deterministic JSON line."""
    sys.stdout.write(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    )


def success(command: str, data: object, *, json_output: bool) -> None:
    """Render one successful result through the stable JSON or human contract."""
    converted = json_value(data)
    if json_output:
        write_json(
            {
                "command": command,
                "data": converted,
                "ok": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
        return
    if _render_ingestion(command, data, converted):
        return
    if _render_retrieval(command, data, converted):
        return
    if _render_context(command, converted):
        return
    if _render_operations(command, converted):
        return
    print(json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True))


def _render_ingestion(command: str, data: object, converted: object) -> bool:
    del data
    if command == "init":
        item = _mapping(converted)
        print(f"Initialized OpenARDP workspace: {item['root']}")
    elif command == "ingest":
        item = _mapping(converted)
        scope = _mapping(item["scope"])
        detail = (
            f"{item['evidence_count']} evidence items"
            if "evidence_count" in item
            else f"{item['block_count']} blocks"
        )
        print(f"Ingested {scope['document_id']} ({item['disposition']}, {detail})")
    elif command == "list":
        for entry in _sequence(converted):
            record = _mapping(entry)
            source = _mapping(record["source_key"])
            print(
                f"{record['document_id']}\t{source['locator']}\t{record['state'] or 'UNPREPARED'}"
            )
    elif command == "status":
        item = _mapping(converted)
        print(f"{item['freshness']}\t{item['integrity_coverage']}")
    elif command == "outline":
        for entry in _sequence(converted):
            record = _mapping(entry)
            print(
                f"{'  ' * _depth(record['depth'])}{record['kind']}\t"
                f"{safe_text(str(record['label']))}"
            )
    else:
        return False
    return True


def _render_retrieval(command: str, data: object, converted: object) -> bool:
    if command == "search":
        assert isinstance(data, SearchOutcome)
        for hit in data.hits:
            print(
                f"{hit.scope.document_id}\t{hit.block_id}\t{hit.kind.value}\t"
                f"{hit.line_start}-{hit.line_end}\t{safe_text(hit.snippet)}"
            )
        print(f"returned={data.returned} available={data.available} truncated={data.truncated}")
    elif command == "reindex":
        scopes = _sequence(_mapping(converted)["scopes"])
        for item in scopes:
            record = _mapping(item)
            scope = _mapping(record["scope"])
            print(f"{scope['document_id']}\t{record['outcome']}\tentries={record['entry_count']}")
    elif command == "evidence":
        for entry in _sequence(converted):
            record = _mapping(entry)
            retrieval = _mapping(record["retrieval"])
            print(
                f"{record['evidence_projection_id']}\t"
                f"{retrieval['media_type']}\t{retrieval['byte_length']} bytes"
            )
    elif command == "get-evidence":
        item = _mapping(converted)
        projection = _mapping(item["projection"])
        print(f"{projection['evidence_projection_id']}\t{safe_text(str(item['body']))}")
    elif command in {"visual-materialize", "visual-evidence"}:
        item = _mapping(converted)
        crop = _mapping(item["crop_object"])
        policy = _mapping(item["usage_policy"])
        print(f"visual={item['visual_evidence_id']}")
        print(f"projection={item['evidence_projection_id']}")
        print(f"crop={crop['object_id']} ({crop['byte_length']} bytes)")
        print(f"usage={policy['scope']} export={str(policy['export_allowed']).lower()}")
    else:
        return False
    return True


def _render_context(command: str, converted: object) -> bool:
    if command == "context":
        item = _mapping(converted)
        counts = _mapping(item["counts"])
        budget = _mapping(item["budget"])
        print(f"receipt={item['receipt_id']}")
        print(f"bundle={item['bundle_id']}")
        print(
            f"selected={counts['selected']} omitted={counts['omitted']} "
            f"rejected={counts['rejected']} stale={counts['stale']} "
            f"truncated={str(item['truncated']).lower()}"
        )
        _render_budget(budget)
        for warning in _sequence(item["warnings"]):
            record = _mapping(warning)
            print(f"warning {record['code']}: {safe_text(str(record['message']))}")
        for missing in _sequence(item["missing_evidence"]):
            record = _mapping(missing)
            print(f"missing {record['evidence_type']} ({record['reason_code']})")
    elif command == "context-receipt":
        item = _mapping(converted)
        policy = _mapping(item["policy"])
        print(f"receipt={item['receipt_id']}")
        print(f"created={item['created_at']}")
        print(f"task_digest={item['task_digest']}")
        print(f"mode={policy['mode']}")
        _render_budget(_mapping(item["budget"]))
        print(
            f"scopes={len(_sequence(item['corpus_snapshot']))} "
            f"selected={len(_sequence(item['selected']))} "
            f"omitted={len(_sequence(item['omitted']))} "
            f"rejected={len(_sequence(item['rejected']))} "
            f"stale={len(_sequence(item['stale']))} "
            f"truncated={str(item['truncated']).lower()}"
        )
    else:
        return False
    return True


def _render_operations(command: str, converted: object) -> bool:
    if command == "storage-optimize":
        item = _mapping(converted)
        print(
            f"eligible={item['eligible_count']} completed={item['completed_count']} "
            f"failed={item['failed_count']} saved={item['stored_bytes_saved']} bytes"
        )
    elif command == "watch":
        item = _mapping(converted)
        counts = _mapping(item["counts"])
        print(
            f"root={item['root_id']} generation={item['generation']} "
            f"complete={str(item['complete']).lower()} "
            f"rescan={str(item['rescan_required']).lower()}"
        )
        print(
            f"entries={counts['entries']} candidates={counts['candidates']} "
            f"stable={counts['stable']} scheduled={counts['scheduled']} "
            f"succeeded={counts['succeeded']} retried={counts['retried']} "
            f"failed={counts['failed']} cancelled={counts['cancelled']}"
        )
    elif command == "jobs":
        for entry in _sequence(converted):
            record = _mapping(entry)
            print(
                f"{record['job_id']}\t{record['kind']}\t{record['state']}\t"
                f"attempts={record['attempt_count']}/{record['max_attempts']}"
            )
    elif command == "job-cancel":
        item = _mapping(converted)
        print(f"{item['job_id']}\t{item['state']}")
    else:
        return False
    return True


def _render_budget(budget: dict[object, object]) -> None:
    print(
        f"budget={budget['bundle_used']}/{budget['bundle_ceiling']} "
        f"{budget['unit']} limit={budget['limit']}"
    )


def _mapping(value: object) -> dict[object, object]:
    assert isinstance(value, dict)
    return value


def _sequence(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def _depth(value: object) -> int:
    assert isinstance(value, (int, str))
    return int(value)


def safe_text(value: str) -> str:
    """Escape terminal control characters in a human-oriented value."""
    encoded = json.dumps(value, ensure_ascii=False)
    return encoded[1:-1]


__all__ = ["json_value", "success", "write_json"]
