"""Render Python domain models for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.model_ids import (
    field_is_database_generated,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.python_types import (
    imports_for_model,
    nullable_python_type_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class PythonFieldContext:
    """Field data prepared for Python code templates."""

    name: str
    python_type: str


class DomainModelsRenderer:
    """Render one domain model file per spec model."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        files = [
            ProjectFile(
                path=f"src/{package_name}/domain/models/{to_snake_case(model.name)}.py",
                content=_encode(self._render_model(model)),
            )
            for model in spec.models
        ]
        files.append(
            ProjectFile(
                path=f"src/{package_name}/domain/models/__init__.py",
                content=_encode(""),
            )
        )
        return files

    def _render_model(self, model: ModelSpec) -> str:
        return self.renderer.render(
            "domain/model.py.j2",
            {
                "class_name": model.name,
                "fields": [_field_context(field) for field in model.fields],
                "imports": imports_for_model(model),
            },
        )


def _field_context(field: FieldSpec) -> PythonFieldContext:
    python_type = nullable_python_type_for(field)
    if field_is_database_generated(field):
        python_type = python_type if python_type.endswith(" | None") else f"{python_type} | None"
    return PythonFieldContext(
        name=field.name,
        python_type=python_type,
    )


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
