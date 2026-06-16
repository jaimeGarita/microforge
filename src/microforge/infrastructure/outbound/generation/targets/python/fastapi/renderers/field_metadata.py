"""Helpers for rendering field metadata."""

from __future__ import annotations

from typing import Any

from microforge.domain.spec.models import FieldSpec
from microforge.domain.spec.types import FieldType


def field_has_default(field: FieldSpec) -> bool:
    """Return whether a default was explicitly configured."""

    return "default_value" in field.model_fields_set


def python_literal(value: Any) -> str:
    """Return a Python expression for a scalar spec value."""

    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return "None"
    return repr(value)


def default_expression_for(field: FieldSpec) -> str:
    """Return a Python expression for a field default."""

    if field.type == FieldType.decimal and field.default_value is not None:
        return f"Decimal({str(field.default_value)!r})"
    return python_literal(field.default_value)


def enum_type_for(field: FieldSpec) -> str | None:
    """Return a Literal type expression for enum fields."""

    if not field.enum_values:
        return None
    values = ", ".join(python_literal(value) for value in field.enum_values)
    return f"Literal[{values}]"


def pydantic_field_args_for(field: FieldSpec) -> list[str]:
    """Return Pydantic Field keyword arguments for metadata constraints."""

    args: list[str] = []
    if field_has_default(field):
        args.append(f"default={default_expression_for(field)}")
    if field.min_length is not None:
        args.append(f"min_length={field.min_length}")
    if field.max_length is not None:
        args.append(f"max_length={field.max_length}")
    if field.minimum is not None:
        args.append(f"ge={field.minimum}")
    if field.maximum is not None:
        args.append(f"le={field.maximum}")
    return args


def sqlalchemy_default_expression_for(field: FieldSpec) -> str:
    """Return a SQLAlchemy mapped_column default expression."""

    if field.type == FieldType.decimal and field.default_value is not None:
        return f"Decimal({str(field.default_value)!r})"
    return python_literal(field.default_value)


def default_needs_decimal_import(field: FieldSpec) -> bool:
    """Return whether rendering the default requires Decimal."""

    return (
        field.type == FieldType.decimal
        and field.default_value is not None
        and field_has_default(field)
    )
