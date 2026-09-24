"""API endpoint, query, and feature-coherence semantic rules."""

from microforge.domain.spec.errors import SpecSemanticError
from microforge.domain.spec.models import ApiEndpoint, SpecV1
from microforge.domain.spec.types import ApiHttpMethod


def validate_api(spec: SpecV1) -> list[SpecSemanticError]:
    """Validate endpoint model references and filters."""
    model_fields = _index_model_fields(spec)
    return [
        *_validate_endpoints_refer_existing_models(spec, model_fields),
        *_validate_endpoint_filters_refer_existing_fields(spec, model_fields),
    ]


def validate_queries_and_features(spec: SpecV1) -> list[SpecSemanticError]:
    """Validate declared queries and their required model features."""
    model_fields = _index_model_fields(spec)
    return [
        *_validate_queries_refer_existing_fields(spec, model_fields),
        *_validate_feature_coherence(spec),
    ]


def _index_model_fields(spec: SpecV1) -> dict[str, set[str]]:
    return {model.name: {field.name for field in model.fields} for model in spec.models}


def _validate_endpoints_refer_existing_models(
    spec: SpecV1, model_fields: dict[str, set[str]]
) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    for endpoint in spec.api.endpoints:
        if endpoint.model is not None and endpoint.model not in model_fields:
            errors.append(
                SpecSemanticError(
                    f"Endpoint '{endpoint.name}' references missing model "
                    f"'{endpoint.model}'. Valid models: {sorted(model_fields)}"
                )
            )
    return errors


def _validate_endpoint_filters_refer_existing_fields(
    spec: SpecV1, model_fields: dict[str, set[str]]
) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    for endpoint in spec.api.endpoints:
        if not endpoint.filters:
            continue
        if not _endpoint_supports_filters(endpoint):
            errors.append(
                SpecSemanticError(
                    f"Endpoint '{endpoint.name}' defines filters but is not a "
                    "collection GET endpoint.",
                    model=endpoint.model,
                )
            )
        if endpoint.model is None:
            errors.append(
                SpecSemanticError(
                    f"Endpoint '{endpoint.name}' defines filters but does not declare a model."
                )
            )
            continue
        if endpoint.model not in model_fields:
            continue
        allowed = model_fields[endpoint.model]
        unknown = [item.field for item in endpoint.filters if item.field not in allowed]
        if unknown:
            errors.append(
                SpecSemanticError(
                    f"Endpoint '{endpoint.name}' filters reference missing fields: "
                    f"{unknown}. Valid fields: {sorted(allowed)}",
                    model=endpoint.model,
                )
            )
    return errors


def _endpoint_supports_filters(endpoint: ApiEndpoint) -> bool:
    return endpoint.method == ApiHttpMethod.get and not _endpoint_has_path_param(endpoint)


def _endpoint_has_path_param(endpoint: ApiEndpoint) -> bool:
    return any(
        segment.startswith("{") and segment.endswith("}")
        for segment in endpoint.path.strip("/").split("/")
    )


def _validate_queries_refer_existing_fields(
    spec: SpecV1, model_fields: dict[str, set[str]]
) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    for model in spec.models:
        allowed = model_fields[model.name]
        for query in model.queries:
            unknown = [param.field for param in query.params if param.field not in allowed]
            if unknown:
                errors.append(
                    SpecSemanticError(
                        f"Query '{query.name}' references missing fields: {unknown}. "
                        f"Valid fields: {sorted(allowed)}",
                        model=model.name,
                    )
                )
    return errors


def _validate_feature_coherence(spec: SpecV1) -> list[SpecSemanticError]:
    errors: list[SpecSemanticError] = []
    for model in spec.models:
        if not model.features.repository and model.queries:
            errors.append(
                SpecSemanticError(
                    "Queries are defined but features.repository is false.", model=model.name
                )
            )
    return errors
