"""Render Pydantic schemas for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ApiEndpoint, FieldSpec, ModelSpec, SpecV1
from microforge.domain.spec.types import ApiHttpMethod
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    endpoint_targets_model,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.model_ids import (
    field_is_generated_on_create,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.python_types import (
    imports_for_fields,
    python_type_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class SchemaFieldContext:
    """Field data prepared for Pydantic schema templates."""

    name: str
    python_type: str


class SchemasRenderer:
    """Render Pydantic schema files required by API endpoints."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/infrastructure/inbound/api/schemas"

        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            )
        ]

        for model in spec.models:
            files.extend(self._render_model_files(model, spec.api.endpoints, base_path))
        return files

    def _render_model_files(
        self,
        model: ModelSpec,
        endpoints: list[ApiEndpoint],
        base_path: str,
    ) -> list[ProjectFile]:
        schema_plan = _schema_plan_for(model, endpoints)
        model_path = f"{base_path}/{to_snake_case(model.name)}"
        files = [
            ProjectFile(
                path=f"{model_path}/__init__.py",
                content=_encode(""),
            )
        ]
        if schema_plan.create_fields:
            files.append(
                self._schema_file(
                    path=f"{model_path}/{to_snake_case(model.name)}_create.py",
                    class_name=f"{model.name}Create",
                    fields=schema_plan.create_fields,
                )
            )
        if schema_plan.read_fields:
            files.append(
                self._schema_file(
                    path=f"{model_path}/{to_snake_case(model.name)}_read.py",
                    class_name=f"{model.name}Read",
                    fields=schema_plan.read_fields,
                )
            )
        if schema_plan.update_fields:
            files.append(
                self._schema_file(
                    path=f"{model_path}/{to_snake_case(model.name)}_update.py",
                    class_name=f"{model.name}Update",
                    fields=schema_plan.update_fields,
                )
            )
        return files

    def _schema_file(
        self,
        path: str,
        class_name: str,
        fields: list[FieldSpec],
    ) -> ProjectFile:
        return ProjectFile(
            path=path,
            content=_encode(
                self.renderer.render(
                    "infrastructure/inbound/api/schemas/schema.py.j2",
                    {
                        "class_name": class_name,
                        "fields": [_field_context(field) for field in fields],
                        "imports": imports_for_fields(fields),
                    },
                )
            ),
        )


@dataclass(frozen=True)
class SchemaPlan:
    """Schema classes and fields required by API endpoints."""

    create_fields: list[FieldSpec]
    read_fields: list[FieldSpec]
    update_fields: list[FieldSpec]


def _schema_plan_for(model: ModelSpec, endpoints: list[ApiEndpoint]) -> SchemaPlan:
    methods = {endpoint.method for endpoint in endpoints if endpoint_targets_model(endpoint, model)}
    writable_fields = _writable_fields(model)
    return SchemaPlan(
        create_fields=writable_fields if ApiHttpMethod.post in methods else [],
        read_fields=model.fields if methods - {ApiHttpMethod.delete} else [],
        update_fields=(
            writable_fields
            if methods.intersection({ApiHttpMethod.put, ApiHttpMethod.patch})
            else []
        ),
    )


def _writable_fields(model: ModelSpec) -> list[FieldSpec]:
    return [field for field in model.fields if not field_is_generated_on_create(field)]


def _field_context(field: FieldSpec) -> SchemaFieldContext:
    return SchemaFieldContext(
        name=field.name,
        python_type=python_type_for(field),
    )


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
