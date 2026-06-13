import pytest

from microforge.domain.spec.types import QueryOp
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_filters import (
    RepositoryFilterContext,
    filter_expression_for,
)


@pytest.mark.parametrize(
    ("op", "expected"),
    [
        (QueryOp.eq, "OrderORM.manolo == manolo"),
        (QueryOp.ne, "OrderORM.manolo != manolo"),
        (QueryOp.lt, "OrderORM.manolo < manolo"),
        (QueryOp.lte, "OrderORM.manolo <= manolo"),
        (QueryOp.gt, "OrderORM.manolo > manolo"),
        (QueryOp.gte, "OrderORM.manolo >= manolo"),
        (QueryOp.like, "OrderORM.manolo.like(manolo)"),
        (QueryOp.not_like, "~OrderORM.manolo.like(manolo)"),
        (QueryOp.in_, "OrderORM.manolo.in_(manolo)"),
        (QueryOp.not_in, "~OrderORM.manolo.in_(manolo)"),
        (QueryOp.contains, "OrderORM.manolo.contains(manolo)"),
        (QueryOp.starts_with, "OrderORM.manolo.startswith(manolo)"),
        (QueryOp.ends_with, "OrderORM.manolo.endswith(manolo)"),
    ],
)
def test_filter_expression_for_maps_query_ops(op: QueryOp, expected: str) -> None:
    filter_context = RepositoryFilterContext(
        field_name="manolo",
        op=op,
        param_name="manolo",
    )

    expression = filter_expression_for(filter_context, "OrderORM")

    assert expression.expression == expected
