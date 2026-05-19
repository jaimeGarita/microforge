"""Python type helpers for FastAPI code generation."""

from __future__ import annotations

from microforge.domain.spec.models import FieldSpec, ModelSpec
from microforge.domain.spec.types import FieldType

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

    return FIELD_TYPE_MAP[field.type]


def imports_for_model(model: ModelSpec) -> list[str]:
    """Return Python imports required by a model fields."""

    imports = {
        IMPORTS_BY_TYPE[field.type] for field in model.fields if field.type in IMPORTS_BY_TYPE
    }
    return sorted(imports)
