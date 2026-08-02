"""Small offline product-path tests for F025 semantic evaluation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from openardp.adapters.context_candidates import TextLexicalCandidateSource
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    ContextCompileLimits,
    ContextCompileRequest,
    ContextSelectionPolicy,
)
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from scripts.semantic_e2e_benchmark import make_observation, selected_observation

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def test_direct_and_operator_queries_use_identical_real_product_limits(tmp_path: Path) -> None:
    """Run product ingestion, lexical selection and exact citation resolution offline."""
    store = FilesystemObjectStore(tmp_path / "objects")
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    ingestion = IngestionService(
        store,
        catalog,
        TextParserAdapter(),
        source_factory=LocalSource,
        clock=lambda: NOW,
        owner_id_factory=lambda: "semantic-test",
        lease_token_factory=lambda: "0" * 64,
        random_bits=lambda: 1,
    )
    source = tmp_path / "facts.md"
    source.write_text("# Produce\n\nThe saffron mango is the gold specimen.\n", encoding="utf-8")
    ingested = ingestion.ingest(source)
    compiler = ContextCompilerService(
        store,
        catalog,
        Utf8ByteEstimator(),
        (TextLexicalCandidateSource(store, catalog),),
    )
    query = DocumentQueryService(
        store,
        catalog,
        source_factory=LocalSource,
        representation_verifier=ingestion.verify_ready_representation,
        clock=lambda: NOW,
    )
    limits = ContextCompileLimits(max_scopes=1, max_candidates=16, max_bundle_units=65_536)

    def request(task: str) -> ContextCompileRequest:
        return ContextCompileRequest(
            task=task,
            document_ids=(ingested.scope.document_id,),
            budget_limit=65_536,
            estimator=Utf8ByteEstimator().identity,
            policy=ContextSelectionPolicy(
                mode=ContextMode.EXACT,
                maximum_sensitivity=Sensitivity.UNKNOWN,
            ),
            limits=limits,
        )

    direct = compiler.compile(request("Identify commodity with aureate coloration?"))
    operator = compiler.compile(request("saffron mango gold specimen"))

    assert direct.bundle.items == ()
    assert operator.bundle.items
    assert direct.receipt.policy == operator.receipt.policy
    assert direct.receipt.estimator == operator.receipt.estimator
    item = operator.bundle.items[0]
    block = query.get(item.provenance.block_id)
    assert item.content is not None
    assert item.content.body == block.text

    question = {
        "question_id": "Q00",
        "answerable": True,
        "required_sources": ["synthetic-produce"],
        "acceptable_sources": ["synthetic-produce"],
        "support_atoms": [
            {
                "atom_id": "A01",
                "source_key": "synthetic-produce",
                "variants": ["saffron mango is the gold specimen"],
            }
        ],
        "source_fitness": [
            {
                "source_key": "synthetic-produce",
                "publisher_authority": 2,
                "directness": 2,
                "temporal_fit": 2,
                "integrity": 2,
                "reuse_basis": 2,
            }
        ],
    }
    evaluated = selected_observation(
        order=0,
        evidence_id=str(block.block_id),
        source_key="synthetic-produce",
        representation=item.representation.value,
        anchor_type="line_range",
        body=block.text or "",
        question=question,
        citation_valid=True,
    )
    row = make_observation(question, "openardp_operator", [evaluated])
    assert row["full_support"] is True
    assert row["citation_integrity_complete"] is True


def test_csv_gap_remains_an_explicit_body_free_product_row() -> None:
    """Never substitute a benchmark conversion for unsupported CSV ingestion."""
    question = {
        "question_id": "Q15",
        "answerable": True,
        "required_sources": ["cisa-known-exploited-vulnerabilities"],
        "acceptable_sources": ["cisa-known-exploited-vulnerabilities"],
        "support_atoms": [{"atom_id": "A01", "source_key": "cisa-known-exploited-vulnerabilities"}],
        "source_fitness": [],
    }
    row = make_observation(
        question,
        "openardp_direct",
        [],
        outcome="unsupported_format",
        failure_category="csv_product_ingestion_unsupported",
    )

    assert row["outcome"] == "unsupported_format"
    assert row["selected"] == []
    assert row["full_support"] is False
