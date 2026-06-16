"""Semantic validation for spec objects."""

from __future__ import annotations

from microforge.domain.spec.errors import SpecSemanticError, SpecValidationErrors
from microforge.domain.spec.models import ModelSpec, SpecV1
from microforge.domain.spec.types import TargetFramework, TargetLanguage


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
        if f.auto_increment and not f.primary_key:
            errors.append(
                SpecSemanticError(
                    f"Field '{f.name}' is auto_increment but not primary_key.",
                    model=model.name,
                )
            )
    return errors
