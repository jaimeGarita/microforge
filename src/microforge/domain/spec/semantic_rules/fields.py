"""Model-field semantic rules."""

from microforge.domain.spec.errors import SpecSemanticError
from microforge.domain.spec.models import ModelSpec, SpecV1
from microforge.domain.spec.types import FieldType

AUTO_INCREMENT_TYPES = {FieldType.int, FieldType.long}
NUMERIC_TYPES = {FieldType.int, FieldType.long, FieldType.decimal}
STRING_TYPES = {FieldType.string}


def validate_fields(spec: SpecV1) -> list[SpecSemanticError]:
    """Validate generated-field configuration and field metadata."""
    errors: list[SpecSemanticError] = []
    for model in spec.models:
        errors.extend(_validate_generated_fields(model))
        errors.extend(_validate_field_metadata(model))
    return errors


def _validate_generated_fields(model: ModelSpec) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    for field in model.fields:
        if field.primary_key and field.nullable:
            errors.append(
                SpecSemanticError(
                    f"Field '{field.name}' is primary_key but nullable.", model=model.name
                )
            )
        if field.auto_increment and not field.primary_key:
            errors.append(
                SpecSemanticError(
                    f"Field '{field.name}' is auto_increment but not primary_key.", model=model.name
                )
            )
        if field.auto_increment and field.type not in AUTO_INCREMENT_TYPES:
            errors.append(
                SpecSemanticError(
                    f"Field '{field.name}' is auto_increment but type '{field.type.value}' "
                    "is not autoincrementable. Only int and long are supported.",
                    model=model.name,
                )
            )
    return errors


def _validate_field_metadata(model: ModelSpec) -> list[SpecSemanticError]:
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
                    f"Field '{field.name}' has minLength greater than maxLength.", model=model.name
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
                    f"Field '{field.name}' has minimum greater than maximum.", model=model.name
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
    model_name: str, field_name: str, field_type: FieldType, values: list[object]
) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
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
                f"Field '{field_name}' default value {value!r} is not in enum.", model=model_name
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
