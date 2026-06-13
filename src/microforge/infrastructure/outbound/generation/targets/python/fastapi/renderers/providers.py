"""Render FastAPI dependency providers for generated projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ApiEndpoint, ModelSpec, SpecV1
from microforge.domain.spec.types import ApiHttpMethod
from .api_endpoints import endpoint_targets_model
from .naming import package_name_for, to_snake_case
from .repository_methods import repository_method_for_endpoint
from .use_cases import UseCaseContext, use_case_for_method
from microforge.infrastructure.outbound.generation.template_renderer import (
    TemplateRenderer,
)


@dataclass(frozen=True)
class ProviderContext:
    """Provider data prepared for FastAPI dependency templates."""

    function_name: str
    import_class_name: str
    import_module: str
    repository_class_name: str
    repository_module: str


class ProvidersRenderer:
    """Render FastAPI dependency providers."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        providers = _providers_for_spec(spec)
        if not providers:
            return []
        return [
            ProjectFile(
                path=f"src/{package_name}/infrastructure/inbound/api/providers.py",
                content=_encode(
                    self.renderer.render(
                        "infrastructure/inbound/api/providers.py.j2",
                        {
                            "package_name": package_name,
                            "providers": providers,
                        },
                    )
                ),
            )
        ]


def _providers_for_spec(spec: SpecV1) -> list[ProviderContext]:
    providers = []
    seen = set()
    for model in spec.models:
        for endpoint in spec.api.endpoints:
            use_case = _use_case_for_endpoint(model, endpoint)
            if use_case is None or use_case.filename in seen:
                continue
            seen.add(use_case.filename)
            providers.append(
                ProviderContext(
                    function_name=f"provide_{use_case.filename}_use_case",
                    import_class_name=use_case.class_name,
                    import_module=(
                        f"application.use_cases.{to_snake_case(model.name)}."
                        f"{use_case.filename}"
                    ),
                    repository_class_name=f"SqlAlchemy{model.name}Repository",
                    repository_module=(
                        f"infrastructure.persistence.repositories."
                        f"{to_snake_case(model.name)}_repository"
                    ),
                )
            )
    return providers


def _use_case_for_endpoint(
    model: ModelSpec,
    endpoint: ApiEndpoint,
) -> UseCaseContext | None:
    if (
        endpoint.method != ApiHttpMethod.get
        or not endpoint_targets_model(endpoint, model)
    ):
        return None
    method = repository_method_for_endpoint(model, endpoint)
    if method is None:
        return None
    return use_case_for_method(model, method)


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
