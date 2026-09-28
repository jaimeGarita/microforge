"""Model-relation semantic rules."""

from collections import Counter

from microforge.domain.spec.errors import SpecSemanticError
from microforge.domain.spec.models import FieldSpec, ModelSpec, RelationSpec, SpecV1
from microforge.domain.spec.types import RelationType


def validate_relations(spec: SpecV1) -> list[SpecSemanticError]:
    """Validate references and field compatibility for model relations."""
    models_by_name = {model.name: model for model in spec.models}
    errors: list[SpecSemanticError] = []
    for source_model in spec.models:
        errors.extend(_validate_local_field_usage(source_model))
        for relation in source_model.relations:
            errors.extend(_validate_relation(source_model, relation, models_by_name))
    return errors


def _validate_relation(
    source_model: ModelSpec,
    relation: RelationSpec,
    models_by_name: dict[str, ModelSpec],
) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    target_model = models_by_name.get(relation.target)
    if target_model is None:
        return [
            SpecSemanticError(
                f"Relation '{relation.name}' references missing target model '{relation.target}'.",
                model=source_model.name,
            )
        ]

    local_field = _fields_by_name(source_model).get(relation.local_field)
    target_field = _fields_by_name(target_model).get(relation.target_field)
    if local_field is None:
        errors.append(
            SpecSemanticError(
                f"Relation '{relation.name}' references missing local field "
                f"'{relation.local_field}'.",
                model=source_model.name,
            )
        )
    if target_field is None:
        errors.append(
            SpecSemanticError(
                f"Relation '{relation.name}' references missing target field "
                f"'{target_model.name}.{relation.target_field}'.",
                model=source_model.name,
            )
        )
    if local_field is None or target_field is None:
        return errors

    if local_field.type != target_field.type:
        errors.append(
            SpecSemanticError(
                f"Relation '{relation.name}' connects fields with incompatible types: "
                f"'{source_model.name}.{local_field.name}' is '{local_field.type.value}', but "
                f"'{target_model.name}.{target_field.name}' is '{target_field.type.value}'.",
                model=source_model.name,
            )
        )
    referenced_field = (
        local_field if relation.relation_type == RelationType.one_to_many else target_field
    )
    referenced_model = (
        source_model if relation.relation_type == RelationType.one_to_many else target_model
    )
    if not referenced_field.primary_key and not referenced_field.unique:
        errors.append(
            SpecSemanticError(
                f"Relation '{relation.name}' referenced field "
                f"'{referenced_model.name}.{referenced_field.name}' must be primary key or unique.",
                model=source_model.name,
            )
        )
    if relation.relation_type == RelationType.many_to_many and not (
        local_field.primary_key or local_field.unique
    ):
        errors.append(
            SpecSemanticError(
                f"Relation '{relation.name}' local association field "
                f"'{source_model.name}.{local_field.name}' must be primary key or unique.",
                model=source_model.name,
            )
        )
    foreign_key_field = (
        target_field
        if relation.relation_type == RelationType.one_to_many
        else local_field
        if relation.relation_type in {RelationType.many_to_one, RelationType.one_to_one}
        else None
    )
    if foreign_key_field is not None and foreign_key_field.auto_increment:
        errors.append(
            SpecSemanticError(
                f"Relation '{relation.name}' foreign-key field "
                f"'{foreign_key_field.name}' cannot be auto increment.",
                model=source_model.name,
            )
        )
    return errors


def _validate_local_field_usage(model: ModelSpec) -> list[SpecSemanticError]:
    counts = Counter(
        relation.local_field
        for relation in model.relations
        if relation.relation_type in {RelationType.many_to_one, RelationType.one_to_one}
    )
    return [
        SpecSemanticError(
            f"Local field '{field_name}' is used by multiple relations.", model=model.name
        )
        for field_name, count in sorted(counts.items())
        if count > 1
    ]


def _fields_by_name(model: ModelSpec) -> dict[str, FieldSpec]:
    return {field.name: field for field in model.fields}
