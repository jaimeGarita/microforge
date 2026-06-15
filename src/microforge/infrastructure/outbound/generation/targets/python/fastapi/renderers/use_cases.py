"""Render application use cases for FastAPI projects."""

from __future__ import annotations

from dataclasses import dataclass

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import ModelSpec, SpecV1
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.naming import (
    package_name_for,
    to_snake_case,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.renderers.repository_methods import (
    RepositoryMethodContext,
    repository_methods_for,
)
from microforge.infrastructure.outbound.generation.template_renderer import TemplateRenderer


@dataclass(frozen=True)
class UseCaseContext:
    """Use case data prepared for application templates."""

    class_name: str
    filename: str
    params: str
    repository_method_name: str
    repository_param_names: str
    return_type: str
    imports: list[str]


class UseCasesRenderer:
    """Render application use cases required by repository methods."""

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    def render(self, spec: SpecV1) -> list[ProjectFile]:
        package_name = package_name_for(spec.project_config.package_name)
        base_path = f"src/{package_name}/application/use_cases"
        files = [
            ProjectFile(
                path=f"{base_path}/__init__.py",
                content=_encode(""),
            )
        ]

        for model in spec.models:
            if not model.features.repository:
                continue
            model_path = f"{base_path}/{to_snake_case(model.name)}"
            methods = repository_methods_for(model, spec.api.endpoints)
            if not methods:
                continue
            files.append(ProjectFile(path=f"{model_path}/__init__.py", content=_encode("")))
            files.extend(
                ProjectFile(
                    path=f"{model_path}/{use_case.filename}.py",
                    content=_encode(self._render_use_case(model, package_name, use_case)),
                )
                for use_case in [use_case_for_method(model, method) for method in methods]
            )
        return files

    def _render_use_case(
        self,
        model: ModelSpec,
        package_name: str,
        use_case: UseCaseContext,
    ) -> str:
        return self.renderer.render(
            "application/use_cases/use_case.py.j2",
            {
                "class_name": use_case.class_name,
                "domain_class_name": model.name,
                "domain_module": to_snake_case(model.name),
                "imports": use_case.imports,
                "package_name": package_name,
                "params": use_case.params,
                "repository_class_name": f"{model.name}RepositoryPort",
                "repository_method_name": use_case.repository_method_name,
                "repository_module": f"{to_snake_case(model.name)}_repository",
                "repository_param_names": use_case.repository_param_names,
                "return_type": use_case.return_type,
            },
        )


def use_case_for_method(model: ModelSpec, method: RepositoryMethodContext) -> UseCaseContext:
    """Return the use case generated for a repository method."""

    return UseCaseContext(
        class_name=_use_case_class_name(model, method),
        filename=_use_case_filename(model, method),
        params=method.params,
        repository_method_name=method.name,
        repository_param_names=_param_names(method.params),
        return_type=method.return_type,
        imports=method.imports,
    )


def _use_case_class_name(model: ModelSpec, method: RepositoryMethodContext) -> str:
    plural_model_name = f"{model.name}s"
    if method.name == "find_all":
        return f"List{plural_model_name}UseCase"
    if method.name == "find_by_id":
        return f"Get{model.name}ByIdUseCase"
    if method.name == "save":
        return f"Create{model.name}UseCase"
    if method.name == "update":
        return f"Update{model.name}UseCase"
    if method.name == "delete_by_id":
        return f"Delete{model.name}ByIdUseCase"
    if method.name.startswith("find_by_"):
        suffix = _pascal_case(method.name.removeprefix("find_by_"))
        return f"Find{plural_model_name}By{suffix}UseCase"
    return f"{_pascal_case(method.name)}{model.name}UseCase"


def _use_case_filename(model: ModelSpec, method: RepositoryMethodContext) -> str:
    plural_model_name = f"{to_snake_case(model.name)}s"
    if method.name == "find_all":
        return f"list_{plural_model_name}"
    if method.name == "find_by_id":
        return f"get_{to_snake_case(model.name)}_by_id"
    if method.name == "save":
        return f"create_{to_snake_case(model.name)}"
    if method.name == "update":
        return f"update_{to_snake_case(model.name)}"
    if method.name == "delete_by_id":
        return f"delete_{to_snake_case(model.name)}_by_id"
    if method.name.startswith("find_by_"):
        return f"find_{plural_model_name}_by_{method.name.removeprefix('find_by_')}"
    return f"{method.name}_{to_snake_case(model.name)}"


def _pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in to_snake_case(value).split("_"))


def _param_names(params: str) -> str:
    if not params:
        return ""
    return ", ".join(param.split(":", maxsplit=1)[0].strip() for param in params.split(","))


def _encode(content: str) -> bytes:
    return content.encode("utf-8")
