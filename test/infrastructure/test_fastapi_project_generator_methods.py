import pathlib

import yaml

from microforge.domain.spec.models import SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi import (
    generator as fastapi_generator,
)


def _load_spec(path: str) -> SpecV1:
    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        return SpecV1.model_validate(yaml.safe_load(handle))


def _integer_id_spec() -> SpecV1:
    return SpecV1.model_validate(
        {
            "specVersion": 1,
            "project": {
                "name": "inventory-service",
                "packageName": "inventory_service",
            },
            "target": {
                "language": "python",
                "framework": "fastapi",
                "pythonVersion": "3.12",
                "packaging": "poetry",
            },
            "service": {"name": "inventory"},
            "api": {
                "basePath": "/api/v1",
                "endpoints": [
                    {"name": "listItems", "path": "/items", "method": "GET"},
                    {"name": "getItemById", "path": "/items/{id}", "method": "GET"},
                    {"name": "createItem", "path": "/items", "method": "POST"},
                    {"name": "updateItem", "path": "/items/{id}", "method": "PATCH"},
                    {"name": "deleteItem", "path": "/items/{id}", "method": "DELETE"},
                ],
            },
            "models": [
                {
                    "name": "Item",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "name", "type": "string"},
                    ],
                    "queries": [],
                    "features": {"repository": True},
                }
            ],
        }
    )


def _auto_increment_id_spec() -> SpecV1:
    return SpecV1.model_validate(
        {
            "specVersion": 1,
            "project": {
                "name": "inventory-service",
                "packageName": "inventory_service",
            },
            "target": {
                "language": "python",
                "framework": "fastapi",
                "pythonVersion": "3.12",
                "packaging": "poetry",
            },
            "service": {"name": "inventory"},
            "api": {
                "basePath": "/api/v1",
                "endpoints": [
                    {"name": "createItem", "path": "/items", "method": "POST"},
                ],
            },
            "models": [
                {
                    "name": "Item",
                    "fields": [
                        {
                            "name": "id",
                            "type": "int",
                            "primaryKey": True,
                            "autoIncrement": True,
                        },
                        {"name": "name", "type": "string"},
                    ],
                    "queries": [],
                    "features": {"repository": True},
                }
            ],
        }
    )


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
    post_route = post_route.split(
        '@router.patch("/{id}", response_model=CustomerRead)', maxsplit=1
    )[0]
    assert "from uuid import uuid4" not in routes
    assert (
        "from commerce_service.infrastructure.inbound.api.mappers.customer_mapper import CustomerApiMapper"
        in routes
    )
    assert "domain = CustomerApiMapper.create_to_domain(payload)" in routes
    assert "domain = CustomerApiMapper.update_to_domain(id, payload)" in routes
    assert "return [CustomerRead(**record.__dict__) for record in records]" not in post_route
    assert "return CustomerApiMapper.to_read(record)" in post_route
    assert "return Response(status_code=204)" in routes

    providers = by_path["src/commerce_service/infrastructure/inbound/api/providers.py"]
    assert ") -> callable:" not in providers
    assert "return CreateCustomerUseCase(repository)" in providers

    create_schema = by_path[
        "src/commerce_service/infrastructure/inbound/api/schemas/customer/customer_create.py"
    ]
    assert "id: int" not in create_schema
    assert "email: str" in create_schema

    api_mapper = by_path[
        "src/commerce_service/infrastructure/inbound/api/mappers/customer_mapper.py"
    ]
    assert "def create_to_domain(payload: CustomerCreate) -> Customer:" in api_mapper
    assert "return Customer(id=None, **payload.model_dump())" in api_mapper
    assert "def update_to_domain(id: int, payload: CustomerUpdate) -> Customer:" in api_mapper
    assert "return Customer(id=id, **payload.model_dump())" in api_mapper
    assert "def to_read(customer: Customer) -> CustomerRead:" in api_mapper
    assert "def to_read_list(" in api_mapper

    product_api_mapper = by_path[
        "src/commerce_service/infrastructure/inbound/api/mappers/product_mapper.py"
    ]
    assert "from uuid import uuid4" in product_api_mapper
    assert "return Product(id=uuid4(), **payload.model_dump())" in product_api_mapper

    order_routes = by_path["src/commerce_service/infrastructure/inbound/api/routes/order_routes.py"]
    assert "from fastapi import APIRouter, Depends, HTTPException, Query" in order_routes
    assert "customer_id: UUID | None = Query(default=None)," in order_routes
    assert "status_in: list[str] | None = Query(default=None)," in order_routes
    assert "total_amount_gte: Decimal | None = Query(default=None)," in order_routes
    assert "if status_in is not None:" in order_routes
    assert "records = find_orders_by_status_use_case.execute(status_in)" in order_routes

    order_use_case = by_path[
        "src/commerce_service/application/use_cases/order/find_orders_by_status.py"
    ]
    assert "def execute(self, status_in: list[str]) -> list[Order]:" in order_use_case
    assert "return self.repository.find_by_status(status_in)" in order_use_case

    order_repository_port = by_path[
        "src/commerce_service/application/ports/repositories/order_repository.py"
    ]
    assert "def find_by_status(self, status_in: list[str]) -> list[Order]:" in order_repository_port

    order_repository = by_path[
        "src/commerce_service/infrastructure/persistence/repositories/order_repository.py"
    ]
    assert "def find_by_status(self, status_in: list[str]) -> list[Order]:" in order_repository
    assert ".where(OrderORM.status.in_(status_in))" in order_repository

    customer_orm = by_path["src/commerce_service/infrastructure/persistence/customer.py"]
    assert "id: Mapped[int] = mapped_column(" in customer_orm
    assert "primary_key=True, autoincrement=True" in customer_orm

    customer_domain = by_path["src/commerce_service/domain/models/customer.py"]
    assert "id: int | None" in customer_domain


def test_generator_uses_declared_id_type() -> None:
    files = fastapi_generator.PythonFastApiProjectGenerator().generate(_integer_id_spec())

    by_path = {f.path: f.content.decode("utf-8") for f in files}

    routes = by_path["src/inventory_service/infrastructure/inbound/api/routes/item_routes.py"]
    assert "from uuid import UUID" not in routes
    assert "id: int," in routes

    api_mapper = by_path["src/inventory_service/infrastructure/inbound/api/mappers/item_mapper.py"]
    assert "from uuid import uuid4" not in api_mapper
    assert "def update_to_domain(id: int, payload: ItemUpdate) -> Item:" in api_mapper
    assert "return Item(**payload.model_dump())" in api_mapper

    create_schema = by_path[
        "src/inventory_service/infrastructure/inbound/api/schemas/item/item_create.py"
    ]
    assert "id: int" in create_schema

    repository_port = by_path[
        "src/inventory_service/application/ports/repositories/item_repository.py"
    ]
    assert "def find_by_id(self, id: int) -> Item | None:" in repository_port
    assert "def delete_by_id(self, id: int) -> None:" in repository_port

    repository = by_path[
        "src/inventory_service/infrastructure/persistence/repositories/item_repository.py"
    ]
    assert "def find_by_id(self, id: int) -> Item | None:" in repository
    assert "def delete_by_id(self, id: int) -> None:" in repository


def test_generator_omits_auto_increment_id_from_create_payload() -> None:
    files = fastapi_generator.PythonFastApiProjectGenerator().generate(
        _auto_increment_id_spec()
    )

    by_path = {f.path: f.content.decode("utf-8") for f in files}

    domain = by_path["src/inventory_service/domain/models/item.py"]
    assert "id: int | None" in domain

    create_schema = by_path[
        "src/inventory_service/infrastructure/inbound/api/schemas/item/item_create.py"
    ]
    assert "id: int" not in create_schema
    assert "name: str" in create_schema

    api_mapper = by_path["src/inventory_service/infrastructure/inbound/api/mappers/item_mapper.py"]
    assert "return Item(id=None, **payload.model_dump())" in api_mapper

    orm = by_path["src/inventory_service/infrastructure/persistence/item.py"]
    assert "primary_key=True, autoincrement=True" in orm
