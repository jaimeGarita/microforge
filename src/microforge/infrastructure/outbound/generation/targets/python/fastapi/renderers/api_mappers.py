"""Render API mapper classes for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ApiEndpoint, ModelSpec, SpecV1
from microforge.domain.spec.types import ApiHttpMethod
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.api_endpoints import (
    endpoint_targets_model,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.model_ids import (
    id_field_for,
    id_is_database_generated,
    id_is_uuid,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.python_types import (
    imports_for_fields,
    python_type_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class ApiMapperPlan:
    """API mapper methods and imports required by a model."""

    has_create: bool
    has_read: bool
    has_update: bool


class ApiMappersRenderer:
    """Render mapper classes between API schemas and domain models."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/infrastructure/inbound/api/mappers"
        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            )
        ]

        for model in spec.models:
            plan = _mapper_plan_for(model, spec.api.endpoints)
            if not any((plan.has_create, plan.has_read, plan.has_update)):
                continue
            files.append(
                ProjectFile(
                    path=f"{base_path}/{to_snake_case(model.name)}_mapper.py",
                    content=_encode(self._render_mapper(model, package_name, plan)),
                )
            )
        return files

    def _render_mapper(
        self,
        model: ModelSpec,
        package_name: str,
        plan: ApiMapperPlan,
    ) -> str:
        model_module = to_snake_case(model.name)
        id_field = id_field_for(model)
        id_type = python_type_for(id_field) if id_field is not None else "str"
        return self.renderer.render(
            "infrastructure/inbound/api/mappers/mapper.py.j2",
            {
                "class_name": f"{model.name}ApiMapper",
                "create_schema_class": f"{model.name}Create",
                "domain_class_name": model.name,
                "domain_module": model_module,
                "has_create": plan.has_create,
                "has_read": plan.has_read,
                "has_update": plan.has_update,
                "id_imports": imports_for_fields([id_field]) if id_field is not None else [],
                "id_is_database_generated": id_is_database_generated(model),
                "id_is_uuid": id_is_uuid(model),
                "id_type": id_type,
                "model_module": model_module,
                "package_name": package_name,
                "read_schema_class": f"{model.name}Read",
                "update_schema_class": f"{model.name}Update",
            },
        )


def _mapper_plan_for(model: ModelSpec, endpoints: list[ApiEndpoint]) -> ApiMapperPlan:
    methods = {endpoint.method for endpoint in endpoints if endpoint_targets_model(endpoint, model)}
    return ApiMapperPlan(
        has_create=ApiHttpMethod.post in methods,
        has_read=bool(methods - {ApiHttpMethod.delete}),
        has_update=bool(methods.intersection({ApiHttpMethod.put, ApiHttpMethod.patch})),
    )


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
