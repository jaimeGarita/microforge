"""Render persistence mapper classes for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class MapperFieldContext:
    """Field mapping data prepared for mapper templates."""

    name: str


class MappersRenderer:
    """Render mapper classes between domain models and ORM models."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/infrastructure/persistence/mappers"
        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            )
        ]

        for model in spec.models:
            files.append(
                ProjectFile(
                    path=f"{base_path}/{to_snake_case(model.name)}_mapper.py",
                    content=_encode(self._render_mapper(model, package_name)),
                )
            )
        return files

    def _render_mapper(self, model: ModelSpec, package_name: str) -> str:
        return self.renderer.render(
            "infrastructure/persistence/mappers/mapper.py.j2",
            {
                "class_name": f"{model.name}Mapper",
                "domain_class_name": model.name,
                "domain_module": to_snake_case(model.name),
                "fields": [_field_context(field) for field in model.fields],
                "orm_class_name": f"{model.name}ORM",
                "orm_module": to_snake_case(model.name),
                "package_name": package_name,
            },
        )


def _field_context(field: FieldSpec) -> MapperFieldContext:
    return MapperFieldContext(name=field.name)


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
