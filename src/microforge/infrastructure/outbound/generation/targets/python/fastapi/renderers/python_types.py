"""Python type helpers for FastAPI code generation."""

from __future__ import annotations

from microforge.domain.spec.models import FieldSpec, ModelSpec
from microforge.domain.spec.types import FieldType
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.field_metadata import (
    enum_type_for,
)

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


def python_type_for(field: FieldSpec) -> str:
    """Return the Python type annotation for a spec field."""

    enum_type = enum_type_for(field)
    if enum_type is not None:
        return enum_type
    return FIELD_TYPE_MAP[field.type]


def nullable_python_type_for(field: FieldSpec) -> str:
    """Return the Python type annotation including nullable metadata."""

    python_type = python_type_for(field)
    if field.nullable:
        return f"{python_type} | None"
    return python_type


def imports_for_model(model: ModelSpec) -> list[str]:
    """Return Python imports required by a model fields."""

    return imports_for_fields(model.fields)


def imports_for_fields(fields: list[FieldSpec]) -> list[str]:
    """Return Python imports required by a list of fields."""

    imports = {IMPORTS_BY_TYPE[field.type] for field in fields if field.type in IMPORTS_BY_TYPE}
    if any(field.enum_values for field in fields):
        imports.add("from typing import Literal")
    return sorted(imports)
