"""Project generator strategy registry."""

from microforge.application.generation.ports.outbound import ProjectGeneratorPort
from microforge.domain.spec.types import TargetFramework, TargetLanguage
from microforge.infrastructure.outbound.generation.strategy.errors import (
    UnsupportedTargetError,
)

GeneratorKey = tuple[TargetLanguage, TargetFramework]


class ProjectGeneratorRegistry:
    def __init__(self, generators: dict[GeneratorKey, ProjectGeneratorPort]):
        self.generators = generators

    def resolve(
        self,
        language: TargetLanguage,
        framework: TargetFramework,
    ) -> ProjectGeneratorPort:
        key = (language, framework)
        if key not in self.generators:
            raise UnsupportedTargetError(language.value, framework.value)
        return self.generators[key]
