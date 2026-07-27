"""API endpoint helpers for FastAPI code generation."""

from __future__ import annotations

from enum import Enum

from microforge.domain.spec.models import ApiEndpoint, ModelSpec
from microforge.domain.spec.types import ApiHttpMethod
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    to_snake_case,
)


class EndpointAction(str, Enum):
    """Implicit endpoint actions inferred from HTTP method and path shape."""

    list = "list"
    get = "get"
    create = "create"
    update = "update"
    delete = "delete"


def endpoint_targets_model(endpoint: ApiEndpoint, model: ModelSpec) -> bool:
    """Return whether an API endpoint appears to target a model."""

    if endpoint.model is not None:
        return endpoint.model == model.name

    model_name = to_snake_case(model.name)
    model_plural = f"{model_name}s"
    endpoint_name = to_snake_case(endpoint.name)
    path_segments = {
        segment.replace("-", "_")
        for segment in endpoint.path.strip("/").split("/")
        if segment and not segment.startswith("{")
    }
    return (
        model_name in endpoint_name
        or model_plural in endpoint_name
        or model_name in path_segments
        or model_plural in path_segments
    )


def endpoint_has_path_param(endpoint: ApiEndpoint) -> bool:
    """Return whether an API endpoint path contains a path parameter."""

    return any(
        segment.startswith("{") and segment.endswith("}")
        for segment in endpoint.path.strip("/").split("/")
    )


def infer_endpoint_action(endpoint: ApiEndpoint) -> EndpointAction | None:
    """Infer the generated action from HTTP method and path parameters."""

    has_path_param = endpoint_has_path_param(endpoint)
    if endpoint.method == ApiHttpMethod.get and has_path_param:
        return EndpointAction.get
    if endpoint.method == ApiHttpMethod.get:
        return EndpointAction.list
    if endpoint.method == ApiHttpMethod.post:
        return EndpointAction.create
    if endpoint.method in {ApiHttpMethod.put, ApiHttpMethod.patch}:
        return EndpointAction.update
    if endpoint.method == ApiHttpMethod.delete:
        return EndpointAction.delete
    return None
