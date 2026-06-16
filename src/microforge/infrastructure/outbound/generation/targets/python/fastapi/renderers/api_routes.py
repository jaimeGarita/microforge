"""Render FastAPI routes for generated projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ApiEndpoint, ModelSpec, SpecV1
from microforge.domain.spec.types import ApiHttpMethod
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    endpoint_has_path_param,
    endpoint_targets_model,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.model_ids import (
    id_field_for,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.python_types import (
    imports_for_fields,
    python_type_for,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_methods import (
    RepositoryMethodContext,
    repository_method_for_endpoint,
    repository_methods_for,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.use_cases import (
    UseCaseContext,
    use_case_for_method,
)
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
    method: str
    repository_method_name: str
    body_schema_class: str | None
    body_schema_file: str | None
    domain_class_name: str
    domain_module: str
    id_imports: list[str]
    id_type: str
    query_routes: list[QueryRouteContext]


@dataclass(frozen=True)
class QueryParamContext:
    """Query parameter data prepared for FastAPI route templates."""

    name: str
    python_type: str


@dataclass(frozen=True)
class QueryRouteContext:
    """Query use case data prepared for collection GET routes."""

    condition: str
    params: list[QueryParamContext]
    provider_name: str
    use_case: UseCaseContext
    use_case_param_names: str


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
                                "import_lines": _import_lines_for_routes(routes),
                                "imports_response": any(
                                    route.method == "delete" for route in routes
                                ),
                                "imports_query": any(route.query_routes for route in routes),
                                "imports_http_exception": any(
                                    route.has_id_param
                                    and not route.body_schema_class
                                    and route.method != "delete"
                                    for route in routes
                                ),
                                "imports_api_mapper": any(
                                    route.method != "delete" for route in routes
                                ),
                                "mapper_class_name": f"{model.name}ApiMapper",
                                "mapper_module": f"{to_snake_case(model.name)}_mapper",
                                "model_module": to_snake_case(model.name),
                                "package_name": package_name,
                                "read_schema_class": f"{model.name}Read",
                                "routes": routes,
                                "router_prefix": router_module.prefix,
                                "router_tag": router_module.tag,
                                "imports_read_schema": any(
                                    f"{model.name}Read" in route.response_model for route in routes
                                ),
                                "imports_create_schema": any(
                                    route.body_schema_class == f"{model.name}Create"
                                    for route in routes
                                ),
                                "imports_update_schema": any(
                                    route.body_schema_class == f"{model.name}Update"
                                    for route in routes
                                ),
                                "create_schema_class": f"{model.name}Create",
                                "update_schema_class": f"{model.name}Update",
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
        if not endpoint_targets_model(endpoint, model):
            continue
        method = repository_method_for_endpoint(model, endpoint)
        if method is None:
            continue
        use_case = use_case_for_method(model, method)
        has_id_param = endpoint_has_path_param(endpoint)
        id_field = id_field_for(model)
        id_type = python_type_for(id_field) if id_field is not None else "str"
        query_routes = (
            _query_routes_for_model(model, endpoints) if method.name == "find_all" else []
        )
        # determine response model and any body schema required
        body_schema_class = None
        body_schema_file = None
        if method.name == "save":
            body_schema_class = f"{model.name}Create"
            body_schema_file = f"{to_snake_case(model.name)}_create"
            response_model = f"{model.name}Read"
        elif method.name == "update":
            body_schema_class = f"{model.name}Update"
            body_schema_file = f"{to_snake_case(model.name)}_update"
            response_model = f"{model.name}Read"
        elif method.name == "delete_by_id":
            response_model = "None"
        elif method.name == "find_by_id":
            response_model = f"{model.name}Read"
        else:
            response_model = f"list[{model.name}Read]"

        routes.append(
            RouteContext(
                function_name=use_case.filename,
                has_id_param=has_id_param,
                path="/{id}" if has_id_param else "",
                provider_name=f"provide_{use_case.filename}_use_case",
                response_model=response_model,
                return_statement=_return_statement_for_route(
                    model,
                    has_id_param,
                    endpoint.method,
                ),
                use_case=use_case,
                method=endpoint.method.value.lower(),
                repository_method_name=method.name,
                body_schema_class=body_schema_class,
                body_schema_file=body_schema_file,
                domain_class_name=model.name,
                domain_module=to_snake_case(model.name),
                id_imports=imports_for_fields([id_field]) if id_field is not None else [],
                id_type=id_type,
                query_routes=query_routes,
            )
        )
    return routes


def _query_routes_for_model(
    model: ModelSpec,
    endpoints: list[ApiEndpoint],
) -> list[QueryRouteContext]:
    query_routes = []
    for method in repository_methods_for(model, endpoints):
        if not method.filters:
            continue
        use_case = use_case_for_method(model, method)
        params = _query_params_for_method(method)
        param_names = [param.name for param in params]
        query_routes.append(
            QueryRouteContext(
                condition=" and ".join(f"{param_name} is not None" for param_name in param_names),
                params=params,
                provider_name=f"provide_{use_case.filename}_use_case",
                use_case=use_case,
                use_case_param_names=", ".join(param_names),
            )
        )
    return query_routes


def _query_params_for_method(method: RepositoryMethodContext) -> list[QueryParamContext]:
    if not method.params:
        return []
    return [
        QueryParamContext(
            name=param.split(":", maxsplit=1)[0].strip(),
            python_type=param.split(":", maxsplit=1)[1].strip(),
        )
        for param in method.params.split(",")
    ]


def _import_lines_for_routes(routes: list[RouteContext]) -> list[str]:
    imports = set()
    if any(route.has_id_param for route in routes):
        for route in routes:
            if not route.has_id_param:
                continue
            imports.update(route.id_imports)
    for route in routes:
        for query_route in route.query_routes:
            imports.update(query_route.use_case.imports)
    return sorted(imports)


def _return_statement_for_route(
    model: ModelSpec,
    has_id_param: bool,
    method: ApiHttpMethod,
) -> str:
    """Compute the return statement for a route depending on HTTP method."""
    if method == ApiHttpMethod.delete:
        return "return Response(status_code=204)"
    if method in {ApiHttpMethod.post, ApiHttpMethod.put, ApiHttpMethod.patch}:
        return f"return {model.name}ApiMapper.to_read(record)"
    if has_id_param:
        return f"return {model.name}ApiMapper.to_read(record)"
    return f"return {model.name}ApiMapper.to_read_list(records)"


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
