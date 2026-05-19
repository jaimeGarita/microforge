"""Project generation use case."""

from __future__ import annotations

from microforge.application.generation.ports.inbound import GenerateProjectPort
from microforge.application.generation.ports.outbound import (
    ProjectGeneratorPort,
    ProjectPackagerPort,
)
from microforge.application.spec.ports.outbound import SpecLoaderPort
from microforge.domain.spec.semantics import validate_semantics


class GenerateProjectUseCase(GenerateProjectPort):
    """Use case: validate a spec, generate files, and package them."""

    def __init__(
        self,
        spec_loader: SpecLoaderPort,
        generator: ProjectGeneratorPort,
        packager: ProjectPackagerPort,
    ):
        self.spec_loader = spec_loader
        self.generator = generator
        self.packager = packager

    def run_bytes(self, data: bytes) -> bytes:
        spec = self.spec_loader.load_bytes(data)
        validate_semantics(spec)
        files = self.generator.generate(spec)
        return self.packager.package(files)
