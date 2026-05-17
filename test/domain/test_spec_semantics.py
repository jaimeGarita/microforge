import pathlib

import pytest
import yaml

from microforge.domain.spec_errors import SpecValidationErrors
from microforge.domain.spec_models import SpecV1
from microforge.domain.spec_semantics import validate_semantics


def _load_yaml(path: str) -> dict:
    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_validate_semantics_accepts_valid_spec() -> None:
    raw = _load_yaml("examples/spec_valid.yaml")
    spec = SpecV1.model_validate(raw)

    validate_semantics(spec)


def test_validate_semantics_returns_all_semantic_errors() -> None:
    raw = _load_yaml("examples/spec_invalid.yaml")
    spec = SpecV1.model_validate(raw)

    with pytest.raises(SpecValidationErrors) as exc_info:
        validate_semantics(spec)

    errors = exc_info.value.errors
    assert len(errors) == 2
    assert all(err.model == "Order" for err in errors)
    messages = [err.raw_message for err in errors]
    assert any("references missing fields" in message for message in messages)
    assert any("features.repository is false" in message for message in messages)
