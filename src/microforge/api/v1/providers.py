"""Dependency wiring for API handlers."""

from __future__ import annotations

from functools import lru_cache

from microforge.application.spec.validate_spec import ValidateSpecService
from microforge.infrastructure.spec.yaml_spec_loader import YamlSpecLoader


@lru_cache(maxsize=1)
def get_spec_loader() -> YamlSpecLoader:
    """Provide a singleton YAML spec loader."""
    return YamlSpecLoader()


@lru_cache(maxsize=1)
def get_validate_service() -> ValidateSpecService:
    """Provide a singleton validate spec service."""
    return ValidateSpecService(get_spec_loader())
