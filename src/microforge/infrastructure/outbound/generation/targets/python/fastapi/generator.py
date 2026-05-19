"""FastAPI project generator adapter."""

from __future__ import annotations

import re
from pathlib import Path

from microforge.application.generation.ports.outbound import ProjectGeneratorPort
from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.domain_models import (
    DomainModelsRenderer,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer

TEMPLATE_DIR = Path(__file__).with_name("templates")


class PythonFastApiProjectGenerator(ProjectGeneratorPort):
    """Generate a minimal FastAPI project from a spec."""

    def __init__(self, renderer: TemplateRenderer | None = None):
        self.renderer = renderer or TemplateRenderer(TEMPLATE_DIR)
        self.domain_models_renderer = DomainModelsRenderer(self.renderer)

    def generate(self, spec: SpecV1) -> list[ProjectFile]:
        context = _build_context(spec)
        files = [
            ProjectFile(
                path="README.md",
                content=_encode(self.renderer.render("README.md.j2", context)),
            ),
            ProjectFile(
                path="pyproject.toml",
                content=_encode(self.renderer.render("pyproject.toml.j2", context)),
            ),
            ProjectFile(
                path=f"src/{context['package_name']}/main.py",
                content=_encode(self.renderer.render("main.py.j2", context)),
            ),
        ]
        files.extend(self.domain_models_renderer.render(spec))
        return files


def _to_package_name(service_name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", service_name.strip().lower())
    normalized = normalized.strip("_")
    return normalized or "generated_service"


def _build_context(spec: SpecV1) -> dict[str, str]:
    description = spec.service.description or "Generated FastAPI service"
    package_name = _to_package_name(spec.project_config.package_name)
    return {
        "app_title": f"{spec.service.name} API",
        "description": description,
        "health_path": f"{spec.api.base_path}/health",
        "package_name": package_name,
        "requires_python": f">={spec.target.python_version}",
        "service_name": spec.service.name,
    }


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
