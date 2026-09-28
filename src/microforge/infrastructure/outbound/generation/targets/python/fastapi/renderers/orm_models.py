"""Render SQLAlchemy ORM models for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, RelationSpec, SpecV1
from microforge.domain.spec.types import RelationType
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


@dataclass(frozen=True)
class ForeignKeyContext:
    """Foreign-key target attached to an ORM field."""

    target_model: str
    target_field: str
    unique: bool = False


@dataclass(frozen=True)
class OrmRelationContext:
    """Relationship property prepared for the ORM template."""

    name: str
    python_type: str
    target_class: str
    arguments: str = ""


@dataclass(frozen=True)
class AssociationContext:
    """Many-to-many association table prepared for the ORM template."""

    variable_name: str
    table_name: str
    source_column: str
    source_reference: str
    target_column: str
    target_reference: str


@dataclass(frozen=True)
class RelatedModelContext:
    """A related ORM model imported only for static type checking."""

    class_name: str
    module_name: str


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
                content=_encode(self._render_model(spec, model, package_name)),
            )
            for model in spec.models
        )
        return files

    def _render_model(self, spec: SpecV1, model: ModelSpec, package_name: str) -> str:
        foreign_keys = _foreign_keys_for_model(spec, model)
        associations = _association_contexts(model)
        return self.renderer.render(
            "infrastructure/persistence/model.py.j2",
            {
                "class_name": model.name,
                "fields": [
                    _field_context(field, foreign_keys.get(field.name)) for field in model.fields
                ],
                "has_associations": bool(associations),
                "has_foreign_keys": bool(foreign_keys) or bool(associations),
                "has_relationships": bool(model.relations),
                "imports": imports_for_model(model),
                "package_name": package_name,
                "associations": associations,
                "related_models": [
                    RelatedModelContext(
                        class_name=f"{target}ORM", module_name=to_snake_case(target)
                    )
                    for target in sorted({relation.target for relation in model.relations})
                ],
                "relations": [
                    _relation_context(relation, model, spec) for relation in model.relations
                ],
                "table_name": table_name_for(model.name),
            },
        )


def _field_context(
    field: FieldSpec, foreign_key: ForeignKeyContext | None = None
) -> OrmFieldContext:
    return OrmFieldContext(
        name=field.name,
        python_type=_orm_python_type_for(field),
        column_args=_column_args_for(field, foreign_key),
    )


def _column_args_for(field: FieldSpec, foreign_key: ForeignKeyContext | None = None) -> str:
    args: list[str] = []
    if foreign_key is not None:
        target_table = table_name_for(foreign_key.target_model)
        args.append(f'ForeignKey("{target_table}.{foreign_key.target_field}")')
    if field.primary_key:
        args.append("primary_key=True")
    if field.auto_increment:
        args.append("autoincrement=True")
    if field.nullable:
        args.append("nullable=True")
    if field.unique or (foreign_key is not None and foreign_key.unique):
        args.append("unique=True")
    if field.index:
        args.append("index=True")
    if field_has_default(field):
        args.append(f"default={sqlalchemy_default_expression_for(field)}")
    return ", ".join(args)


def _foreign_keys_for_model(spec: SpecV1, model: ModelSpec) -> dict[str, ForeignKeyContext]:
    foreign_keys: dict[str, ForeignKeyContext] = {}
    for relation in model.relations:
        if relation.relation_type in {RelationType.many_to_one, RelationType.one_to_one}:
            foreign_keys[relation.local_field] = ForeignKeyContext(
                target_model=relation.target,
                target_field=relation.target_field,
                unique=relation.relation_type == RelationType.one_to_one,
            )
    for source_model in spec.models:
        for relation in source_model.relations:
            if relation.relation_type == RelationType.one_to_many and relation.target == model.name:
                foreign_keys[relation.target_field] = ForeignKeyContext(
                    target_model=source_model.name,
                    target_field=relation.local_field,
                )
    return foreign_keys


def _relation_context(relation: RelationSpec, model: ModelSpec, spec: SpecV1) -> OrmRelationContext:
    target_class = f"{relation.target}ORM"
    if relation.relation_type in {RelationType.one_to_many, RelationType.many_to_many}:
        python_type = f'list["{target_class}"]'
    else:
        local_field = next(field for field in model.fields if field.name == relation.local_field)
        python_type = f'"{target_class}"'
        if local_field.nullable:
            python_type = f'"{target_class} | None"'

    arguments: list[str] = []
    if relation.relation_type == RelationType.one_to_one:
        arguments.append("uselist=False")
    elif relation.relation_type == RelationType.many_to_many:
        arguments.append(f"secondary={_association_name(model, relation)}")
    inverse = _inverse_relation_for(model, relation, spec)
    if inverse is not None:
        arguments.append(f'back_populates="{inverse.name}"')
    return OrmRelationContext(
        name=relation.name,
        python_type=python_type,
        target_class=target_class,
        arguments=", ".join(arguments),
    )


def _inverse_relation_for(
    source_model: ModelSpec, relation: RelationSpec, spec: SpecV1
) -> RelationSpec | None:
    target_model = next((model for model in spec.models if model.name == relation.target), None)
    if target_model is None:
        return None
    inverse_types = {
        RelationType.many_to_one: RelationType.one_to_many,
        RelationType.one_to_many: RelationType.many_to_one,
        RelationType.one_to_one: RelationType.one_to_one,
    }
    expected_type = inverse_types.get(relation.relation_type)
    if expected_type is None:
        return None
    return next(
        (
            candidate
            for candidate in target_model.relations
            if candidate.relation_type == expected_type
            and candidate.target == source_model.name
            and candidate.local_field == relation.target_field
            and candidate.target_field == relation.local_field
        ),
        None,
    )


def _association_contexts(model: ModelSpec) -> list[AssociationContext]:
    return [
        AssociationContext(
            variable_name=_association_name(model, relation),
            table_name=_association_name(model, relation),
            source_column=f"source_{relation.local_field}",
            source_reference=f"{table_name_for(model.name)}.{relation.local_field}",
            target_column=f"target_{relation.target_field}",
            target_reference=f"{table_name_for(relation.target)}.{relation.target_field}",
        )
        for relation in model.relations
        if relation.relation_type == RelationType.many_to_many
    ]


def _association_name(model: ModelSpec, relation: RelationSpec) -> str:
    return f"{to_snake_case(model.name)}_{to_snake_case(relation.name)}_association"


def _orm_python_type_for(field: FieldSpec) -> str:
    python_type = python_type_for(field)
    if field.nullable:
        return f"{python_type} | None"
    return python_type


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
