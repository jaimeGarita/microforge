from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from microforge.domain.spec.types import (
    ApiHttpMethod,
    FieldType,
    Packaging,
    QueryOp,
    TargetFramework,
    TargetLanguage,
)


class SpecModel(BaseModel):
    """Strict base model shared by every versioned spec object."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProjectConfig(SpecModel):
    """Project-level configuration."""

    name: str = "microforge"
    package_name: str = Field(default="microforge", alias="packageName")


class TargetConfig(SpecModel):
    """Code generation target metadata."""

    language: TargetLanguage = TargetLanguage.python
    framework: TargetFramework = TargetFramework.fastapi
    python_version: str = Field(default="3.12", alias="pythonVersion")
    packaging: Packaging = Packaging.poetry


class ServiceConfig(SpecModel):
    """High-level service info."""

    name: str = "microforge"
    description: str | None = None


class QueryParam(SpecModel):
    """Filter parameter used by a query."""

    field: str
    op: QueryOp = QueryOp.eq


class ApiEndpoint(SpecModel):
    """Single HTTP endpoint definition."""

    name: str
    path: str
    method: ApiHttpMethod = ApiHttpMethod.get
    model: str | None = None
    filters: list[QueryParam] = Field(default_factory=list)


class ApiConfig(SpecModel):
    """API surface configuration."""

    base_path: str = Field(default="/api/v1", alias="basePath")
    endpoints: list[ApiEndpoint] = Field(default_factory=list)


class FeatureConfig(SpecModel):
    """Optional features toggles per model."""

    repository: bool = True


class FieldSpec(SpecModel):
    """Field definition for a model."""

    name: str
    type: FieldType
    auto_increment: bool = Field(default=False, alias="autoIncrement")
    default_value: Any | None = Field(default=None, alias="default")
    enum_values: list[Any] = Field(default_factory=list, alias="enum")
    index: bool = False
    max_length: int | None = Field(default=None, alias="maxLength")
    maximum: int | float | None = None
    min_length: int | None = Field(default=None, alias="minLength")
    minimum: int | float | None = None
    nullable: bool = False
    primary_key: bool = Field(default=False, alias="primaryKey")
    unique: bool = False


class QuerySpec(SpecModel):
    """Query definition for a model."""

    name: str
    params: list[QueryParam] = Field(default_factory=list)


class ModelSpec(SpecModel):
    """Model specification (fields, queries, features)."""

    name: str
    fields: list[FieldSpec]
    queries: list[QuerySpec] = Field(default_factory=list)
    features: FeatureConfig = Field(default_factory=FeatureConfig)


class SpecV1(SpecModel):
    """Top-level specification (version 1 schema)."""

    project_config: ProjectConfig = Field(default_factory=ProjectConfig, alias="project")
    spec_version: Literal[1] = Field(default=1, alias="specVersion", frozen=True)
    target: TargetConfig = Field(default_factory=TargetConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    models: list[ModelSpec] = Field(default_factory=list)
