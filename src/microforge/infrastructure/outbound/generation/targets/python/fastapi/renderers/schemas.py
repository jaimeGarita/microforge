"""Render Pydantic schemas for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.python_types import (
    imports_for_model,
    python_type_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class SchemaFieldContext:
    """Field data prepared for Pydantic schema templates."""

    name: str
    python_type: str


class SchemasRenderer:
    """Render one Pydantic schema file per spec model."""

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

        files.extend(
            ProjectFile(
                path=f"{base_path}/{to_snake_case(model.name)}.py",
                content=_encode(self._render_model(model)),
            )
            for model in spec.models
        )
        return files

    def _render_model(self, model: ModelSpec) -> str:
        return self.renderer.render(
            "infrastructure/inbound/api/schemas/model.py.j2",
            {
                "class_name": model.name,
                "create_fields": [_field_context(field) for field in _create_fields(model)],
                "imports": imports_for_model(model),
                "read_fields": [_field_context(field) for field in model.fields],
            },
        )


def _create_fields(model: ModelSpec) -> list[FieldSpec]:
    return [field for field in model.fields if field.name != "id"]


def _field_context(field: FieldSpec) -> SchemaFieldContext:
    return SchemaFieldContext(
        name=field.name,
        python_type=python_type_for(field),
    )


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
