"""Render FastAPI routes for generated projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ApiEndpoint, ModelSpec, SpecV1
from microforge.domain.spec.types import ApiHttpMethod
from .api_endpoints import endpoint_has_path_param, endpoint_targets_model
from .naming import package_name_for, to_snake_case
from .repository_methods import repository_method_for_endpoint
from .use_cases import UseCaseContext, use_case_for_method
from microforge.infrastructure.outbound.generation.template_renderer import (
    TemplateRenderer,
)


@dataclass(frozen=True)
class RouteContext:
    """Route data prepared for FastAPI route templates."""

    function_name: str
    has_id_param: bool
    path: str
    provider_name: str
    response_model: str
    return_statement: str
    use_case: UseCaseContext


@dataclass(frozen=True)
class RouterModuleContext:
    """Router module data used by route and main templates."""

    module_name: str
    prefix: str
    router_variable: str
    tag: str


class ApiRoutesRenderer:
    """Render FastAPI route modules for supported endpoints."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/infrastructure/inbound/api/routes"
        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            )
        ]

        for model in spec.models:
            routes = _routes_for_model(model, spec.api.endpoints)
            if not routes:
                continue
            router_module = router_module_for_model(model)
            files.append(
                ProjectFile(
                    path=f"{base_path}/{router_module.module_name}.py",
                    content=_encode(
                        self.renderer.render(
                            "infrastructure/inbound/api/routes/routes.py.j2",
                            {
                                "imports_uuid": any(
                                    route.has_id_param for route in routes
                                ),
                                "model_module": to_snake_case(model.name),
                                "package_name": package_name,
                                "read_schema_class": f"{model.name}Read",
                                "routes": routes,
                                "router_prefix": router_module.prefix,
                                "router_tag": router_module.tag,
                            },
                        )
                    ),
                )
            )
        return files


def router_modules_for_spec(spec: SpecV1) -> list[RouterModuleContext]:
    """Return route modules generated for the spec."""

    return [
        router_module_for_model(model)
        for model in spec.models
        if _routes_for_model(model, spec.api.endpoints)
    ]


def router_module_for_model(model: ModelSpec) -> RouterModuleContext:
    model_name = to_snake_case(model.name)
    return RouterModuleContext(
        module_name=f"{model_name}_routes",
        prefix=f"/{model_name}s",
        router_variable=f"{model_name}_router",
        tag=f"{model_name}s",
    )


def _routes_for_model(
    model: ModelSpec,
    endpoints: list[ApiEndpoint],
) -> list[RouteContext]:
    routes = []
    for endpoint in endpoints:
        if (
            endpoint.method != ApiHttpMethod.get
            or not endpoint_targets_model(endpoint, model)
        ):
            continue
        method = repository_method_for_endpoint(model, endpoint)
        if method is None:
            continue
        use_case = use_case_for_method(model, method)
        has_id_param = endpoint_has_path_param(endpoint)
        routes.append(
            RouteContext(
                function_name=use_case.filename,
                has_id_param=has_id_param,
                path="/{id}" if has_id_param else "",
                provider_name=f"provide_{use_case.filename}_use_case",
                response_model=(
                    f"{model.name}Read" if has_id_param else f"list[{model.name}Read]"
                ),
                return_statement=_return_statement_for_route(model, has_id_param),
                use_case=use_case,
            )
        )
    return routes


def _return_statement_for_route(model: ModelSpec, has_id_param: bool) -> str:
    if has_id_param:
        return f"return {model.name}Read(**record.__dict__)"
    return f"return [{model.name}Read(**record.__dict__) for record in records]"


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
