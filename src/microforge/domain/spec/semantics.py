"""Public orchestration entrypoint for specification semantic validation."""

from collections.abc import Callable

from microforge.domain.spec.errors import SpecSemanticError, SpecValidationErrors
from microforge.domain.spec.models import SpecV1
from microforge.domain.spec.semantic_rules.api import validate_api, validate_queries_and_features
from microforge.domain.spec.semantic_rules.fields import validate_fields
from microforge.domain.spec.semantic_rules.names import validate_names
from microforge.domain.spec.semantic_rules.relations import validate_relations
from microforge.domain.spec.semantic_rules.target import validate_target

SemanticRule = Callable[[SpecV1], list[SpecSemanticError]]

RULES: tuple[SemanticRule, ...] = (
    validate_target,
    validate_names,
    validate_api,
    validate_queries_and_features,
    validate_fields,
    validate_relations,
)


def validate_semantics(spec: SpecV1) -> None:
    """Run every semantic rule group and report all violations together."""
    errors = [error for rule in RULES for error in rule(spec)]
    if errors:
        raise SpecValidationErrors(errors)
