import pytest

from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.models import SpecV1
from microforge.domain.spec.types import TargetFramework, TargetLanguage
from microforge.infrastructure.outbound.generation.strategy.default_project_generator_registry import (
    default_project_generator_registry,
)
from microforge.infrastructure.outbound.generation.strategy.errors import (
    UnsupportedTargetError,
)
from microforge.infrastructure.outbound.generation.strategy.registry import (
    ProjectGeneratorRegistry,
)
from microforge.infrastructure.outbound.generation.strategy.target_project_generator import (
    TargetProjectGenerator,
)
from microforge.infrastructure.outbound.generation.targets.python.fastapi.generator import (
    PythonFastApiProjectGenerator,
)


class DummyProjectGenerator:
    def __init__(self) -> None:
        self.received_spec: SpecV1 | None = None

    def generate(self, spec: SpecV1) -> list[ProjectFile]:
        self.received_spec = spec
        return [ProjectFile(path="README.md", content=b"dummy")]


def test_default_project_generator_registry_resolves_python_fastapi() -> None:
    registry = default_project_generator_registry()

    generator = registry.resolve(TargetLanguage.python, TargetFramework.fastapi)

    assert isinstance(generator, PythonFastApiProjectGenerator)


def test_project_generator_registry_raises_for_missing_target() -> None:
    registry = ProjectGeneratorRegistry({})

    with pytest.raises(UnsupportedTargetError) as exc_info:
        registry.resolve(TargetLanguage.python, TargetFramework.fastapi)

    assert str(exc_info.value) == "Unsupported target: language=python, framework=fastapi"


def test_target_project_generator_delegates_to_resolved_generator() -> None:
    spec = SpecV1()
    dummy_generator = DummyProjectGenerator()
    registry = ProjectGeneratorRegistry(
        {
            (TargetLanguage.python, TargetFramework.fastapi): dummy_generator,
        }
    )

    files = TargetProjectGenerator(registry).generate(spec)

    assert files == [ProjectFile(path="README.md", content=b"dummy")]
    assert dummy_generator.received_spec is spec
