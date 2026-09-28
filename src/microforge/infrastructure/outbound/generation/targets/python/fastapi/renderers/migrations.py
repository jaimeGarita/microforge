"""Render Alembic configuration and an immutable initial schema migration."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.domain.spec.types import FieldType, RelationType
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    table_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class MigrationColumnContext:
    """Static SQLAlchemy column declaration stored in the initial revision."""

    name: str
    arguments: str


@dataclass(frozen=True)
class MigrationTableContext:
    """Static table declaration stored in the initial revision."""

    name: str
    columns: list[MigrationColumnContext]


class MigrationsRenderer:
    """Render the Alembic environment and baseline revision."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        context = {
            "orm_modules": [to_snake_case(model.name) for model in spec.models],
            "package_name": package_name,
            "tables": _migration_tables(spec),
        }
        return [
            ProjectFile(
                path="alembic.ini",
                content=_encode(self.renderer.render("migrations/alembic.ini.j2", context)),
            ),
            ProjectFile(
                path="migrations/env.py",
                content=_encode(self.renderer.render("migrations/env.py.j2", context)),
            ),
            ProjectFile(
                path="migrations/script.py.mako",
                content=_encode(self.renderer.render("migrations/script.py.mako.j2", context)),
            ),
            ProjectFile(
                path="migrations/versions/0001_initial_schema.py",
                content=_encode(
                    self.renderer.render("migrations/versions/initial_schema.py.j2", context)
                ),
            ),
        ]


def _migration_tables(spec: SpecV1) -> list[MigrationTableContext]:
    tables = [
        MigrationTableContext(
            name=table_name_for(model.name),
            columns=[
                MigrationColumnContext(
                    name=field.name,
                    arguments=_column_arguments(spec, model, field),
                )
                for field in model.fields
            ],
        )
        for model in spec.models
    ]
    for model in spec.models:
        for relation in model.relations:
            if relation.relation_type != RelationType.many_to_many:
                continue
            tables.append(
                MigrationTableContext(
                    name=f"{to_snake_case(model.name)}_{to_snake_case(relation.name)}_association",
                    columns=[
                        MigrationColumnContext(
                            name=f"source_{relation.local_field}",
                            arguments=(
                                f"{_type_expression(_field(model, relation.local_field))}, "
                                f'sa.ForeignKey("{table_name_for(model.name)}.{relation.local_field}"), '
                                "primary_key=True"
                            ),
                        ),
                        MigrationColumnContext(
                            name=f"target_{relation.target_field}",
                            arguments=(
                                f"{_type_expression(_field(_model(spec, relation.target), relation.target_field))}, "
                                f'sa.ForeignKey("{table_name_for(relation.target)}.{relation.target_field}"), '
                                "primary_key=True"
                            ),
                        ),
                    ],
                )
            )
    return tables


def _column_arguments(spec: SpecV1, model: ModelSpec, field: FieldSpec) -> str:
    arguments = [_type_expression(field)]
    foreign_key, relation_unique = _foreign_key_for(spec, model, field.name)
    if foreign_key is not None:
        arguments.append(f'sa.ForeignKey("{foreign_key}")')
    arguments.append(f"nullable={field.nullable}")
    if field.primary_key:
        arguments.append("primary_key=True")
    if field.auto_increment:
        arguments.append("autoincrement=True")
    if field.unique or relation_unique:
        arguments.append("unique=True")
    if field.index:
        arguments.append("index=True")
    return ", ".join(arguments)


def _foreign_key_for(spec: SpecV1, model: ModelSpec, field_name: str) -> tuple[str | None, bool]:
    for relation in model.relations:
        if relation.local_field == field_name and relation.relation_type in {
            RelationType.many_to_one,
            RelationType.one_to_one,
        }:
            return (
                f"{table_name_for(relation.target)}.{relation.target_field}",
                relation.relation_type == RelationType.one_to_one,
            )
    for source in spec.models:
        for relation in source.relations:
            if (
                relation.relation_type == RelationType.one_to_many
                and relation.target == model.name
                and relation.target_field == field_name
            ):
                return f"{table_name_for(source.name)}.{relation.local_field}", False
    return None, False


def _type_expression(field: FieldSpec) -> str:
    return {
        FieldType.string: "sa.String()",
        FieldType.int: "sa.Integer()",
        FieldType.long: "sa.Integer()",
        FieldType.boolean: "sa.Boolean()",
        FieldType.uuid: "sa.Uuid()",
        FieldType.decimal: "sa.Numeric()",
        FieldType.instant: "sa.DateTime()",
        FieldType.date: "sa.Date()",
    }[field.type]


def _model(spec: SpecV1, name: str) -> ModelSpec:
    return next(model for model in spec.models if model.name == name)


def _field(model: ModelSpec, name: str) -> FieldSpec:
    return next(field for field in model.fields if field.name == name)


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
