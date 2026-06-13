"""Repository filter expression helpers for SQLAlchemy generation."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.spec.types import QueryOp

INFIX_OPERATORS = {
    QueryOp.eq: "==",
    QueryOp.ne: "!=",
    QueryOp.lt: "<",
    QueryOp.lte: "<=",
    QueryOp.gt: ">",
    QueryOp.gte: ">=",
}


@dataclass(frozen=True)
class RepositoryFilterContext:
    """Repository filter data independent from a concrete ORM class."""

    field_name: str
    op: QueryOp
    param_name: str


@dataclass(frozen=True)
class RepositoryFilterExpressionContext:
    """SQLAlchemy filter expression prepared for repository templates."""

    expression: str


def filter_expression_for(
    filter_context: RepositoryFilterContext,
    orm_class_name: str,
) -> RepositoryFilterExpressionContext:
    """Return a SQLAlchemy filter expression for a repository query filter."""

    field_reference = f"{orm_class_name}.{filter_context.field_name}"
    param_reference = filter_context.param_name

    if filter_context.op in INFIX_OPERATORS:
        operator = INFIX_OPERATORS[filter_context.op]
        return RepositoryFilterExpressionContext(
            expression=f"{field_reference} {operator} {param_reference}",
        )
    if filter_context.op == QueryOp.like:
        return RepositoryFilterExpressionContext(
            expression=f"{field_reference}.like({param_reference})",
        )
    if filter_context.op == QueryOp.not_like:
        return RepositoryFilterExpressionContext(
            expression=f"~{field_reference}.like({param_reference})",
        )
    if filter_context.op == QueryOp.in_:
        return RepositoryFilterExpressionContext(
            expression=f"{field_reference}.in_({param_reference})",
        )
    if filter_context.op == QueryOp.not_in:
        return RepositoryFilterExpressionContext(
            expression=f"~{field_reference}.in_({param_reference})",
        )
    if filter_context.op == QueryOp.contains:
        return RepositoryFilterExpressionContext(
            expression=f"{field_reference}.contains({param_reference})",
        )
    if filter_context.op == QueryOp.starts_with:
        return RepositoryFilterExpressionContext(
            expression=f"{field_reference}.startswith({param_reference})",
        )
    if filter_context.op == QueryOp.ends_with:
        return RepositoryFilterExpressionContext(
            expression=f"{field_reference}.endswith({param_reference})",
        )

    raise ValueError(f"Unsupported query operator: {filter_context.op}")
