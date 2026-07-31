"""Randomized reference-oracle evidence for the recursive invalidation closure."""

from __future__ import annotations

import random
import sqlite3

from openardp.adapters.sqlite_catalog import SQLiteCatalog


def _digest(index: int) -> str:
    return f"sha256:{index:064x}"


def test_recursive_sql_closure_matches_reference_oracle_for_100_branching_dags() -> None:
    """Compare branching/shared dependency closures with an independent Python walk."""
    generator = random.Random(10_010)  # noqa: S311 -- deterministic synthetic test corpus
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            "CREATE TABLE derivation_nodes (artifact_id TEXT PRIMARY KEY, state TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE derivation_dependencies (artifact_id TEXT NOT NULL, "
            "kind TEXT NOT NULL, input_digest TEXT NOT NULL, producer_artifact_id TEXT)"
        )
        for case in range(100):
            connection.execute("DELETE FROM derivation_dependencies")
            connection.execute("DELETE FROM derivation_nodes")
            count = generator.randint(4, 16)
            artifacts = tuple(_digest(case * 100 + index + 1) for index in range(count))
            states = {
                artifact: ("STALE" if generator.random() < 0.15 else "CURRENT")
                for artifact in artifacts
            }
            connection.executemany(
                "INSERT INTO derivation_nodes(artifact_id, state) VALUES (?, ?)",
                tuple(states.items()),
            )
            evidence_edges: dict[str, set[str]] = {artifact: set() for artifact in artifacts}
            producer_edges: dict[str, set[str]] = {artifact: set() for artifact in artifacts}
            for index, artifact in enumerate(artifacts):
                if generator.random() < 0.65:
                    binding = _digest(50_000 + case * 100 + generator.randint(0, 5))
                    evidence_edges[artifact].add(binding)
                    connection.execute(
                        "INSERT INTO derivation_dependencies VALUES (?, ?, ?, NULL)",
                        (artifact, "EVIDENCE_BINDING", binding),
                    )
                for producer_index in range(index):
                    if generator.random() < 0.16:
                        producer = artifacts[producer_index]
                        producer_edges[artifact].add(producer)
                        connection.execute(
                            "INSERT INTO derivation_dependencies VALUES (?, ?, ?, ?)",
                            (
                                artifact,
                                "DERIVATION_OUTPUT",
                                _digest(90_000 + producer_index),
                                producer,
                            ),
                        )
            inactive = tuple(
                sorted(
                    {
                        _digest(50_000 + case * 100 + generator.randint(0, 5))
                        for _ in range(generator.randint(1, 3))
                    }
                )
            )
            expected = {
                artifact
                for artifact in artifacts
                if states[artifact] == "CURRENT" and evidence_edges[artifact].intersection(inactive)
            }
            changed = True
            while changed:
                changed = False
                for artifact in artifacts:
                    if (
                        artifact not in expected
                        and states[artifact] == "CURRENT"
                        and producer_edges[artifact].intersection(expected)
                    ):
                        expected.add(artifact)
                        changed = True

            actual = SQLiteCatalog._invalidation_artifact_ids(connection, inactive)
            assert actual == tuple(sorted(expected))
