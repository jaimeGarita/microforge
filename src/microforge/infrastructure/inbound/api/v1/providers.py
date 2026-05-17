"""Dependency wiring for API handlers."""

from __future__ import annotations

from functools import lru_cache

from microforge.application.spec.ports.inbound import ValidateSpecPort
from microforge.application.spec.use_cases.validate_spec import ValidateSpecUseCase
from microforge.infrastructure.outbound.spec.yaml_spec_loader import YamlSpecLoader


@lru_cache(maxsize=1)
def get_spec_loader() -> YamlSpecLoader:
    """Provide a singleton YAML spec loader."""
    return YamlSpecLoader()


@lru_cache(maxsize=1)
def get_validate_spec_port() -> ValidateSpecPort:
    """Provide a singleton validate spec service."""
    return ValidateSpecUseCase(get_spec_loader())
