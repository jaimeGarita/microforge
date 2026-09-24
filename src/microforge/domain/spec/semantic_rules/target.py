"""Generation-target semantic rules."""

from microforge.domain.spec.errors import SpecSemanticError
from microforge.domain.spec.models import SpecV1
from microforge.domain.spec.types import TargetFramework, TargetLanguage


def validate_target(spec: SpecV1) -> list[SpecSemanticError]:
    """Ensure v1 uses a supported generation target."""
    if (
        spec.target.language != TargetLanguage.python
        or spec.target.framework != TargetFramework.fastapi
    ):
        return [SpecSemanticError("v1 only supports target: python + fastapi.")]
    return []
