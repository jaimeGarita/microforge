"""Render SQLAlchemy ORM models for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.field_metadata import (
    field_has_default,
    sqlalchemy_default_expression_for,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    table_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.python_types import (
    imports_for_model,
    python_type_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class OrmFieldContext:
    """Field data prepared for SQLAlchemy templates."""

    name: str
    python_type: str
    column_args: str


class OrmModelsRenderer:
    """Render one SQLAlchemy ORM model file per spec model."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/infrastructure/persistence"

        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            ),
            ProjectFile(
                path=f"{base_path}/base.py",
                content=_encode(self.renderer.render("infrastructure/persistence/base.py.j2", {})),
            ),
            ProjectFile(
                path=f"{base_path}/session.py",
                content=_encode(
                    self.renderer.render(
                        "infrastructure/persistence/session.py.j2",
                        {
                            "orm_modules": [to_snake_case(model.name) for model in spec.models],
                            "package_name": package_name,
                        },
                    )
                ),
            ),
        ]

        files.extend(
            ProjectFile(
                path=f"{base_path}/{to_snake_case(model.name)}.py",
                content=_encode(self._render_model(model, package_name)),
            )
            for model in spec.models
        )
        return files

    def _render_model(self, model: ModelSpec, package_name: str) -> str:
        return self.renderer.render(
            "infrastructure/persistence/model.py.j2",
            {
                "class_name": model.name,
                "fields": [_field_context(field) for field in model.fields],
                "imports": imports_for_model(model),
                "package_name": package_name,
                "table_name": table_name_for(model.name),
            },
        )


def _field_context(field: FieldSpec) -> OrmFieldContext:
    return OrmFieldContext(
        name=field.name,
        python_type=_orm_python_type_for(field),
        column_args=_column_args_for(field),
    )


def _column_args_for(field: FieldSpec) -> str:
    args: list[str] = []
    if field.primary_key:
        args.append("primary_key=True")
    if field.auto_increment:
        args.append("autoincrement=True")
    if field.nullable:
        args.append("nullable=True")
    if field.unique:
        args.append("unique=True")
    if field.index:
        args.append("index=True")
    if field_has_default(field):
        args.append(f"default={sqlalchemy_default_expression_for(field)}")
    return ", ".join(args)


def _orm_python_type_for(field: FieldSpec) -> str:
    python_type = python_type_for(field)
    if field.nullable:
        return f"{python_type} | None"
    return python_type


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
