"""Deterministic generation, verification and evaluation for the F034 holdout."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from openardp.domain.identity import canonical_json_bytes, canonical_sha256

VERSION = "0.1.0"
UPSTREAM_COMMIT = "7d30520c717524000f0d9d2f9c10a069acd9d285"
EXPECTED_UPSTREAM_LOCK_ID = (
    "sha256:60368f2d36aac7708231c8128586550079efb629f09b46ee37df26674f5f1c64"
)
EXPECTED_CORPUS_ID = "sha256:a5047bbd768cd2927da302da94ded5fa8449a2a3df097ec482f9f6ca708eaca3"
EXPECTED_QUESTION_SET_ID = "sha256:5648e59596d1e6bc95cf786f5bdf8a9da8856d8d1f6ee072621014be1b848c61"
EXPECTED_PROTOCOL_ID = "sha256:371bfeafc35d80b792aed06cf5394356bcba83cc4fb2510e682ef29cf2f4e91e"
SELECTION_SEED = "openardp-f034-xquad-holdout-v0.1.0"
CORPUS_RELATIVE = Path("corpora/retrieval-holdout/v0.1.0")
BENCHMARK_RELATIVE = Path("benchmarks/retrieval-holdout/v0.1.0")
QUESTION_IDS = tuple(f"H{number:03d}" for number in range(1, 101))
TREATMENTS = ("f027_lexical_direct", "f029_semantic_direct")
RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
THRESHOLDS = {
    "full_support": [80, 100],
    "atom_recall": [90, 100],
    "source_recall": [90, 100],
    "evidence_precision": [60, 100],
    "mrr": [80, 100],
    "citation_integrity": [100, 100],
    "unsupported_abstention": [80, 100],
    "german_atom_recall": [50, 100],
    "spanish_atom_recall": [50, 100],
}
UPSTREAM_FILES = {
    "CC-BY-SA4.0.txt": {
        "byte_length": 15058,
        "sha256": "sha256:25ddafc153e4cfdafd70729574ef1b44348e1814709e57680d55347038d3f92c",
    },
    "xquad.de.json": {
        "byte_length": 669810,
        "sha256": "sha256:990b5d746746ed65ed4702ea5f35f99ffa4e2f1c390c07d003642acd937916f9",
    },
    "xquad.en.json": {
        "byte_length": 609383,
        "sha256": "sha256:e4c57d1c9143aaa1c5d265ba5987a65f4e69528d2a98f29d6e75019b10344f29",
    },
    "xquad.es.json": {
        "byte_length": 684322,
        "sha256": "sha256:dcbae93ec3a9f4b9e78fd834a171d6f96c1a875e10e15b7530b7e4ef4971e37e",
    },
}
_SOURCE_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_README = (
    "# OpenARDP XQuAD retrieval holdout\n\n"
    "Deterministic 20-document derivative of pinned XQuAD English contexts for "
    "milestone-only retrieval evaluation. Questions use aligned English, German "
    "and Spanish XQuAD records. See `upstream-lock.json` and "
    "`THIRD_PARTY_NOTICES.md`.\n"
)
_NOTICE = (
    "# Third-party notices\n\n"
    "XQuAD by Mikel Artetxe, Sebastian Ruder and Dani Yogatama is distributed "
    "under CC BY-SA 4.0. This repository redistributes a deterministic adapted "
    "subset and identifies changes through the generation recipe and OpenARDP "
    "corpus/question identities. The underlying contexts originate from "
    "SQuAD/Wikipedia. The adapted corpus sources and aligned question records in "
    "this holdout are licensed under CC BY-SA 4.0. No endorsement by Google "
    "DeepMind is implied.\n\n"
    f"Upstream: https://github.com/google-deepmind/xquad/tree/{UPSTREAM_COMMIT}\n"
)


class HoldoutError(ValueError):
    """Stable body-free F034 failure category."""


@dataclass(frozen=True, slots=True)
class HoldoutVerification:
    """Verified body-free identities and coverage."""

    corpus_id: str
    protocol_id: str
    question_set_id: str
    source_count: int
    question_count: int


@dataclass(frozen=True, slots=True)
class HoldoutInputs:
    """Exact verified F034 inputs and source payloads."""

    corpus: dict[str, Any]
    protocol: dict[str, Any]
    question_set: dict[str, Any]
    questions: dict[str, dict[str, Any]]
    source_text: dict[str, str]

    @property
    def by_id(self) -> dict[str, dict[str, Any]]:
        """Expose the shared benchmark input shape without duplicating records."""
        return self.questions


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(dict(value)) + b"\n")


def load_json(path: Path, *, maximum_bytes: int = 4_194_304) -> dict[str, Any]:
    """Load one bounded duplicate-member-rejecting JSON object."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise HoldoutError("json_file")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise HoldoutError("json_duplicate_key")
            value[key] = item
        return value

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(HoldoutError("json_non_finite")),
        )
    except HoldoutError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HoldoutError("json_invalid") from error
    if not isinstance(value, dict):
        raise HoldoutError("json_shape")
    return value


def _identity(value: dict[str, Any], field: str) -> str:
    declared = value.get(field)
    if not isinstance(declared, str) or _SHA256.fullmatch(declared) is None:
        raise HoldoutError(f"{field}_shape")
    projected = dict(value)
    projected.pop(field)
    if canonical_sha256(projected) != declared:
        raise HoldoutError(f"{field}_mismatch")
    return declared


def _rank(kind: str, value: str) -> str:
    return hashlib.sha256(f"{SELECTION_SEED}:{kind}:{value}".encode()).hexdigest()


def _slug(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    if not value or _SOURCE_KEY.fullmatch(value) is None:
        raise HoldoutError("source_key")
    return value


def _safe_relative(value: str, prefix: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or "\\" in value
        or any(part in {"", ".", ".."} for part in path.parts)
        or not value.startswith(prefix)
    ):
        raise HoldoutError("path")
    return path


def _verify_upstream_file(root: Path, name: str) -> bytes:
    path = root / name
    expected = UPSTREAM_FILES[name]
    if path.is_symlink() or not path.is_file():
        raise HoldoutError("upstream_file")
    payload = path.read_bytes()
    if len(payload) != expected["byte_length"] or _digest(payload) != expected["sha256"]:
        raise HoldoutError("upstream_digest")
    return payload


def _upstream_index(payload: bytes) -> tuple[list[str], dict[str, list[str]], dict[str, Any]]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HoldoutError("upstream_json") from error
    if not isinstance(value, dict) or value.get("version") != "1.1":
        raise HoldoutError("upstream_schema")
    data = value.get("data")
    if not isinstance(data, list):
        raise HoldoutError("upstream_schema")
    titles: list[str] = []
    contexts: dict[str, list[str]] = {}
    qas: dict[str, Any] = {}
    for article in data:
        if not isinstance(article, dict) or not isinstance(article.get("title"), str):
            raise HoldoutError("upstream_schema")
        title = article["title"]
        if title in contexts:
            raise HoldoutError("upstream_duplicate")
        titles.append(title)
        contexts[title] = []
        article_qas: dict[str, Any] = {}
        paragraphs = article.get("paragraphs")
        if not isinstance(paragraphs, list):
            raise HoldoutError("upstream_schema")
        for paragraph in paragraphs:
            if not isinstance(paragraph, dict) or not isinstance(paragraph.get("context"), str):
                raise HoldoutError("upstream_schema")
            contexts[title].append(paragraph["context"])
            raw_qas = paragraph.get("qas")
            if not isinstance(raw_qas, list):
                raise HoldoutError("upstream_schema")
            for qa in raw_qas:
                if (
                    not isinstance(qa, dict)
                    or not isinstance(qa.get("id"), str)
                    or not isinstance(qa.get("question"), str)
                    or not isinstance(qa.get("answers"), list)
                ):
                    raise HoldoutError("upstream_schema")
                qa_id = qa["id"]
                answers = qa["answers"]
                if qa_id in article_qas or not answers:
                    raise HoldoutError("upstream_duplicate")
                if any(
                    not isinstance(answer, dict)
                    or not isinstance(answer.get("text"), str)
                    or not answer["text"]
                    for answer in answers
                ):
                    raise HoldoutError("upstream_schema")
                article_qas[qa_id] = qa
        qas[title] = article_qas
    return titles, contexts, qas


def _fitness(source_key: str) -> dict[str, Any]:
    return {
        "source_key": source_key,
        "publisher_authority": 1,
        "directness": 2,
        "temporal_fit": 2,
        "integrity": 2,
        "reuse_basis": 2,
        "rationale": (
            "Pinned XQuAD/SQuAD excerpt directly containing the professionally aligned answer span."
        ),
    }


def _answers(qa: dict[str, Any]) -> list[str]:
    return sorted({str(answer["text"]) for answer in qa["answers"]})


def _single_question(
    *,
    question_id: str,
    language: str,
    stratum: str,
    title: str,
    source_key: str,
    localized_qa: dict[str, Any],
    english_qa: dict[str, Any],
) -> dict[str, Any]:
    variants = _answers(english_qa)
    return {
        "question_id": question_id,
        "language": language,
        "stratum": stratum,
        "question": localized_qa["question"],
        "operator_query": localized_qa["question"],
        "reference_answer": variants[0],
        "answerable": True,
        "temporal_scope": "historical_document",
        "required_formats": ["md"],
        "required_sources": [source_key],
        "acceptable_sources": [source_key],
        "support_atoms": [
            {
                "atom_id": "A01",
                "source_key": source_key,
                "variants": variants,
                "required": True,
            }
        ],
        "source_fitness": [_fitness(source_key)],
        "upstream_qa_ids": [english_qa["id"]],
        "upstream_titles": [title],
    }


def _multi_question(
    *,
    question_id: str,
    left_title: str,
    right_title: str,
    left_key: str,
    right_key: str,
    left_qa: dict[str, Any],
    right_qa: dict[str, Any],
) -> dict[str, Any]:
    left_answers = _answers(left_qa)
    right_answers = _answers(right_qa)
    question = (
        f"For {left_title.replace('_', ' ')}, {left_qa['question']} "
        f"For {right_title.replace('_', ' ')}, {right_qa['question']}"
    )
    keys = sorted((left_key, right_key))
    atom_by_key = {
        left_key: {"variants": left_answers, "qa_id": left_qa["id"], "title": left_title},
        right_key: {
            "variants": right_answers,
            "qa_id": right_qa["id"],
            "title": right_title,
        },
    }
    return {
        "question_id": question_id,
        "language": "en",
        "stratum": "multi_source",
        "question": question,
        "operator_query": question,
        "reference_answer": f"{left_answers[0]}; {right_answers[0]}",
        "answerable": True,
        "temporal_scope": "historical_document",
        "required_formats": ["md"],
        "required_sources": keys,
        "acceptable_sources": keys,
        "support_atoms": [
            {
                "atom_id": f"A{index:02d}",
                "source_key": key,
                "variants": atom_by_key[key]["variants"],
                "required": True,
            }
            for index, key in enumerate(keys, 1)
        ],
        "source_fitness": [_fitness(key) for key in keys],
        "upstream_qa_ids": sorted(str(atom_by_key[key]["qa_id"]) for key in keys),
        "upstream_titles": sorted(str(atom_by_key[key]["title"]) for key in keys),
    }


def _unsupported_question(
    *, question_id: str, language: str, title: str, qa: dict[str, Any]
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "language": language,
        "stratum": "unsupported",
        "question": qa["question"],
        "operator_query": qa["question"],
        "reference_answer": (
            "The required XQuAD source is intentionally absent from this holdout corpus."
        ),
        "answerable": False,
        "temporal_scope": "historical_document",
        "required_formats": ["md"],
        "required_sources": [],
        "acceptable_sources": [],
        "support_atoms": [],
        "source_fitness": [],
        "upstream_qa_ids": [qa["id"]],
        "upstream_titles": [title],
    }


def _questions_schema(corpus_id: str) -> dict[str, Any]:
    source_key = {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://openardp.org/schemas/benchmark/retrieval-holdout-questions-0.1.0.json",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "benchmark_version",
            "corpus_id",
            "license",
            "upstream_lock_id",
            "questions",
            "question_set_id",
        ],
        "properties": {
            "schema_version": {"const": VERSION},
            "benchmark_version": {"const": VERSION},
            "corpus_id": {"const": corpus_id},
            "license": {"const": "CC-BY-SA-4.0"},
            "upstream_lock_id": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "question_set_id": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "questions": {
                "type": "array",
                "minItems": 100,
                "maxItems": 100,
                "items": {"$ref": "#/$defs/question"},
            },
        },
        "$defs": {
            "fitness": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_key",
                    "publisher_authority",
                    "directness",
                    "temporal_fit",
                    "integrity",
                    "reuse_basis",
                    "rationale",
                ],
                "properties": {
                    "source_key": source_key,
                    "publisher_authority": {"type": "integer", "minimum": 0, "maximum": 2},
                    "directness": {"type": "integer", "minimum": 0, "maximum": 2},
                    "temporal_fit": {"type": "integer", "minimum": 0, "maximum": 2},
                    "integrity": {"type": "integer", "minimum": 0, "maximum": 2},
                    "reuse_basis": {"type": "integer", "minimum": 0, "maximum": 2},
                    "rationale": {"type": "string", "minLength": 1},
                },
            },
            "atom": {
                "type": "object",
                "additionalProperties": False,
                "required": ["atom_id", "source_key", "variants", "required"],
                "properties": {
                    "atom_id": {"type": "string", "pattern": "^A[0-9]{2}$"},
                    "source_key": source_key,
                    "variants": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "required": {"const": True},
                },
            },
            "question": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "question_id",
                    "language",
                    "stratum",
                    "question",
                    "operator_query",
                    "reference_answer",
                    "answerable",
                    "temporal_scope",
                    "required_formats",
                    "required_sources",
                    "acceptable_sources",
                    "support_atoms",
                    "source_fitness",
                    "upstream_qa_ids",
                    "upstream_titles",
                ],
                "properties": {
                    "question_id": {"type": "string", "pattern": "^H[0-9]{3}$"},
                    "language": {"enum": ["de", "en", "es"]},
                    "stratum": {
                        "enum": [
                            "cross_language",
                            "direct",
                            "multi_source",
                            "source_discrimination",
                            "unsupported",
                        ]
                    },
                    "question": {"type": "string", "minLength": 1},
                    "operator_query": {"type": "string", "minLength": 1},
                    "reference_answer": {"type": "string", "minLength": 1},
                    "answerable": {"type": "boolean"},
                    "temporal_scope": {"const": "historical_document"},
                    "required_formats": {"const": ["md"]},
                    "required_sources": {
                        "type": "array",
                        "maxItems": 2,
                        "items": source_key,
                    },
                    "acceptable_sources": {
                        "type": "array",
                        "maxItems": 2,
                        "items": source_key,
                    },
                    "support_atoms": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {"$ref": "#/$defs/atom"},
                    },
                    "source_fitness": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {"$ref": "#/$defs/fitness"},
                    },
                    "upstream_qa_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 2,
                        "items": {"type": "string"},
                    },
                    "upstream_titles": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 2,
                        "items": {"type": "string"},
                    },
                },
            },
        },
    }


def _prepare_directory(path: Path) -> None:
    if path.is_symlink():
        raise HoldoutError("output_path")
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        raise HoldoutError("output_not_empty")


def generate_holdout(upstream_root: Path, output_root: Path) -> HoldoutVerification:
    """Generate the exact F034 derivative from the pinned XQuAD checkout."""
    root = upstream_root.resolve(strict=True)
    license_payload = _verify_upstream_file(root, "CC-BY-SA4.0.txt")
    language_payloads = {
        language: _verify_upstream_file(root, f"xquad.{language}.json")
        for language in ("de", "en", "es")
    }
    indexed = {
        language: _upstream_index(payload) for language, payload in language_payloads.items()
    }
    titles, contexts, english_qas = indexed["en"]
    for language in ("de", "es"):
        localized_titles, _, localized_qas = indexed[language]
        if localized_titles != titles:
            raise HoldoutError("parallel_titles")
        for title in titles:
            if list(localized_qas[title]) != list(english_qas[title]):
                raise HoldoutError("parallel_questions")

    ranked_titles = sorted(titles, key=lambda title: (_rank("title", title), title))
    selected_titles = ranked_titles[:20]
    negative_titles = ranked_titles[20:30]
    if len(selected_titles) != 20 or len(negative_titles) != 10:
        raise HoldoutError("selection_count")

    corpus_root = output_root / CORPUS_RELATIVE
    benchmark_root = output_root / BENCHMARK_RELATIVE
    _prepare_directory(corpus_root)
    _prepare_directory(benchmark_root)
    source_root = corpus_root / "sources"
    source_root.mkdir()
    license_root = corpus_root / "LICENSES"
    license_root.mkdir()
    (license_root / "CC-BY-SA-4.0.txt").write_bytes(license_payload)
    (corpus_root / "README.md").write_text(_README, encoding="utf-8")
    (corpus_root / "THIRD_PARTY_NOTICES.md").write_text(_NOTICE, encoding="utf-8")

    source_records: list[dict[str, Any]] = []
    source_keys: dict[str, str] = {}
    selected_qas: dict[str, list[str]] = {}
    for ordinal, title in enumerate(selected_titles, 1):
        source_key = f"xquad-{_slug(title)}"
        if source_key in source_keys.values():
            raise HoldoutError("source_key_collision")
        source_keys[title] = source_key
        qa_ids = sorted(english_qas[title], key=lambda value: (_rank(f"qa:{title}", value), value))
        if len(qa_ids) < 5:
            raise HoldoutError("question_selection")
        selected_qas[title] = qa_ids[:5]
        relative = f"sources/{ordinal:02d}-{_slug(title)}.md"
        body = "\n\n".join(context.rstrip() for context in contexts[title])
        payload = (f"# {title.replace('_', ' ')}\n\n{body}\n").encode()
        (corpus_root / relative).write_bytes(payload)
        source_records.append(
            {
                "key": source_key,
                "path": relative,
                "title": title.replace("_", " "),
                "upstream_title": title,
                "format": "md",
                "media_type": "text/markdown",
                "byte_length": len(payload),
                "sha256": _digest(payload),
                "rights_id": "xquad-cc-by-sa-4.0",
            }
        )

    upstream_lock: dict[str, Any] = {
        "schema_version": VERSION,
        "upstream_name": "XQuAD",
        "upstream_repository": "https://github.com/google-deepmind/xquad",
        "upstream_commit": UPSTREAM_COMMIT,
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/legalcode",
        "selection_seed": SELECTION_SEED,
        "selection_algorithm": "sha256-title-first20-next10-qa-first5-v1",
        "files": [
            {
                "name": name,
                "byte_length": facts["byte_length"],
                "sha256": facts["sha256"],
                "url": f"https://raw.githubusercontent.com/google-deepmind/xquad/{UPSTREAM_COMMIT}/{name}",
            }
            for name, facts in sorted(UPSTREAM_FILES.items())
        ],
    }
    upstream_lock["upstream_lock_id"] = canonical_sha256(upstream_lock)
    _write_json(corpus_root / "upstream-lock.json", upstream_lock)

    corpus_lock: dict[str, Any] = {
        "schema_version": VERSION,
        "corpus_version": VERSION,
        "corpus_name": "openardp-xquad-retrieval-holdout",
        "upstream_lock_id": upstream_lock["upstream_lock_id"],
        "source_count": 20,
        "payload_bytes": sum(int(item["byte_length"]) for item in source_records),
        "auxiliary_files": [
            {
                "path": "LICENSES/CC-BY-SA-4.0.txt",
                "byte_length": len(license_payload),
                "sha256": _digest(license_payload),
            },
            {
                "path": "README.md",
                "byte_length": len(_README.encode("utf-8")),
                "sha256": _digest(_README.encode("utf-8")),
            },
            {
                "path": "THIRD_PARTY_NOTICES.md",
                "byte_length": len(_NOTICE.encode("utf-8")),
                "sha256": _digest(_NOTICE.encode("utf-8")),
            },
        ],
        "sources": source_records,
    }
    corpus_lock["corpus_id"] = canonical_sha256(corpus_lock)
    _write_json(corpus_root / "corpus-lock.json", corpus_lock)

    questions: list[dict[str, Any]] = []
    next_id = iter(QUESTION_IDS)
    for title_index, title in enumerate(selected_titles):
        source_key = source_keys[title]
        qa_ids = selected_qas[title]
        assignments = (
            ("en", "direct", qa_ids[0]),
            ("de", "cross_language", qa_ids[1]),
            ("es", "cross_language", qa_ids[2]),
            ("en", "direct" if title_index < 10 else "source_discrimination", qa_ids[3]),
        )
        for language, stratum, qa_id in assignments:
            questions.append(
                _single_question(
                    question_id=next(next_id),
                    language=language,
                    stratum=stratum,
                    title=title,
                    source_key=source_key,
                    localized_qa=indexed[language][2][title][qa_id],
                    english_qa=english_qas[title][qa_id],
                )
            )
    for index in range(0, 20, 2):
        left_title = selected_titles[index]
        right_title = selected_titles[index + 1]
        questions.append(
            _multi_question(
                question_id=next(next_id),
                left_title=left_title,
                right_title=right_title,
                left_key=source_keys[left_title],
                right_key=source_keys[right_title],
                left_qa=english_qas[left_title][selected_qas[left_title][4]],
                right_qa=english_qas[right_title][selected_qas[right_title][4]],
            )
        )
    for index, title in enumerate(negative_titles):
        language = "de" if index < 5 else "es"
        qa_id = sorted(
            english_qas[title],
            key=lambda value: (_rank(f"negative:{title}", value), value),
        )[0]
        questions.append(
            _unsupported_question(
                question_id=next(next_id),
                language=language,
                title=title,
                qa=indexed[language][2][title][qa_id],
            )
        )
    try:
        next(next_id)
    except StopIteration:
        pass
    else:  # pragma: no cover - guarded by exact construction counts
        raise HoldoutError("question_count")

    question_set: dict[str, Any] = {
        "schema_version": VERSION,
        "benchmark_version": VERSION,
        "corpus_id": corpus_lock["corpus_id"],
        "license": "CC-BY-SA-4.0",
        "upstream_lock_id": upstream_lock["upstream_lock_id"],
        "questions": questions,
    }
    question_set["question_set_id"] = canonical_sha256(question_set)
    _write_json(benchmark_root / "questions.json", question_set)
    _write_json(
        benchmark_root / "questions.schema.json",
        _questions_schema(corpus_lock["corpus_id"]),
    )

    protocol: dict[str, Any] = {
        "benchmark_version": VERSION,
        "corpus_id": corpus_lock["corpus_id"],
        "question_set_id": question_set["question_set_id"],
        "question_count": 100,
        "treatments": list(TREATMENTS),
        "fresh_runs": 2,
        "network": "denied",
        "holdout_use": "milestone_only_f025_is_development",
        "context": {
            "budget_bytes": 262144,
            "max_scopes": 20,
            "max_discovered": 10000,
            "max_candidates": 64,
            "max_body_bytes": 8388608,
            "max_decisions": 12000,
            "max_bundle_units": 262144,
        },
        "semantic_policy": {
            "minimum_score_millionths": 800000,
            "top_k": 128,
            "require_volatile_time_match": True,
        },
        "provider_limits": {
            "max_passages": 10000,
            "max_total_text_bytes": 67108864,
            "max_passage_bytes": 8388608,
            "batch_size": 16,
            "max_cache_entries": 10000,
            "max_response_entries": 10000,
            "timeout_seconds": 900,
        },
        "retrieval_profile": {
            "hybrid_lexical_fallback": True,
            "source_balanced_semantic_admission": True,
            "semantic_max_per_document": 32,
            "semantic_ranked_prefix": 4,
            "retrieval_tier_order": ["minimum_relevant_lexical", "semantic"],
            "representation_precedence": "rich_then_text",
        },
        "model": {
            "model_id": "intfloat/multilingual-e5-small",
            "model_revision": "f470c6a1a906014160ece1968c484b275f0396de",
            "model_bundle_id": (
                "sha256:1d1242c4f405989f1c134ad2fc4557afaa75bcf2d5bca58990c70a54b39c4b02"
            ),
            "dimensions": 384,
            "max_tokens": 512,
        },
        "thresholds": THRESHOLDS,
        "result_max_bytes": 8388608,
        "forbidden_result_keys": [
            "body",
            "content",
            "hostname",
            "path",
            "query",
            "question",
            "reference_answer",
            "username",
        ],
    }
    protocol["protocol_id"] = canonical_sha256(protocol)
    _write_json(benchmark_root / "protocol.json", protocol)

    return verify_holdout(output_root)


def _validate_question_set(
    question_set: dict[str, Any],
    schema: dict[str, Any],
    source_text: dict[str, str],
    corpus: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(question_set),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        raise HoldoutError("question_schema")
    _identity(question_set, "question_set_id")
    records = question_set.get("questions")
    if not isinstance(records, list) or [item.get("question_id") for item in records] != list(
        QUESTION_IDS
    ):
        raise HoldoutError("question_order")
    by_id = {str(item["question_id"]): item for item in records}
    languages = Counter(str(item["language"]) for item in records)
    strata = Counter(str(item["stratum"]) for item in records)
    if languages != Counter({"en": 50, "de": 25, "es": 25}) or strata != Counter(
        {
            "direct": 30,
            "cross_language": 40,
            "source_discrimination": 10,
            "multi_source": 10,
            "unsupported": 10,
        }
    ):
        raise HoldoutError("question_coverage")
    selected_titles = {str(item["upstream_title"]) for item in corpus["sources"]}
    for question in records:
        required = question["required_sources"]
        acceptable = question["acceptable_sources"]
        atoms = question["support_atoms"]
        fitness = question["source_fitness"]
        if required != sorted(set(required)) or acceptable != sorted(set(acceptable)):
            raise HoldoutError("question_source_order")
        if question["answerable"]:
            if not required or required != acceptable or len(atoms) != len(required):
                raise HoldoutError("answerable_contract")
            if sorted(item["source_key"] for item in atoms) != required:
                raise HoldoutError("oracle_source")
            if sorted(item["source_key"] for item in fitness) != required:
                raise HoldoutError("fitness_source")
            for atom in atoms:
                body = source_text.get(str(atom["source_key"]))
                if body is None or not any(
                    str(variant).casefold() in body.casefold() for variant in atom["variants"]
                ):
                    raise HoldoutError("oracle_atom")
        elif required or acceptable or atoms or fitness:
            raise HoldoutError("unsupported_contract")
        if not question["answerable"] and any(
            str(title) in selected_titles for title in question["upstream_titles"]
        ):
            raise HoldoutError("unsupported_source_present")
    return by_id


def load_holdout(repository_root: Path) -> HoldoutInputs:
    """Load and fully verify the committed F034 input set."""
    root = repository_root.resolve(strict=True)
    corpus_root = root / CORPUS_RELATIVE
    benchmark_root = root / BENCHMARK_RELATIVE
    upstream = load_json(corpus_root / "upstream-lock.json")
    corpus = load_json(corpus_root / "corpus-lock.json")
    question_set = load_json(benchmark_root / "questions.json")
    schema = load_json(benchmark_root / "questions.schema.json")
    protocol = load_json(benchmark_root / "protocol.json")
    _identity(upstream, "upstream_lock_id")
    corpus_id = _identity(corpus, "corpus_id")
    question_set_id = _identity(question_set, "question_set_id")
    _identity(protocol, "protocol_id")
    expected_upstream_files = [
        {
            "name": name,
            "byte_length": facts["byte_length"],
            "sha256": facts["sha256"],
            "url": (
                f"https://raw.githubusercontent.com/google-deepmind/xquad/{UPSTREAM_COMMIT}/{name}"
            ),
        }
        for name, facts in sorted(UPSTREAM_FILES.items())
    ]
    if (
        upstream.get("upstream_lock_id") != EXPECTED_UPSTREAM_LOCK_ID
        or corpus_id != EXPECTED_CORPUS_ID
        or question_set_id != EXPECTED_QUESTION_SET_ID
        or protocol.get("protocol_id") != EXPECTED_PROTOCOL_ID
        or upstream.get("upstream_commit") != UPSTREAM_COMMIT
        or upstream.get("selection_seed") != SELECTION_SEED
        or upstream.get("upstream_name") != "XQuAD"
        or upstream.get("upstream_repository") != "https://github.com/google-deepmind/xquad"
        or upstream.get("license") != "CC-BY-SA-4.0"
        or upstream.get("license_url") != "https://creativecommons.org/licenses/by-sa/4.0/legalcode"
        or upstream.get("selection_algorithm") != "sha256-title-first20-next10-qa-first5-v1"
        or upstream.get("files") != expected_upstream_files
        or corpus.get("upstream_lock_id") != upstream.get("upstream_lock_id")
        or question_set.get("corpus_id") != corpus_id
        or question_set.get("license") != "CC-BY-SA-4.0"
        or question_set.get("upstream_lock_id") != EXPECTED_UPSTREAM_LOCK_ID
        or protocol.get("corpus_id") != corpus_id
        or protocol.get("question_set_id") != question_set_id
        or protocol.get("thresholds") != THRESHOLDS
        or protocol.get("treatments") != list(TREATMENTS)
        or protocol.get("holdout_use") != "milestone_only_f025_is_development"
    ):
        raise HoldoutError("input_binding")
    if schema != _questions_schema(corpus_id):
        raise HoldoutError("question_schema_drift")
    sources = corpus.get("sources")
    if not isinstance(sources, list) or len(sources) != 20:
        raise HoldoutError("corpus_count")
    source_text: dict[str, str] = {}
    expected_source_paths: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise HoldoutError("corpus_source")
        key = source.get("key")
        relative = source.get("path")
        if (
            not isinstance(key, str)
            or _SOURCE_KEY.fullmatch(key) is None
            or not isinstance(relative, str)
        ):
            raise HoldoutError("corpus_source")
        _safe_relative(relative, "sources/")
        path = corpus_root / relative
        if path.is_symlink() or not path.is_file():
            raise HoldoutError("corpus_file")
        payload = path.read_bytes()
        if len(payload) != source.get("byte_length") or _digest(payload) != source.get("sha256"):
            raise HoldoutError("corpus_digest")
        if key in source_text or relative in expected_source_paths:
            raise HoldoutError("corpus_duplicate")
        try:
            source_text[key] = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HoldoutError("corpus_encoding") from error
        expected_source_paths.add(relative)
    auxiliary = corpus.get("auxiliary_files")
    expected_auxiliary = {"LICENSES/CC-BY-SA-4.0.txt": UPSTREAM_FILES["CC-BY-SA4.0.txt"]}
    expected_auxiliary["README.md"] = {
        "byte_length": len(_README.encode("utf-8")),
        "sha256": _digest(_README.encode("utf-8")),
    }
    expected_auxiliary["THIRD_PARTY_NOTICES.md"] = {
        "byte_length": len(_NOTICE.encode("utf-8")),
        "sha256": _digest(_NOTICE.encode("utf-8")),
    }
    if (
        not isinstance(auxiliary, list)
        or {
            str(record.get("path")): {
                "byte_length": record.get("byte_length"),
                "sha256": record.get("sha256"),
            }
            for record in auxiliary
            if isinstance(record, dict)
        }
        != expected_auxiliary
    ):
        raise HoldoutError("auxiliary_binding")
    for relative, facts in expected_auxiliary.items():
        path = corpus_root / relative
        if path.is_symlink() or not path.is_file():
            raise HoldoutError("auxiliary_file")
        payload = path.read_bytes()
        if len(payload) != facts["byte_length"] or _digest(payload) != facts["sha256"]:
            raise HoldoutError("auxiliary_digest")
    expected_inventory = {
        "README.md",
        "THIRD_PARTY_NOTICES.md",
        "LICENSES/CC-BY-SA-4.0.txt",
        "corpus-lock.json",
        "upstream-lock.json",
        *expected_source_paths,
    }
    actual_inventory = {
        path.relative_to(corpus_root).as_posix()
        for path in corpus_root.rglob("*")
        if path.is_file()
    }
    actual_directories = {
        path.relative_to(corpus_root).as_posix() for path in corpus_root.rglob("*") if path.is_dir()
    }
    if actual_inventory != expected_inventory or actual_directories != {"LICENSES", "sources"}:
        raise HoldoutError("corpus_inventory")
    benchmark_inventory = {
        path.relative_to(benchmark_root).as_posix()
        for path in benchmark_root.rglob("*")
        if path.is_file() and "results" not in path.relative_to(benchmark_root).parts
    }
    if benchmark_inventory != {"protocol.json", "questions.json", "questions.schema.json"}:
        raise HoldoutError("benchmark_inventory")
    unexpected_benchmark_directories = {
        path.relative_to(benchmark_root).as_posix()
        for path in benchmark_root.rglob("*")
        if path.is_dir() and "results" not in path.relative_to(benchmark_root).parts
    }
    if unexpected_benchmark_directories:
        raise HoldoutError("benchmark_inventory")
    by_id = _validate_question_set(question_set, schema, source_text, corpus)
    return HoldoutInputs(
        corpus=corpus,
        protocol=protocol,
        question_set=question_set,
        questions=by_id,
        source_text=source_text,
    )


def verify_holdout(repository_root: Path) -> HoldoutVerification:
    """Verify all committed holdout inputs and return body-free facts."""
    inputs = load_holdout(repository_root)
    return HoldoutVerification(
        corpus_id=str(inputs.corpus["corpus_id"]),
        protocol_id=str(inputs.protocol["protocol_id"]),
        question_set_id=str(inputs.question_set["question_set_id"]),
        source_count=len(inputs.source_text),
        question_count=len(inputs.questions),
    )


def evaluate_verdict(
    *,
    validity_checks: Mapping[str, bool],
    quality_checks: Mapping[str, bool],
    failures: tuple[str, ...],
    summary_id: str,
) -> dict[str, Any]:
    """Return separate exact validity and quality axes."""
    validity_blockers = sorted(key for key, passed in validity_checks.items() if not passed)
    quality_blockers = sorted(key for key, passed in quality_checks.items() if not passed)
    valid = not failures and not validity_blockers
    decision: dict[str, Any] = {
        "benchmark_version": VERSION,
        "validity": "HOLDOUT_BASELINE_VALID" if valid else "HOLDOUT_BASELINE_INVALID",
        "quality": (
            "HOLDOUT_TARGETS_MET"
            if valid and not quality_blockers
            else "HOLDOUT_BELOW_TARGETS"
            if valid
            else "HOLDOUT_QUALITY_NOT_EVALUABLE"
        ),
        "failures": sorted(set(failures)),
        "validity_blockers": validity_blockers,
        "quality_blockers": quality_blockers if valid else [],
        "summary_id": summary_id,
    }
    decision["decision_id"] = canonical_sha256(decision)
    return decision


def compare_generated(generated_root: Path, repository_root: Path) -> bool:
    """Compare every generated input byte against the committed F034 tree."""
    for relative in (CORPUS_RELATIVE, BENCHMARK_RELATIVE):
        generated = generated_root / relative
        committed = repository_root / relative
        generated_files = sorted(
            path.relative_to(generated).as_posix()
            for path in generated.rglob("*")
            if path.is_file()
        )
        committed_files = sorted(
            path.relative_to(committed).as_posix()
            for path in committed.rglob("*")
            if path.is_file() and "results" not in path.relative_to(committed).parts
        )
        if generated_files != committed_files:
            return False
        if any(
            (generated / name).read_bytes() != (committed / name).read_bytes()
            for name in generated_files
        ):
            return False
    return True


def copy_generated_inputs(source_root: Path, destination_root: Path) -> None:
    """Copy generated inputs into an explicitly empty destination tree."""
    for relative in (CORPUS_RELATIVE, BENCHMARK_RELATIVE):
        destination = destination_root / relative
        if destination.exists():
            raise HoldoutError("output_not_empty")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_root / relative, destination)


__all__ = [
    "BENCHMARK_RELATIVE",
    "CORPUS_RELATIVE",
    "QUESTION_IDS",
    "RESULT_NAMES",
    "THRESHOLDS",
    "TREATMENTS",
    "VERSION",
    "HoldoutError",
    "HoldoutInputs",
    "HoldoutVerification",
    "compare_generated",
    "copy_generated_inputs",
    "evaluate_verdict",
    "generate_holdout",
    "load_holdout",
    "load_json",
    "verify_holdout",
]
