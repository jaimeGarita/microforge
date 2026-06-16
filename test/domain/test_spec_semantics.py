import pathlib

import pytest
import yaml

from microforge.domain.spec.errors import SpecValidationErrors
from microforge.domain.spec.models import SpecV1
from microforge.domain.spec.semantics import validate_semantics


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


def test_validate_semantics_flattens_generated_field_errors() -> None:
    spec = SpecV1.model_validate(
        {
            "specVersion": 1,
            "project": {"name": "orders-service", "packageName": "orders_service"},
            "target": {
                "language": "python",
                "framework": "fastapi",
                "pythonVersion": "3.12",
                "packaging": "poetry",
            },
            "service": {"name": "orders"},
            "api": {"basePath": "/api/v1", "endpoints": []},
            "models": [
                {
                    "name": "Order",
                    "fields": [
                        {
                            "name": "id",
                            "type": "int",
                            "autoIncrement": True,
                            "primaryKey": False,
                        }
                    ],
                }
            ],
        }
    )

    with pytest.raises(SpecValidationErrors) as exc_info:
        validate_semantics(spec)

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].to_dict() == {
        "message": "Field 'id' is auto_increment but not primary_key.",
        "model": "Order",
    }


def test_validate_semantics_rejects_non_numeric_auto_increment() -> None:
    spec = SpecV1.model_validate(
        {
            "specVersion": 1,
            "project": {"name": "orders-service", "packageName": "orders_service"},
            "target": {
                "language": "python",
                "framework": "fastapi",
                "pythonVersion": "3.12",
                "packaging": "poetry",
            },
            "service": {"name": "orders"},
            "api": {"basePath": "/api/v1", "endpoints": []},
            "models": [
                {
                    "name": "Order",
                    "fields": [
                        {
                            "name": "code",
                            "type": "string",
                            "autoIncrement": True,
                            "primaryKey": True,
                        }
                    ],
                }
            ],
        }
    )

    with pytest.raises(SpecValidationErrors) as exc_info:
        validate_semantics(spec)

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].to_dict() == {
        "message": (
            "Field 'code' is auto_increment but type 'string' is not "
            "autoincrementable. Only int and long are supported."
        ),
        "model": "Order",
    }


@pytest.mark.parametrize("field_type", ["int", "long"])
def test_validate_semantics_accepts_numeric_auto_increment(field_type: str) -> None:
    spec = SpecV1.model_validate(
        {
            "specVersion": 1,
            "project": {"name": "orders-service", "packageName": "orders_service"},
            "target": {
                "language": "python",
                "framework": "fastapi",
                "pythonVersion": "3.12",
                "packaging": "poetry",
            },
            "service": {"name": "orders"},
            "api": {"basePath": "/api/v1", "endpoints": []},
            "models": [
                {
                    "name": "Order",
                    "fields": [
                        {
                            "name": "id",
                            "type": field_type,
                            "autoIncrement": True,
                            "primaryKey": True,
                        }
                    ],
                }
            ],
        }
    )

    validate_semantics(spec)


def test_validate_semantics_rejects_nullable_primary_key() -> None:
    spec = SpecV1.model_validate(
        {
            "specVersion": 1,
            "project": {"name": "orders-service", "packageName": "orders_service"},
            "target": {
                "language": "python",
                "framework": "fastapi",
                "pythonVersion": "3.12",
                "packaging": "poetry",
            },
            "service": {"name": "orders"},
            "api": {"basePath": "/api/v1", "endpoints": []},
            "models": [
                {
                    "name": "Order",
                    "fields": [
                        {
                            "name": "id",
                            "type": "int",
                            "primaryKey": True,
                            "nullable": True,
                        }
                    ],
                }
            ],
        }
    )

    with pytest.raises(SpecValidationErrors) as exc_info:
        validate_semantics(spec)

    assert exc_info.value.errors[0].to_dict() == {
        "message": "Field 'id' is primary_key but nullable.",
        "model": "Order",
    }


def test_validate_semantics_rejects_invalid_field_metadata() -> None:
    spec = SpecV1.model_validate(
        {
            "specVersion": 1,
            "project": {"name": "orders-service", "packageName": "orders_service"},
            "target": {
                "language": "python",
                "framework": "fastapi",
                "pythonVersion": "3.12",
                "packaging": "poetry",
            },
            "service": {"name": "orders"},
            "api": {"basePath": "/api/v1", "endpoints": []},
            "models": [
                {
                    "name": "Order",
                    "fields": [
                        {"name": "count", "type": "int", "minLength": 3},
                        {"name": "status", "type": "string", "minimum": 1},
                        {"name": "priority", "type": "int", "default": "high"},
                        {"name": "kind", "type": "string", "enum": ["a"], "default": "b"},
                    ],
                }
            ],
        }
    )

    with pytest.raises(SpecValidationErrors) as exc_info:
        validate_semantics(spec)

    messages = [error.raw_message for error in exc_info.value.errors]
    assert any("minLength/maxLength" in message for message in messages)
    assert any("minimum/maximum" in message for message in messages)
    assert any("default value 'high' does not match type 'int'" in message for message in messages)
    assert any("default value 'b' is not in enum" in message for message in messages)
