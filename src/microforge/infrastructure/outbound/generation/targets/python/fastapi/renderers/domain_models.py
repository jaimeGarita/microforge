"""Render Python domain models for FastAPI projects."""

from __future__ import annotations

import re
from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.domain.spec.types import FieldType
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer

FIELD_TYPE_MAP = {
    FieldType.string: "str",
    FieldType.int: "int",
    FieldType.long: "int",
    FieldType.boolean: "bool",
    FieldType.uuid: "UUID",
    FieldType.decimal: "Decimal",
    FieldType.instant: "datetime",
    FieldType.date: "date",
}

IMPORTS_BY_TYPE = {
    FieldType.uuid: "from uuid import UUID",
    FieldType.decimal: "from decimal import Decimal",
    FieldType.instant: "from datetime import datetime",
    FieldType.date: "from datetime import date",
}


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
        package_name = _to_snake_case(spec.project_config.package_name)
        files = [
            ProjectFile(
                path=f"src/{package_name}/domain/models/{_to_snake_case(model.name)}.py",
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
                "imports": _imports_for_model(model),
            },
        )


def _field_context(field: FieldSpec) -> PythonFieldContext:
    return PythonFieldContext(
        name=field.name,
        python_type=FIELD_TYPE_MAP[field.type],
    )


def _imports_for_model(model: ModelSpec) -> list[str]:
    imports = {
        IMPORTS_BY_TYPE[field.type] for field in model.fields if field.type in IMPORTS_BY_TYPE
    }
    return sorted(imports)


def _to_snake_case(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    return value.strip("_").lower() or "model"


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
