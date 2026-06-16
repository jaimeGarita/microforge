"""Semantic validation for spec objects."""

from __future__ import annotations

from microforge.domain.spec.errors import SpecSemanticError, SpecValidationErrors
from microforge.domain.spec.models import ModelSpec, SpecV1
from microforge.domain.spec.types import FieldType, TargetFramework, TargetLanguage

AUTO_INCREMENT_TYPES = {FieldType.int, FieldType.long}
NUMERIC_TYPES = {FieldType.int, FieldType.long, FieldType.decimal}
STRING_TYPES = {FieldType.string}


def validate_semantics(spec: SpecV1) -> None:
    """Run all semantic checks for a spec and report all violations together."""
    errors: list[SpecSemanticError] = []
    for rule in (_validate_target_v1, _validate_model_rules):
        errors.extend(rule(spec))
    if errors:
        raise SpecValidationErrors(errors)


def _validate_target_v1(spec: SpecV1) -> list[SpecSemanticError]:
    """v1 only supports Python + FastAPI targets."""
    errors: list[SpecSemanticError] = []
    if (
        spec.target.language != TargetLanguage.python
        or spec.target.framework != TargetFramework.fastapi
    ):
        errors.append(SpecSemanticError("v1 only supports target: python + fastapi."))
    return errors


def _validate_model_rules(spec: SpecV1) -> list[SpecSemanticError]:
    """Run model-specific semantic checks."""
    errors: list[SpecSemanticError] = []
    model_fields = _index_model_fields(spec)
    errors.extend(_validate_queries_refer_existing_fields(spec, model_fields))
    errors.extend(_validate_feature_coherence(spec))
    for model in spec.models:
        errors.extend(_validate_generated_fields(model))
        errors.extend(_validate_field_metadata(model))
    return errors


def _index_model_fields(spec: SpecV1) -> dict[str, set[str]]:
    """Return a mapping of model name -> set of field names."""
    return {m.name: {f.name for f in m.fields} for m in spec.models}


def _validate_queries_refer_existing_fields(
    spec: SpecV1,
    model_fields: dict[str, set[str]],
) -> list[SpecSemanticError]:
    """Ensure every query parameter points to an existing field."""
    errors: list[SpecSemanticError] = []
    for m in spec.models:
        allowed = model_fields[m.name]
        for q in m.queries:
            unknown = [p.field for p in q.params if p.field not in allowed]
            if unknown:
                errors.append(
                    SpecSemanticError(
                        f"Query '{q.name}' references missing fields: {unknown}. "
                        f"Valid fields: {sorted(allowed)}",
                        model=m.name,
                    )
                )
    return errors


def _validate_feature_coherence(spec: SpecV1) -> list[SpecSemanticError]:
    """Check that declared features align with the model configuration."""
    errors: list[SpecSemanticError] = []
    for m in spec.models:
        if not m.features.repository and m.queries:
            errors.append(
                SpecSemanticError(
                    "Queries are defined but features.repository is false.",
                    model=m.name,
                )
            )
    return errors


def _validate_generated_fields(model: ModelSpec) -> list[SpecSemanticError]:
    """Check that generated fields are properly configured."""
    errors: list[SpecSemanticError] = []
    for f in model.fields:
        if f.primary_key and f.nullable:
            errors.append(
                SpecSemanticError(
                    f"Field '{f.name}' is primary_key but nullable.",
                    model=model.name,
                )
            )
        if f.auto_increment and not f.primary_key:
            errors.append(
                SpecSemanticError(
                    f"Field '{f.name}' is auto_increment but not primary_key.",
                    model=model.name,
                )
            )
        if f.auto_increment and f.type not in AUTO_INCREMENT_TYPES:
            errors.append(
                SpecSemanticError(
                    f"Field '{f.name}' is auto_increment but type '{f.type.value}' "
                    "is not autoincrementable. Only int and long are supported.",
                    model=model.name,
                )
            )
    return errors


def _validate_field_metadata(model: ModelSpec) -> list[SpecSemanticError]:
    """Check field metadata such as constraints, defaults and enums."""
    errors: list[SpecSemanticError] = []
    for field in model.fields:
        if (
            field.min_length is not None or field.max_length is not None
        ) and field.type not in STRING_TYPES:
            errors.append(
                SpecSemanticError(
                    f"Field '{field.name}' uses minLength/maxLength but type "
                    f"'{field.type.value}' is not string.",
                    model=model.name,
                )
            )
        if (
            field.min_length is not None
            and field.max_length is not None
            and field.min_length > field.max_length
        ):
            errors.append(
                SpecSemanticError(
                    f"Field '{field.name}' has minLength greater than maxLength.",
                    model=model.name,
                )
            )
        if (
            field.minimum is not None or field.maximum is not None
        ) and field.type not in NUMERIC_TYPES:
            errors.append(
                SpecSemanticError(
                    f"Field '{field.name}' uses minimum/maximum but type "
                    f"'{field.type.value}' is not numeric.",
                    model=model.name,
                )
            )
        if (
            field.minimum is not None
            and field.maximum is not None
            and field.minimum > field.maximum
        ):
            errors.append(
                SpecSemanticError(
                    f"Field '{field.name}' has minimum greater than maximum.",
                    model=model.name,
                )
            )
        if field.enum_values:
            errors.extend(
                _validate_enum_values(model.name, field.name, field.type, field.enum_values)
            )
        if "default_value" in field.model_fields_set:
            errors.extend(
                _validate_default_value(
                    model.name,
                    field.name,
                    field.type,
                    field.default_value,
                    field.enum_values,
                )
            )
    return errors


def _validate_enum_values(
    model_name: str,
    field_name: str,
    field_type: FieldType,
    values: list[object],
) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    if not values:
        return errors
    for value in values:
        if not _value_matches_type(value, field_type):
            errors.append(
                SpecSemanticError(
                    f"Field '{field_name}' enum value {value!r} does not match "
                    f"type '{field_type.value}'.",
                    model=model_name,
                )
            )
    return errors


def _validate_default_value(
    model_name: str,
    field_name: str,
    field_type: FieldType,
    value: object,
    enum_values: list[object],
) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    if value is not None and not _value_matches_type(value, field_type):
        errors.append(
            SpecSemanticError(
                f"Field '{field_name}' default value {value!r} does not match "
                f"type '{field_type.value}'.",
                model=model_name,
            )
        )
    if enum_values and value not in enum_values:
        errors.append(
            SpecSemanticError(
                f"Field '{field_name}' default value {value!r} is not in enum.",
                model=model_name,
            )
        )
    return errors


def _value_matches_type(value: object, field_type: FieldType) -> bool:
    if field_type == FieldType.string:
        return isinstance(value, str)
    if field_type in {FieldType.int, FieldType.long}:
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == FieldType.boolean:
        return isinstance(value, bool)
    if field_type == FieldType.decimal:
        return isinstance(value, int | float | str) and not isinstance(value, bool)
    return True
