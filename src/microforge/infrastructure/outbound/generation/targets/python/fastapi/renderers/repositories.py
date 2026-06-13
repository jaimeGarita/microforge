"""Render SQLAlchemy repository implementations for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import FieldSpec, ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_filters import (
    RepositoryFilterExpressionContext,
    filter_expression_for,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_methods import (
    RepositoryMethodContext,
    imports_for_repository_methods,
    repository_methods_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class FieldMappingContext:
    """Field mapping data prepared for repository templates."""

    name: str


@dataclass(frozen=True)
class RepositoryImplementationMethodContext:
    """Repository method data prepared for SQLAlchemy implementation templates."""

    name: str
    params: str
    return_type: str
    filters: list[RepositoryFilterExpressionContext]


class RepositoriesRenderer:
    """Render SQLAlchemy repositories required by API endpoints."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/infrastructure/persistence/repositories"
        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            )
        ]

        for model in spec.models:
            if not model.features.repository:
                continue
            methods = repository_methods_for(model, spec.api.endpoints)
            if not methods:
                continue
            files.append(
                ProjectFile(
                    path=f"{base_path}/{to_snake_case(model.name)}_repository.py",
                    content=_encode(self._render_repository(model, package_name, methods)),
                )
            )
        return files

    def _render_repository(
        self,
        model: ModelSpec,
        package_name: str,
        methods: list[RepositoryMethodContext],
    ) -> str:
        return self.renderer.render(
            "infrastructure/persistence/repositories/repository.py.j2",
            {
                "class_name": f"SqlAlchemy{model.name}Repository",
                "domain_class_name": model.name,
                "domain_module": to_snake_case(model.name),
                "field_mappings": [_field_mapping(field) for field in model.fields],
                "imports": imports_for_repository_methods(methods),
                "methods": [
                    _implementation_method(method, f"{model.name}ORM") for method in methods
                ],
                "orm_class_name": f"{model.name}ORM",
                "orm_module": to_snake_case(model.name),
                "package_name": package_name,
                "port_class_name": f"{model.name}RepositoryPort",
                "port_module": f"{to_snake_case(model.name)}_repository",
            },
        )


def _field_mapping(field: FieldSpec) -> FieldMappingContext:
    return FieldMappingContext(name=field.name)


def _implementation_method(
    method: RepositoryMethodContext,
    orm_class_name: str,
) -> RepositoryImplementationMethodContext:
    return RepositoryImplementationMethodContext(
        name=method.name,
        params=method.params,
        return_type=method.return_type,
        filters=[
            filter_expression_for(filter_context, orm_class_name)
            for filter_context in method.filters
        ],
    )


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
