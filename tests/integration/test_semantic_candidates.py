"""Exact product composition tests with a model-free semantic provider."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.csv_parser import CsvParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.semantic_candidates import SemanticContextCandidateSource
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import ContextCompileRequest, ContextSelectionPolicy
from openardp.domain.semantic_retrieval import (
    SemanticPassage,
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticRetrievalPolicy,
    SemanticScore,
)
from openardp.interfaces.context_composition import local_semantic_context_compiler
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.ingestion import IngestionService
from tests.integration.test_rich_ingestion import _Clock, _Parser
from tests.integration.test_rich_ingestion import _service as _rich_service

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


class _MeaningProvider:
    def __init__(self) -> None:
        self.closed = False
        self.calls = 0

    @property
    def recipe(self) -> SemanticProviderRecipe:
        return SemanticProviderRecipe(
            provider="fixture-meaning",
            provider_version="1.0.0",
            model_id="fixture/de-en",
            model_revision="1" * 40,
            model_bundle_id="sha256:" + "2" * 64,
            dimensions=3,
            max_tokens=32,
            query_prefix="query: ",
            passage_prefix="passage: ",
            pooling="mean_attention_mask",
            normalization="l2",
            similarity="cosine",
            quantizer="half_away_from_zero_millionths_v1",
            transformers_version="0.0.0",
            torch_version="0.0.0",
        )

    def score(
        self,
        query: str,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: object,
    ) -> tuple[SemanticScore, ...]:
        del limits, cancel
        self.calls += 1
        return tuple(
            SemanticScore(
                evidence_id=passage.evidence_id,
                object_id=passage.object_id,
                provider_recipe_id=self.recipe.recipe_id,
                score_millionths=(
                    920_000
                    if "Robustness" in passage.text and "Robustheitsprinzip" in query
                    else 850_000
                    if "CVE-2021-44228" in passage.text and "CVE-2021-44228" in query
                    else 100_000
                ),
                cache_hit=self.calls > 1,
            )
            for passage in passages
        )

    def close(self) -> None:
        self.closed = True


class _CsvDominatingProvider(_MeaningProvider):
    def score(
        self,
        query: str,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: object,
    ) -> tuple[SemanticScore, ...]:
        del query, limits, cancel
        return tuple(
            SemanticScore(
                evidence_id=passage.evidence_id,
                object_id=passage.object_id,
                provider_recipe_id=self.recipe.recipe_id,
                score_millionths=(
                    950_000
                    if "noise" in passage.text
                    else 817_784
                    if "Scientific, Technical and Ethical Robustness" in passage.text
                    else 100_000
                ),
                cache_hit=False,
            )
            for passage in passages
        )


def _service(workspace: LocalWorkspace, parser: object, owner: str) -> IngestionService:
    return IngestionService(
        workspace.object_store,
        workspace.catalog,
        parser,  # type: ignore[arg-type]
        source_factory=LocalSource,
        clock=lambda: NOW,
        owner_id_factory=lambda: owner,
        lease_token_factory=lambda: owner * 16,
        random_bits=lambda: 1 if owner == "text" else 2,
    )


def test_semantic_profile_retrieves_cross_language_csv_and_abstains_on_future_year(
    tmp_path: Path,
) -> None:
    """Retrieve verified multilingual evidence and retain exact temporal abstention."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    text = tmp_path / "principles.txt"
    text.write_text(
        "NASA adds Scientific, Technical and Ethical Robustness as an additional principle.\n",
        encoding="utf-8",
    )
    csv = tmp_path / "kev.csv"
    csv.write_text(
        "cve,action,date\nCVE-2021-44228,Apply updates or remove product,2021-12-24\n",
        encoding="utf-8",
    )
    text_service = _service(workspace, TextParserAdapter(), "text")
    csv_service = _service(workspace, CsvParserAdapter(), "csv-")
    text_result = text_service.ingest(text)
    csv_result = csv_service.ingest(csv)
    provider = _MeaningProvider()
    compiler = local_semantic_context_compiler(
        workspace,
        Utf8ByteEstimator(),
        text_service.verify_ready_representation,
        lambda _rich: None,
        provider,
        policy=SemanticRetrievalPolicy(minimum_score_millionths=800_000),
        provider_limits=SemanticRetrievalLimits(
            max_passages=10,
            max_cache_entries=10,
            max_response_entries=10,
        ),
    )

    def compile(task: str) -> object:
        return compiler.compile(
            ContextCompileRequest(
                task=task,
                document_ids=tuple(
                    sorted(
                        (text_result.scope.document_id, csv_result.scope.document_id),
                        key=str,
                    )
                ),
                budget_limit=65_536,
                estimator=Utf8ByteEstimator().identity,
                policy=ContextSelectionPolicy(
                    mode=ContextMode.EXACT,
                    maximum_sensitivity=Sensitivity.UNKNOWN,
                ),
            )
        )

    german = compile("Welches zusätzliche Robustheitsprinzip hat NASA?")
    assert len(german.bundle.items) == 1
    assert german.bundle.items[0].reason == "semantic_embedding_match"
    selected_extensions = german.receipt.selected[0].extensions
    assert "https://openardp.example/ns/semantic-retrieval/v1" in selected_extensions

    cve = compile("What must agencies do for CVE-2021-44228 by 2021-12-24?")
    assert any("CVE-2021-44228" in str(item.content.body) for item in cve.bundle.items)

    unsupported = compile("What is NASA's 2027 AGI deployment budget?")
    assert unsupported.bundle.items == ()
    assert [warning.code for warning in unsupported.bundle.warnings] == ["no_semantic_evidence"]
    assert "no_semantic_evidence" in {notice.code for notice in unsupported.receipt.notices}


def test_source_balancing_prevents_large_csv_from_starving_cross_language_evidence(
    tmp_path: Path,
) -> None:
    """Diversify before global top-k while retaining the fixed semantic score floor."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    text = tmp_path / "principles.txt"
    text.write_text(
        "NASA adds Scientific, Technical and Ethical Robustness as an additional principle.\n",
        encoding="utf-8",
    )
    csv = tmp_path / "large.csv"
    csv.write_text(
        "id,value\n" + "".join(f"{index},noise record {index}\n" for index in range(20)),
        encoding="utf-8",
    )
    text_service = _service(workspace, TextParserAdapter(), "text")
    csv_service = _service(workspace, CsvParserAdapter(), "csv-")
    text_result = text_service.ingest(text)
    csv_result = csv_service.ingest(csv)
    documents = tuple(
        sorted((text_result.scope.document_id, csv_result.scope.document_id), key=str)
    )

    def compile(source_balanced: bool) -> object:
        compiler = local_semantic_context_compiler(
            workspace,
            Utf8ByteEstimator(),
            text_service.verify_ready_representation,
            lambda _rich: None,
            _CsvDominatingProvider(),
            policy=SemanticRetrievalPolicy(top_k=8),
            provider_limits=SemanticRetrievalLimits(
                max_passages=30,
                max_cache_entries=30,
                max_response_entries=30,
            ),
            hybrid_lexical_fallback=False,
            source_balanced=source_balanced,
            semantic_max_per_document=8,
            semantic_ranked_prefix=4,
        )
        return compiler.compile(
            ContextCompileRequest(
                task="Welches zusätzliche Robustheitsprinzip wurde ergänzt?",
                document_ids=documents,
                budget_limit=65_536,
                estimator=Utf8ByteEstimator().identity,
                policy=ContextSelectionPolicy(
                    mode=ContextMode.EXACT,
                    maximum_sensitivity=Sensitivity.UNKNOWN,
                ),
            )
        )

    unbalanced = compile(False)
    balanced = compile(True)

    assert not any(
        "Scientific, Technical and Ethical Robustness" in str(item.content.body)
        for item in unbalanced.bundle.items
    )
    assert any(
        "Scientific, Technical and Ethical Robustness" in str(item.content.body)
        for item in balanced.bundle.items
    )


def test_semantic_enumeration_prefers_verified_rich_projection_over_generic_rows(
    tmp_path: Path,
) -> None:
    """Score accepted rich evidence rather than shadowing it with generic catalog rows."""
    source_path = tmp_path / "source.docx"
    source_path.write_bytes(b"source-v1")
    parser = _Parser()
    parser.text = "NASA adds Scientific, Technical and Ethical Robustness as a principle."
    rich, store, catalog = _rich_service(tmp_path / "rich", parser, clock=_Clock())
    result = rich.ingest(source_path)
    semantic_source = SemanticContextCandidateSource(
        store,
        catalog,
        _MeaningProvider(),
        SemanticRetrievalPolicy(),
        SemanticRetrievalLimits(),
        text_verifier=lambda _text: None,
        rich_verifier=rich.verify_ready_representation,
    )
    compiler = ContextCompilerService(
        store,
        catalog,
        Utf8ByteEstimator(),
        (semantic_source,),
    )

    compiled = compiler.compile(
        ContextCompileRequest(
            task="Welches zusätzliche Robustheitsprinzip nennt NASA?",
            document_ids=(result.scope.document_id,),
            budget_limit=65_536,
            estimator=Utf8ByteEstimator().identity,
            policy=ContextSelectionPolicy(
                mode=ContextMode.EXACT,
                maximum_sensitivity=Sensitivity.UNKNOWN,
            ),
        )
    )

    assert len(compiled.bundle.items) == 1
    assert compiled.bundle.items[0].provenance.record_type == "evidence_projection"
    assert "Scientific, Technical and Ethical Robustness" in str(
        compiled.bundle.items[0].content.body
    )
