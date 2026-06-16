from microforge.infrastructure.outbound.generation.strategy import ProjectGeneratorRegistry
from microforge.domain.spec.models import SpecV1, ProjectFile

class TargetProjectGenerator(ProjectGeneratorRegistry):
    def __init__(self, registry: ProjectGeneratorRegistry):
        self.registry = registry
        
    def generate(self, spec: SpecV1) -> list[ProjectFile]:
        generator = self.registry.resolve(
            spec.target.language,
            spec.target.framework
        )
        return generator.generate(spec)