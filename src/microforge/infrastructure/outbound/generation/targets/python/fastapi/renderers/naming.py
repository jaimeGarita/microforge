"""Naming helpers for FastAPI code generation."""

from __future__ import annotations

import re


def to_snake_case(value: str) -> str:
    """Convert a spec name into a Python snake_case identifier."""

    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    return value.strip("_").lower() or "model"


def package_name_for(value: str) -> str:
    """Convert a project package name into a Python package name."""

    return to_snake_case(value) or "generated_service"


def table_name_for(model_name: str) -> str:
    """Return the default table name for a model."""

    return f"{to_snake_case(model_name)}s"
