import pathlib

import yaml

from microforge.domain.spec.models import SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi import (
    generator as fastapi_generator,
)


def _load_spec(path: str) -> SpecV1:
    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        return SpecV1.model_validate(yaml.safe_load(handle))


def test_fastapi_project_generator_creates_minimal_project_files() -> None:
    spec = _load_spec("examples/spec_valid.yaml")
    files = fastapi_generator.PythonFastApiProjectGenerator().generate(spec)

    repository_port_path = (
        "src/orders_service/infrastructure/persistence/repositories/"
        "order_repository.py"
    )
    main_path = "src/orders_service/main.py"

    by_path = {
        project_file.path: project_file.content.decode("utf-8")
        for project_file in files
    }

    assert set(by_path) == {
        "README.md",
        "pyproject.toml",
        "src/orders_service/application/ports/repositories/__init__.py",
        "src/orders_service/application/ports/repositories/order_repository.py",
        "src/orders_service/application/use_cases/__init__.py",
        "src/orders_service/application/use_cases/order/__init__.py",
        "src/orders_service/application/use_cases/order/find_orders_by_status.py",
        "src/orders_service/application/use_cases/order/list_orders.py",
        "src/orders_service/domain/models/__init__.py",
        "src/orders_service/domain/models/order.py",
        "src/orders_service/infrastructure/inbound/api/providers.py",
        "src/orders_service/infrastructure/inbound/api/routes/__init__.py",
        "src/orders_service/infrastructure/inbound/api/routes/order_routes.py",
        "src/orders_service/infrastructure/inbound/api/schemas/__init__.py",
        "src/orders_service/infrastructure/inbound/api/schemas/order/__init__.py",
        "src/orders_service/infrastructure/inbound/api/schemas/order/order_read.py",
        "src/orders_service/infrastructure/persistence/__init__.py",
        "src/orders_service/infrastructure/persistence/base.py",
        "src/orders_service/infrastructure/persistence/order.py",
        "src/orders_service/infrastructure/persistence/session.py",
        "src/orders_service/infrastructure/persistence/repositories/__init__.py",
        repository_port_path,
        "src/orders_service/main.py",
    }
    assert "# orders" in by_path["README.md"]
    assert 'name = "orders_service"' in by_path["pyproject.toml"]
    assert 'app = FastAPI(title="orders API")' in by_path[main_path]
    assert (
        "from orders_service.infrastructure.inbound.api.routes.order_routes import "
        "router as order_router"
        in by_path[main_path]
    )
    assert (
        "from orders_service.infrastructure.persistence.session import init_db"
        in by_path[main_path]
    )
    assert "init_db()" in by_path[main_path]
    assert 'app.include_router(order_router, prefix="/api/v1")' in by_path[main_path]
    assert '@app.get("/api/v1/health")' in by_path[main_path]
    repository_port = by_path[
        "src/orders_service/application/ports/repositories/order_repository.py"
    ]
    assert "class OrderRepositoryPort(Protocol):" in repository_port
    assert "def find_all(self) -> list[Order]:" in repository_port
    assert "def find_by_status(self, status: str) -> list[Order]:" in repository_port
    assert "def find_by_id" not in repository_port
    assert "def save" not in repository_port
    list_orders = by_path[
        "src/orders_service/application/use_cases/order/list_orders.py"
    ]
    assert "class ListOrdersUseCase:" in list_orders
    assert "def execute(self) -> list[Order]:" in list_orders
    assert "return self.repository.find_all()" in list_orders
    find_by_status = by_path[
        "src/orders_service/application/use_cases/order/find_orders_by_status.py"
    ]
    assert "class FindOrdersByStatusUseCase:" in find_by_status
    assert "def execute(self, status: str) -> list[Order]:" in find_by_status
    assert "return self.repository.find_by_status(status)" in find_by_status
    providers = by_path["src/orders_service/infrastructure/inbound/api/providers.py"]
    assert "from fastapi import Depends" in providers
    assert "from sqlalchemy.orm import Session" in providers
    assert (
        "from orders_service.infrastructure.persistence.repositories.order_repository "
        "import SqlAlchemyOrderRepository"
    ) in providers
    assert "def provide_list_orders_use_case(" in providers
    assert "session: Session = Depends(get_session)," in providers
    assert "repository = SqlAlchemyOrderRepository(session)" in providers
    assert "return ListOrdersUseCase(repository)" in providers
    routes = by_path[
        "src/orders_service/infrastructure/inbound/api/routes/order_routes.py"
    ]
    assert 'router = APIRouter(prefix="/orders", tags=["orders"])' in routes
    assert '@router.get("", response_model=list[OrderRead])' in routes
    assert "def list_orders(" in routes
    assert "Depends(provide_list_orders_use_case)" in routes
    assert "records = use_case.execute()" in routes
    assert "return [OrderRead(**record.__dict__) for record in records]" in routes
    assert "class Order:" in by_path["src/orders_service/domain/models/order.py"]
    assert "id: UUID" in by_path["src/orders_service/domain/models/order.py"]
    assert "status: str" in by_path["src/orders_service/domain/models/order.py"]
    assert "pydantic>=2.0" in by_path["pyproject.toml"]
    order_schema = by_path[
        "src/orders_service/infrastructure/inbound/api/schemas/order/order_read.py"
    ]
    assert "class OrderCreate(BaseModel):" not in order_schema
    assert "class OrderRead(BaseModel):" in order_schema
    assert "class OrderUpdate(BaseModel):" not in order_schema
    assert "    status: str" in order_schema
    assert "    id: UUID" in order_schema
    assert (
        "class Base(DeclarativeBase):"
        in by_path["src/orders_service/infrastructure/persistence/base.py"]
    )
    session = by_path["src/orders_service/infrastructure/persistence/session.py"]
    assert (
        "from orders_service.infrastructure.persistence.base import Base" in session
    )
    assert (
        "from orders_service.infrastructure.persistence import order as _order_model"
        in session
    )
    assert 'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")' in session
    assert "engine = create_engine(DATABASE_URL, connect_args=connect_args)" in session
    assert (
        "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)"
        in session
    )
    assert "def get_session() -> Generator[Session, None, None]:" in session
    assert "def init_db() -> None:" in session
    assert "Base.metadata.create_all(bind=engine)" in session
    assert (
        "class OrderORM(Base):"
        in by_path["src/orders_service/infrastructure/persistence/order.py"]
    )
    assert (
        "from orders_service.infrastructure.persistence.base import Base"
        in by_path["src/orders_service/infrastructure/persistence/order.py"]
    )
    assert (
        '__tablename__ = "orders"'
        in by_path["src/orders_service/infrastructure/persistence/order.py"]
    )
    assert (
        "id: Mapped[UUID] = mapped_column(primary_key=True)"
        in by_path["src/orders_service/infrastructure/persistence/order.py"]
    )
    assert (
        "status: Mapped[str] = mapped_column()"
        in by_path["src/orders_service/infrastructure/persistence/order.py"]
    )
    repository = by_path[
        "src/orders_service/infrastructure/persistence/repositories/order_repository.py"
    ]
    assert "class SqlAlchemyOrderRepository(OrderRepositoryPort):" in repository
    assert "def find_all(self) -> list[Order]:" in repository
    assert "records = self.session.scalars(select(OrderORM)).all()" in repository
    assert "def find_by_status(self, status: str) -> list[Order]:" in repository
    assert ".where(OrderORM.status == status)" in repository
    assert "def _to_domain(self, record: OrderORM) -> Order:" in repository
    assert "def _to_orm(self, order: Order) -> OrderORM:" in repository
