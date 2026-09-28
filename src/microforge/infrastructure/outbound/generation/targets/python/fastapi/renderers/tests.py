"""Render executable tests for generated FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.domain.spec.types import FieldType, RelationType
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    EndpointAction,
    endpoint_targets_model,
    infer_endpoint_action,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_routes import (
    router_module_for_model,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.model_ids import (
    field_is_generated_on_create,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class ModelTestContext:
    """Test capabilities generated for one model."""

    model_name: str
    model_module: str
    package_name: str
    list_path: str
    supports_crud: bool
    create_payload: str
    patch_field: str
    patch_value: str
    target_seeds: list[TargetSeedContext]
    seed_imports: list[str]


@dataclass(frozen=True)
class TargetSeedContext:
    """Related record required before a generated CRUD test can create its model."""

    class_name: str
    module_name: str
    constructor_args: str
    imports: list[str]


class TestsRenderer:
    """Render shared fixtures and endpoint tests for generated services."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        files = [
            ProjectFile(
                path="tests/conftest.py",
                content=_encode(
                    self.renderer.render("tests/conftest.py.j2", {"package_name": package_name})
                ),
            ),
            ProjectFile(
                path="tests/test_health.py",
                content=_encode(
                    self.renderer.render(
                        "tests/test_health.py.j2",
                        {"health_path": f"{spec.api.base_path}/health"},
                    )
                ),
            ),
            ProjectFile(
                path="tests/test_config.py",
                content=_encode(
                    self.renderer.render(
                        "tests/test_config.py.j2",
                        {"package_name": package_name},
                    )
                ),
            ),
        ]
        for model in spec.models:
            context = _model_test_context(spec, model)
            if context is None:
                continue
            files.append(
                ProjectFile(
                    path=f"tests/test_{context.model_module}_routes.py",
                    content=_encode(
                        self.renderer.render("tests/test_model_routes.py.j2", {"model": context})
                    ),
                )
            )
        return files


def _model_test_context(spec: SpecV1, model: ModelSpec) -> ModelTestContext | None:
    actions = {
        infer_endpoint_action(endpoint)
        for endpoint in spec.api.endpoints
        if endpoint_targets_model(endpoint, model)
    }
    has_list = EndpointAction.list in actions
    if not has_list:
        return None
    router = router_module_for_model(model)
    target_seeds = _target_seeds_for(spec, model)
    writable_fields = [field for field in model.fields if not field_is_generated_on_create(field)]
    patch_field = next(
        (field for field in writable_fields if field.type == FieldType.string),
        writable_fields[0] if writable_fields else None,
    )
    supports_crud = {
        EndpointAction.get,
        EndpointAction.create,
        EndpointAction.replace_,
        EndpointAction.update,
        EndpointAction.delete,
    }.issubset(actions) and patch_field is not None
    return ModelTestContext(
        model_name=model.name,
        model_module=to_snake_case(model.name),
        package_name=package_name_for(spec.project_config.package_name),
        list_path=f"{spec.api.base_path}{router.prefix}",
        supports_crud=supports_crud,
        create_payload=repr({field.name: _payload_value_for(field) for field in writable_fields}),
        patch_field=patch_field.name if patch_field is not None else "",
        patch_value=repr(_payload_value_for(patch_field, alternate=True))
        if patch_field is not None
        else "None",
        target_seeds=target_seeds,
        seed_imports=sorted({item for seed in target_seeds for item in seed.imports}),
    )


def _target_seeds_for(spec: SpecV1, model: ModelSpec) -> list[TargetSeedContext]:
    models_by_name = {item.name: item for item in spec.models}
    seeds: list[TargetSeedContext] = []
    seen: set[str] = set()
    for relation in model.relations:
        if relation.relation_type not in {RelationType.many_to_one, RelationType.one_to_one}:
            continue
        if relation.target in seen:
            continue
        seen.add(relation.target)
        target = models_by_name[relation.target]
        values = ", ".join(
            f"{field.name}={_python_expression_for(field)}" for field in target.fields
        )
        seeds.append(
            TargetSeedContext(
                class_name=f"{target.name}ORM",
                module_name=to_snake_case(target.name),
                constructor_args=values,
                imports=_python_imports_for(target.fields),
            )
        )
    return seeds


def _payload_value_for(field: FieldSpec, *, alternate: bool = False) -> object:
    if field.enum_values:
        return field.enum_values[-1 if alternate else 0]
    if field.nullable and not alternate:
        return None
    if field.type == FieldType.string:
        minimum = max(field.min_length or 1, 3)
        value = ("updated" if alternate else field.name).ljust(minimum, "x")
        return value[: field.max_length] if field.max_length is not None else value
    if field.type in {FieldType.int, FieldType.long}:
        return 2 if alternate else max(int(field.minimum or 1), 1)
    if field.type == FieldType.boolean:
        return not alternate
    if field.type == FieldType.uuid:
        return (
            "00000000-0000-0000-0000-000000000002"
            if alternate
            else "00000000-0000-0000-0000-000000000001"
        )
    if field.type == FieldType.decimal:
        return "2.0" if alternate else str(field.minimum or "1.0")
    if field.type == FieldType.instant:
        return "2026-01-02T00:00:00Z" if alternate else "2026-01-01T00:00:00Z"
    if field.type == FieldType.date:
        return "2026-01-02" if alternate else "2026-01-01"
    raise ValueError(f"Unsupported generated test field type: {field.type}")


def _python_expression_for(field: FieldSpec) -> str:
    value = _payload_value_for(field)
    if field.type == FieldType.uuid and value is not None:
        return f"UUID({str(value)!r})"
    if field.type == FieldType.decimal and value is not None:
        return f"Decimal({str(value)!r})"
    if field.type == FieldType.instant and value is not None:
        return f"datetime.fromisoformat({str(value).replace('Z', '+00:00')!r})"
    if field.type == FieldType.date and value is not None:
        return f"date.fromisoformat({str(value)!r})"
    return repr(value)


def _python_imports_for(fields: list[FieldSpec]) -> list[str]:
    field_types = {field.type for field in fields}
    imports: list[str] = []
    if FieldType.date in field_types:
        imports.append("from datetime import date")
    if FieldType.instant in field_types:
        imports.append("from datetime import datetime")
    if FieldType.decimal in field_types:
        imports.append("from decimal import Decimal")
    if FieldType.uuid in field_types:
        imports.append("from uuid import UUID")
    return imports


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
