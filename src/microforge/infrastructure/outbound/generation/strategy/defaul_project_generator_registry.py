from microforge.infrastructure.outbound.generation.strategy import ProjectGeneratorRegistry
from microforge.infrastructure.outbound.generation.targets.python.fastapi import PythonFastApiProjectGenerator
from microforge.domain.spec.models import (
    TargetLanguage,
    TargetFramework,
)

def default_project_generator_registry() -> ProjectGeneratorRegistry:
    return ProjectGeneratorRegistry(
        {
            (TargetLanguage.python, TargetFramework.fastapi): PythonFastApiProjectGenerator(),
        }
    )