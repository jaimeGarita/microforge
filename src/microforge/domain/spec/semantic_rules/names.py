"""Generated-name and uniqueness semantic rules."""

from __future__ import annotations

import keyword
import re
from collections import Counter

from microforge.domain.spec.errors import SpecSemanticError
from microforge.domain.spec.models import SpecV1


def validate_names(spec: SpecV1) -> list[SpecSemanticError]:
    """Validate identifiers, duplicates, and post-normalization collisions."""
    return [*_validate_generated_names(spec), *_validate_unique_names(spec)]


def _validate_generated_names(spec: SpecV1) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    package_name = _python_name(spec.project_config.package_name)
    if not _is_python_identifier(package_name):
        errors.append(
            SpecSemanticError(
                f"Project packageName '{spec.project_config.package_name}' does not produce a "
                "valid Python package identifier."
            )
        )
    for model in spec.models:
        if not _is_python_identifier(model.name):
            errors.append(
                SpecSemanticError(
                    f"Model name '{model.name}' is not a valid Python identifier.", model=model.name
                )
            )
        for field in model.fields:
            if not _is_python_identifier(field.name):
                errors.append(
                    SpecSemanticError(
                        f"Field name '{field.name}' is not a valid Python identifier.",
                        model=model.name,
                    )
                )
        for query in model.queries:
            if not _is_python_identifier(_python_name(query.name)):
                errors.append(
                    SpecSemanticError(
                        f"Query name '{query.name}' does not produce a valid Python identifier.",
                        model=model.name,
                    )
                )
        for relation in model.relations:
            if not _is_python_identifier(relation.name):
                errors.append(
                    SpecSemanticError(
                        f"Relation name '{relation.name}' is not a valid Python identifier.",
                        model=model.name,
                    )
                )
    for endpoint in spec.api.endpoints:
        if not _is_python_identifier(_python_name(endpoint.name)):
            errors.append(
                SpecSemanticError(
                    f"Endpoint name '{endpoint.name}' does not produce a valid Python identifier."
                )
            )
    return errors


def _validate_unique_names(spec: SpecV1) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    errors.extend(_duplicate_errors("Model", [model.name for model in spec.models]))
    errors.extend(_normalized_collision_errors("Model", [model.name for model in spec.models]))
    errors.extend(_duplicate_errors("Endpoint", [endpoint.name for endpoint in spec.api.endpoints]))
    errors.extend(
        _normalized_collision_errors("Endpoint", [endpoint.name for endpoint in spec.api.endpoints])
    )
    for model in spec.models:
        errors.extend(
            _duplicate_errors("Field", [field.name for field in model.fields], model=model.name)
        )
        errors.extend(
            _normalized_collision_errors(
                "Field", [field.name for field in model.fields], model=model.name
            )
        )
        errors.extend(
            _duplicate_errors("Query", [query.name for query in model.queries], model=model.name)
        )
        errors.extend(
            _normalized_collision_errors(
                "Query", [query.name for query in model.queries], model=model.name
            )
        )
        errors.extend(
            _duplicate_errors(
                "Relation", [relation.name for relation in model.relations], model=model.name
            )
        )
        errors.extend(
            _normalized_collision_errors(
                "Relation", [relation.name for relation in model.relations], model=model.name
            )
        )
    return errors


def _duplicate_errors(
    kind: str, names: list[str], *, model: str | None = None
) -> list[SpecSemanticError]:
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    return [
        SpecSemanticError(f"{kind} name '{name}' is duplicated.", model=model)
        for name in duplicates
    ]


def _normalized_collision_errors(
    kind: str, names: list[str], *, model: str | None = None
) -> list[SpecSemanticError]:
    by_normalized: dict[str, set[str]] = {}
    for name in names:
        by_normalized.setdefault(_python_name(name), set()).add(name)
    return [
        SpecSemanticError(
            f"{kind} names {sorted(originals)} collide after Python name normalization "
            f"as '{normalized}'.",
            model=model,
        )
        for normalized, originals in sorted(by_normalized.items())
        if len(originals) > 1
    ]


def _python_name(value: str) -> str:
    """Mirror the target's snake-case normalization without importing infrastructure."""
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    return value.strip("_").lower() or "model"


def _is_python_identifier(value: str) -> bool:
    return value.isidentifier() and not keyword.iskeyword(value)
