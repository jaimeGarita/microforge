"""Default project generator strategy registry."""

from microforge.domain.spec.types import TargetFramework, TargetLanguage
from microforge.infrastructure.outbound.generation.strategy.registry import (
    ProjectGeneratorRegistry,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.generator import (
    PythonFastApiProjectGenerator,
)

def default_project_generator_registry() -> ProjectGeneratorRegistry:
    return ProjectGeneratorRegistry(
        {
            (TargetLanguage.python, TargetFramework.fastapi): PythonFastApiProjectGenerator(),
        }
    )