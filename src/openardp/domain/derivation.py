"""Disposable derived-artifact contract."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue, field_validator, model_validator

from openardp.domain.common import (
    ComponentDescriptor,
    DataTrustClassification,
    ExtensibleModel,
    NonEmptyStr,
    Sha256Id,
    SupportedSchemaVersion,
    TrustZone,
    UtcDatetime,
    ensure_json_value,
)
from openardp.domain.identity import derivation_artifact_id


class DerivationState(StrEnum):
    """Lifecycle of a disposable derived artifact."""

    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"
    STALE = "STALE"
    REVOKED = "REVOKED"


class DerivationRecord(ExtensibleModel):
    """Reproducibility, trust and lifecycle facts for one derived artifact."""

    schema_version: SupportedSchemaVersion
    artifact_id: Sha256Id
    state: DerivationState
    generator: ComponentDescriptor
    model_id: NonEmptyStr | None = None
    input_hashes: tuple[Sha256Id, ...] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    config_hash: Sha256Id
    prompt_hash: Sha256Id | None = None
    created_at: UtcDatetime
    completed_at: UtcDatetime | None = None
    output_hash: Sha256Id | None = None
    quality_signals: dict[str, JsonValue] = Field(default_factory=dict)
    trust: DataTrustClassification

    @field_validator("quality_signals", mode="before")
    @classmethod
    def _quality_signals_are_json(cls, value: object) -> object:
        return ensure_json_value(value, path="$.quality_signals")

    @model_validator(mode="after")
    def _recipe_lifecycle_and_trust_are_consistent(self) -> DerivationRecord:
        if len(set(self.input_hashes)) != len(self.input_hashes):
            raise ValueError("input_hashes must be unique while preserving order")
        expected = derivation_artifact_id(
            input_hashes=self.input_hashes,
            generator_name=self.generator.name,
            generator_version=self.generator.version,
            generator_profile=self.generator.profile,
            model_id=self.model_id,
            config_hash=self.config_hash,
            prompt_hash=self.prompt_hash,
        )
        if self.artifact_id != expected:
            raise ValueError("artifact_id does not match the declared derivation recipe")
        if self.completed_at is not None and self.completed_at < self.created_at:
            raise ValueError("completed_at cannot be earlier than created_at")
        if self.state is DerivationState.PENDING:
            if self.completed_at is not None or self.output_hash is not None:
                raise ValueError("PENDING derivation cannot have completion or output")
        elif self.state is DerivationState.FAILED:
            if self.completed_at is None or self.output_hash is not None:
                raise ValueError("FAILED derivation requires completion and no output_hash")
        elif self.completed_at is None or self.output_hash is None:
            raise ValueError(f"{self.state.value} derivation requires completion and output_hash")
        if self.trust.zone is not TrustZone.MODEL_DERIVED:
            raise ValueError("derived artifact trust zone must be model_derived")
        return self
