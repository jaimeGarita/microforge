"""Outbound application ports for project generation."""

from __future__ import annotations

from typing import Protocol

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import SpecV1


class ProjectGeneratorPort(Protocol):
    """Generate project files from a validated spec."""

    def generate(self, spec: SpecV1) -> list[ProjectFile]:
        ...


class ProjectPackagerPort(Protocol):
    """Package generated files into a distributable artifact."""

    def package(self, files: list[ProjectFile]) -> bytes:
        ...
