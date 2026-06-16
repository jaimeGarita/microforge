from microforge.application.generation.ports.outbound import ProjectGeneratorPort
from microforge.domain.generation import UnsupportedTargetError
# Type alias for generator keys
GeneratorKey = tuple[str, str]

class ProjectGeneratorRegistry:
    def __init__(self, generators: dict[GeneratorKey, ProjectGeneratorPort]):
        self.generators = generators
        
    def resolve(self, language: str, framework: str) -> ProjectGeneratorPort:
        key = (language, framework)
        if key not in self.generators:
            raise UnsupportedTargetError(language, framework)
        return self.generators[key]