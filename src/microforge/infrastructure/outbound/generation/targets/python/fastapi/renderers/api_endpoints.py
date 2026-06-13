"""API endpoint helpers for FastAPI code generation."""

from __future__ import annotations

from microforge.domain.spec.models import ApiEndpoint, ModelSpec
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    to_snake_case,
)


def endpoint_targets_model(endpoint: ApiEndpoint, model: ModelSpec) -> bool:
    """Return whether an API endpoint appears to target a model."""

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
