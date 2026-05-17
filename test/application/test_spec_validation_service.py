import pathlib

import pytest
import yaml

from microforge.application.spec.ports import SpecLoaderPort
from microforge.application.spec.validate_spec import ValidateSpecService
from microforge.domain.spec.errors import SpecValidationErrors
from microforge.domain.spec.models import SpecV1


class InMemoryLoader(SpecLoaderPort):
    def __init__(self, raw: dict):
        self.raw = raw

    def load(self, path: str) -> SpecV1:
        del path
        return SpecV1.model_validate(self.raw)

    def load_bytes(self, data: bytes) -> SpecV1:
        del data
        return SpecV1.model_validate(self.raw)


def _load_yaml(path: str) -> dict:
    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_validate_spec_service_accepts_valid_spec() -> None:
    service = ValidateSpecService(InMemoryLoader(_load_yaml("examples/spec_valid.yaml")))
    service.run("unused-path.yaml")


def test_validate_spec_service_reports_all_semantic_errors() -> None:
    service = ValidateSpecService(InMemoryLoader(_load_yaml("examples/spec_invalid.yaml")))

    with pytest.raises(SpecValidationErrors) as exc_info:
        service.run_bytes(b"unused")

    assert len(exc_info.value.errors) == 2
