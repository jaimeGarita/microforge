import pytest

from microforge.domain.spec.models import ApiEndpoint, ModelSpec
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    EndpointAction,
    endpoint_targets_model,
    infer_endpoint_action,
)


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("GET", "/customers", EndpointAction.list),
        ("GET", "/customers/{id}", EndpointAction.get),
        ("POST", "/customers", EndpointAction.create),
        ("PATCH", "/customers/{id}", EndpointAction.update),
        ("PUT", "/customers/{id}", EndpointAction.update),
        ("DELETE", "/customers/{id}", EndpointAction.delete),
    ],
)
def test_infer_endpoint_action(method: str, path: str, expected: EndpointAction) -> None:
    endpoint = ApiEndpoint(name="customers", path=path, method=method)

    assert infer_endpoint_action(endpoint) == expected


def test_endpoint_targets_declared_model_before_inference() -> None:
    endpoint = ApiEndpoint(
        name="customers",
        model="Order",
        path="/customers",
        method="GET",
    )
    customer = ModelSpec(name="Customer", fields=[])
    order = ModelSpec(name="Order", fields=[])

    assert not endpoint_targets_model(endpoint, customer)
    assert endpoint_targets_model(endpoint, order)
