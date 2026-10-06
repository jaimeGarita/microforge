"""Typed request and response models for Jev SystemOne."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JevIndexCandidate(BaseModel):
    """Compact context for a field whose database index can be evaluated."""

    model_name: str
    field_name: str
    field_type: str
    already_indexed: bool
    used_in_filters: bool
    used_in_relations: bool
    query_operations: list[str]
    endpoint_filters: list[str]
    named_queries: list[str]
    relation_usage: list[str]


class JevIndexState(BaseModel):
    """The reduced project state sent to Jev."""

    candidates: list[JevIndexCandidate]


class JevChoiceQuestion(BaseModel):
    """A choice question in the SystemOne request."""

    type: Literal["choice"] = "choice"
    instructions: str
    criteria: dict[str, str]


class JevRequest(BaseModel):
    """Typed payload for one Jev SystemOne request."""

    model_config = ConfigDict(populate_by_name=True)

    model: str = "jev-latest"
    state: JevIndexState
    questions: dict[str, JevChoiceQuestion]


class JevChoiceAnswer(BaseModel):
    """Validated answer returned for one candidate."""

    type: Literal["choice"]
    choice: Literal["recommended", "unnecessary", "human_review"]
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]


class JevResponse(BaseModel):
    """Typed SystemOne response."""

    model: str | None = None
    model_version: str | None = None
    answers: dict[str, JevChoiceAnswer]
