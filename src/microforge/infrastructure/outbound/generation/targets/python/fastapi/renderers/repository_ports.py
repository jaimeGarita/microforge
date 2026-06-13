"""Render application repository ports for FastAPI projects."""

from __future__ import annotations

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_methods import (
    RepositoryMethodContext,
    imports_for_repository_methods,
    repository_methods_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


class RepositoryPortsRenderer:
    """Render repository port protocols required by API endpoints."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/application/ports/repositories"
        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            )
        ]

        for model in spec.models:
            if not model.features.repository:
                continue
            methods = repository_methods_for(model, spec.api.endpoints)
            if not methods:
                continue
            files.append(
                ProjectFile(
                    path=f"{base_path}/{to_snake_case(model.name)}_repository.py",
                    content=_encode(self._render_repository_port(model, package_name, methods)),
                )
            )
        return files

    def _render_repository_port(
        self,
        model: ModelSpec,
        package_name: str,
        methods: list[RepositoryMethodContext],
    ) -> str:
        return self.renderer.render(
            "application/ports/repositories/repository.py.j2",
            {
                "class_name": f"{model.name}RepositoryPort",
                "imports": imports_for_repository_methods(methods),
                "methods": methods,
                "model_class_name": model.name,
                "model_module": to_snake_case(model.name),
                "package_name": package_name,
            },
        )


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
