"""Render application repository ports for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ApiEndpoint, ModelSpec, SpecV1
from microforge.domain.spec.types import ApiHttpMethod
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    endpoint_has_path_param,
    endpoint_targets_model,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class RepositoryMethodContext:
    """Repository method data prepared for port templates."""

    name: str
    params: str
    return_type: str


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
            methods = _repository_methods_for(model, spec.api.endpoints)
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
                "imports": _imports_for_methods(methods),
                "methods": methods,
                "model_class_name": model.name,
                "model_module": to_snake_case(model.name),
                "package_name": package_name,
            },
        )


def _repository_methods_for(
    model: ModelSpec,
    endpoints: list[ApiEndpoint],
) -> list[RepositoryMethodContext]:
    methods = []
    seen = set()
    for endpoint in endpoints:
        if not endpoint_targets_model(endpoint, model):
            continue
        method = _method_for_endpoint(model, endpoint)
        if method is None or method.name in seen:
            continue
        seen.add(method.name)
        methods.append(method)
    return methods


def _method_for_endpoint(
    model: ModelSpec,
    endpoint: ApiEndpoint,
) -> RepositoryMethodContext | None:
    has_path_param = endpoint_has_path_param(endpoint)
    if endpoint.method == ApiHttpMethod.get and has_path_param:
        return RepositoryMethodContext("find_by_id", "id: UUID", f"{model.name} | None")
    if endpoint.method == ApiHttpMethod.get:
        return RepositoryMethodContext("find_all", "", f"list[{model.name}]")
    if endpoint.method == ApiHttpMethod.post:
        return RepositoryMethodContext(
            "save", f"{to_snake_case(model.name)}: {model.name}", model.name
        )
    if endpoint.method in {ApiHttpMethod.put, ApiHttpMethod.patch}:
        return RepositoryMethodContext(
            "update",
            f"{to_snake_case(model.name)}: {model.name}",
            model.name,
        )
    if endpoint.method == ApiHttpMethod.delete:
        return RepositoryMethodContext("delete_by_id", "id: UUID", "None")
    return None


def _imports_for_methods(methods: list[RepositoryMethodContext]) -> list[str]:
    if any("UUID" in method.params for method in methods):
        return ["from uuid import UUID"]
    return []


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
