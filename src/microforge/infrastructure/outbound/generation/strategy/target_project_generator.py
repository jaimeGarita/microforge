"""Target-dispatching project generator strategy."""

from microforge.application.generation.ports.outbound import ProjectGeneratorPort
from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import SpecV1
from microforge.infrastructure.outbound.generation.strategy.registry import (
    ProjectGeneratorRegistry,
)


class TargetProjectGenerator(ProjectGeneratorPort):
    def __init__(self, registry: ProjectGeneratorRegistry):
        self.registry = registry

    def generate(self, spec: SpecV1) -> list[ProjectFile]:
        generator = self.registry.resolve(
            spec.target.language,
            spec.target.framework,
        )
        return generator.generate(spec)
