"""Repository method planning helpers for FastAPI code generation."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.spec.models import ApiEndpoint, FieldSpec, ModelSpec, QueryParam
from microforge.domain.spec.types import ApiHttpMethod, QueryOp
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    endpoint_has_path_param,
    endpoint_targets_model,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.model_ids import (
    id_field_for,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.python_types import (
    imports_for_fields,
    python_type_for,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_filters import (
    RepositoryFilterContext,
)


@dataclass(frozen=True)
class RepositoryMethodContext:
    """Repository method data prepared for repository templates."""

    name: str
    params: str
    return_type: str
    filters: list[RepositoryFilterContext]
    imports: list[str]


def repository_methods_for(
    model: ModelSpec,
    endpoints: list[ApiEndpoint],
) -> list[RepositoryMethodContext]:
    """Return repository methods required by model API endpoints."""

    methods = []
    seen = set()
    for endpoint in endpoints:
        if not endpoint_targets_model(endpoint, model):
            continue
        method = repository_method_for_endpoint(model, endpoint)
        if method is None or method.name in seen:
            continue
        seen.add(method.name)
        methods.append(method)
    for method in _methods_for_queries(model):
        if method.name in seen:
            continue
        seen.add(method.name)
        methods.append(method)
    return methods


def imports_for_repository_methods(methods: list[RepositoryMethodContext]) -> list[str]:
    """Return imports required by repository methods."""

    imports = {import_line for method in methods for import_line in method.imports}
    return sorted(imports)


def repository_method_for_endpoint(
    model: ModelSpec,
    endpoint: ApiEndpoint,
) -> RepositoryMethodContext | None:
    """Return the repository method required by an API endpoint."""

    has_path_param = endpoint_has_path_param(endpoint)
    id_field = id_field_for(model)
    id_type = python_type_for(id_field) if id_field is not None else "str"
    id_imports = imports_for_fields([id_field]) if id_field is not None else []
    if endpoint.method == ApiHttpMethod.get and has_path_param:
        return RepositoryMethodContext(
            "find_by_id",
            f"id: {id_type}",
            f"{model.name} | None",
            filters=[],
            imports=id_imports,
        )
    if endpoint.method == ApiHttpMethod.get:
        return RepositoryMethodContext(
            "find_all",
            "",
            f"list[{model.name}]",
            filters=[],
            imports=[],
        )
    if endpoint.method == ApiHttpMethod.post:
        return RepositoryMethodContext(
            "save",
            f"{to_snake_case(model.name)}: {model.name}",
            model.name,
            filters=[],
            imports=[],
        )
    if endpoint.method in {ApiHttpMethod.put, ApiHttpMethod.patch}:
        return RepositoryMethodContext(
            "update",
            f"{to_snake_case(model.name)}: {model.name}",
            model.name,
            filters=[],
            imports=[],
        )
    if endpoint.method == ApiHttpMethod.delete:
        return RepositoryMethodContext(
            "delete_by_id",
            f"id: {id_type}",
            "None",
            filters=[],
            imports=id_imports,
        )
    return None


def _methods_for_queries(model: ModelSpec) -> list[RepositoryMethodContext]:
    methods = []
    for query in model.queries:
        fields = [_field_for_query_param(model, param) for param in query.params]
        params = ", ".join(
            f"{_query_param_name(param)}: {_query_param_type(param, field)}"
            for param, field in zip(query.params, fields, strict=True)
        )
        methods.append(
            RepositoryMethodContext(
                name=_query_method_name(query.name),
                params=params,
                return_type=f"list[{model.name}]",
                filters=[
                    RepositoryFilterContext(
                        field_name=param.field,
                        op=param.op,
                        param_name=_query_param_name(param),
                    )
                    for param in query.params
                ],
                imports=imports_for_fields(fields),
            )
        )
    return methods


def _field_for_query_param(model: ModelSpec, param: QueryParam) -> FieldSpec:
    for field in model.fields:
        if field.name == param.field:
            return field
    raise ValueError(f"Query param references unknown field: {param.field}")


def _query_param_name(param: QueryParam) -> str:
    if param.op == QueryOp.eq:
        return param.field
    return f"{param.field}_{param.op.value}"


def _query_param_type(param: QueryParam, field: FieldSpec) -> str:
    python_type = python_type_for(field)
    if param.op in {QueryOp.in_, QueryOp.not_in}:
        return f"list[{python_type}]"
    return python_type


def _query_method_name(query_name: str) -> str:
    query_name = to_snake_case(query_name)
    if query_name.startswith("find_"):
        return query_name
    return f"find_{query_name}"
