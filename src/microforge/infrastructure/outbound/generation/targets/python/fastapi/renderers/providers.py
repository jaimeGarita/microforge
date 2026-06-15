"""Render FastAPI dependency providers for generated projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ApiEndpoint, ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    endpoint_has_path_param,
    endpoint_targets_model,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_methods import (
    repository_method_for_endpoint,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.use_cases import (
    UseCaseContext,
    use_case_for_method,
)
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
    has_id_param: bool
    body_schema_class: str | None
    body_schema_file: str | None
    domain_class_name: str
    domain_module: str


@dataclass(frozen=True)
class ImportContext:
    """Import data prepared for provider templates."""

    class_name: str
    module: str


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
                            "repository_imports": _repository_imports(providers),
                            "use_case_imports": _use_case_imports(providers),
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
            # determine if provider needs id param or a body schema
            has_id = endpoint_has_path_param(endpoint)
            method = repository_method_for_endpoint(model, endpoint)
            body_schema_class = None
            body_schema_file = None
            if method and method.name == "save":
                body_schema_class = f"{model.name}Create"
                body_schema_file = f"{to_snake_case(model.name)}_create"
            if method and method.name == "update":
                body_schema_class = f"{model.name}Update"
                body_schema_file = f"{to_snake_case(model.name)}_update"

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
                    has_id_param=has_id,
                    body_schema_class=body_schema_class,
                    body_schema_file=body_schema_file,
                    domain_class_name=model.name,
                    domain_module=to_snake_case(model.name),
                )
            )
    return providers


def _repository_imports(providers: list[ProviderContext]) -> list[ImportContext]:
    imports = {
        (provider.repository_module, provider.repository_class_name) for provider in providers
    }
    return [
        ImportContext(class_name=class_name, module=module)
        for module, class_name in sorted(imports)
    ]


def _use_case_imports(providers: list[ProviderContext]) -> list[ImportContext]:
    imports = {(provider.import_module, provider.import_class_name) for provider in providers}
    return [
        ImportContext(class_name=class_name, module=module)
        for module, class_name in sorted(imports)
    ]


def _use_case_for_endpoint(
    model: ModelSpec,
    endpoint: ApiEndpoint,
) -> UseCaseContext | None:
    if not endpoint_targets_model(endpoint, model):
        return None
    method = repository_method_for_endpoint(model, endpoint)
    if method is None:
        return None
    return use_case_for_method(model, method)


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
