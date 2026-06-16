"""Dependency wiring for API handlers."""

from __future__ import annotations

from functools import lru_cache

from microforge.application.generation.ports.inbound import GenerateProjectPort
from microforge.application.generation.ports.outbound import ProjectGeneratorPort
from microforge.application.generation.use_cases.generate_project import GenerateProjectUseCase
from microforge.application.spec.ports.inbound import ValidateSpecPort
from microforge.application.spec.use_cases.validate_spec import ValidateSpecUseCase
from microforge.infrastructure.outbound.generation.strategy.default_project_generator_registry import (
    default_project_generator_registry,
)
from microforge.infrastructure.outbound.generation.strategy.target_project_generator import (
    TargetProjectGenerator,
)
from microforge.infrastructure.outbound.generation.zip_project_packager import ZipProjectPackager
from microforge.infrastructure.outbound.spec.yaml_spec_loader import YamlSpecLoader


@lru_cache(maxsize=1)
def get_spec_loader() -> YamlSpecLoader:
    """Provide a singleton YAML spec loader."""
    return YamlSpecLoader()


@lru_cache(maxsize=1)
def get_validate_spec_port() -> ValidateSpecPort:
    """Provide a singleton validate spec service."""
    return ValidateSpecUseCase(get_spec_loader())


@lru_cache(maxsize=1)
def get_project_generator() -> ProjectGeneratorPort:
    """Provide a singleton project generator."""
    registry = default_project_generator_registry()
    return TargetProjectGenerator(registry)


@lru_cache(maxsize=1)
def get_project_packager() -> ZipProjectPackager:
    """Provide a singleton project packager."""
    return ZipProjectPackager()


@lru_cache(maxsize=1)
def get_generate_project_port() -> GenerateProjectPort:
    """Provide a singleton generate project use case."""
    return GenerateProjectUseCase(
        spec_loader=get_spec_loader(),
        generator=get_project_generator(),
        packager=get_project_packager(),
    )
