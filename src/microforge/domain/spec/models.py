from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from microforge.domain.spec.types import (
    ApiHttpMethod,
    FieldType,
    Packaging,
    QueryOp,
    TargetFramework,
    TargetLanguage,
)


class ProjectConfig(BaseModel):
    """Project-level configuration."""

    name: str = "microforge"
    package_name: str = Field(default="microforge", alias="packageName")


class TargetConfig(BaseModel):
    """Code generation target metadata."""

    language: TargetLanguage = TargetLanguage.python
    framework: TargetFramework = TargetFramework.fastapi
    python_version: str = Field(default="3.12", alias="pythonVersion")
    packaging: Packaging = Packaging.poetry


class ServiceConfig(BaseModel):
    """High-level service info."""

    name: str = "microforge"
    description: str | None = None


class ApiEndpoint(BaseModel):
    """Single HTTP endpoint definition."""

    name: str
    path: str
    method: ApiHttpMethod = ApiHttpMethod.get


class ApiConfig(BaseModel):
    """API surface configuration."""

    base_path: str = Field(default="/api/v1", alias="basePath")
    endpoints: List[ApiEndpoint] = Field(default_factory=list)


class FeatureConfig(BaseModel):
    """Optional features toggles per model."""

    repository: bool = True


class FieldSpec(BaseModel):
    """Field definition for a model."""

    name: str
    type: FieldType


class QueryParam(BaseModel):
    """Filter parameter used by a query."""

    field: str
    op: QueryOp = QueryOp.eq


class QuerySpec(BaseModel):
    """Query definition for a model."""

    name: str
    params: List[QueryParam] = Field(default_factory=list)


class ModelSpec(BaseModel):
    """Model specification (fields, queries, features)."""

    name: str
    fields: List[FieldSpec]
    queries: List[QuerySpec] = Field(default_factory=list)
    features: FeatureConfig = Field(default_factory=FeatureConfig)


class SpecV1(BaseModel):
    """Top-level specification (version 1 schema)."""

    project_config: ProjectConfig = Field(default_factory=ProjectConfig, alias="project")
    spec_version: int = Field(default=1, alias="specVersion", frozen=True)
    target: TargetConfig = Field(default_factory=TargetConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    models: List[ModelSpec] = Field(default_factory=list)
    model_config = ConfigDict(populate_by_name=True)
