import pathlib

import yaml

from microforge.domain.spec.models import SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi import (
    generator as fastapi_generator,
)


def _load_spec(path: str) -> SpecV1:
    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        return SpecV1.model_validate(yaml.safe_load(handle))


def test_generator_creates_non_get_routes() -> None:
    spec = _load_spec("examples/spec_large.yaml")
    files = fastapi_generator.PythonFastApiProjectGenerator().generate(spec)

    by_path = {f.path: f.content.decode("utf-8") for f in files}

    routes = by_path["src/commerce_service/infrastructure/inbound/api/routes/customer_routes.py"]
    assert "@router.post" in routes
    assert "@router.patch" in routes or "@router.put" in routes
    assert "@router.delete" in routes
    assert "payload: CustomerCreate" in routes or "payload: ProductCreate" in routes
    assert "use_case_callable" not in routes
    assert "CreateCustomer(**payload.model_dump())" not in routes
    post_route = routes.split('@router.post("", response_model=CustomerRead)', maxsplit=1)[1]
    post_route = post_route.split('@router.patch("/{id}", response_model=CustomerRead)', maxsplit=1)[0]
    assert "from uuid import uuid4" in routes
    assert "domain = Customer(id=uuid4(), **payload.model_dump())" in routes
    assert "domain = Customer(id=id, **payload.model_dump())" in routes
    assert "return [CustomerRead(**record.__dict__) for record in records]" not in post_route
    assert "return CustomerRead(**record.__dict__)" in post_route
    assert "return Response(status_code=204)" in routes

    providers = by_path["src/commerce_service/infrastructure/inbound/api/providers.py"]
    assert ") -> callable:" not in providers
    assert "return CreateCustomerUseCase(repository)" in providers

    create_schema = by_path[
        "src/commerce_service/infrastructure/inbound/api/schemas/customer/customer_create.py"
    ]
    assert "id: UUID" not in create_schema
    assert "email: str" in create_schema
