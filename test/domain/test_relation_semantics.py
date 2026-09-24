from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from microforge.domain.spec.errors import SpecValidationErrors
from microforge.domain.spec.models import SpecV1
from microforge.domain.spec.semantics import validate_semantics


def _valid_relation_data() -> dict[str, object]:
    return {
        "models": [
            {
                "name": "Customer",
                "fields": [{"name": "id", "type": "int", "primaryKey": True}],
            },
            {
                "name": "Order",
                "fields": [
                    {"name": "id", "type": "int", "primaryKey": True},
                    {"name": "customer_id", "type": "int"},
                ],
                "relations": [
                    {
                        "name": "customer",
                        "type": "manyToOne",
                        "target": "Customer",
                        "localField": "customer_id",
                        "targetField": "id",
                    }
                ],
            },
        ]
    }


def _messages(data: dict[str, object]) -> list[str]:
    spec = SpecV1.model_validate(data)
    with pytest.raises(SpecValidationErrors) as exc_info:
        validate_semantics(spec)
    return [error.raw_message for error in exc_info.value.errors]


def test_validate_relations_accepts_valid_many_to_one() -> None:
    spec = SpecV1.model_validate(_valid_relation_data())

    validate_semantics(spec)


def test_relation_type_rejects_unsupported_cardinalities() -> None:
    data = _valid_relation_data()
    data["models"][1]["relations"][0]["type"] = "manyToMany"  # type: ignore[index]

    with pytest.raises(ValidationError):
        SpecV1.model_validate(data)


def test_validate_relations_rejects_missing_target_model() -> None:
    data = _valid_relation_data()
    data["models"][1]["relations"][0]["target"] = "Missing"  # type: ignore[index]

    assert any("missing target model 'Missing'" in message for message in _messages(data))


@pytest.mark.parametrize(
    ("field_key", "field_name", "expected"),
    [
        ("localField", "missing", "missing local field 'missing'"),
        ("targetField", "missing", "missing target field 'Customer.missing'"),
    ],
)
def test_validate_relations_rejects_missing_fields(
    field_key: str, field_name: str, expected: str
) -> None:
    data = _valid_relation_data()
    data["models"][1]["relations"][0][field_key] = field_name  # type: ignore[index]

    assert any(expected in message for message in _messages(data))


def test_validate_relations_rejects_incompatible_field_types() -> None:
    data = _valid_relation_data()
    data["models"][1]["fields"][1]["type"] = "uuid"  # type: ignore[index]

    assert any("incompatible types" in message for message in _messages(data))


def test_validate_relations_requires_unique_target_field() -> None:
    data = _valid_relation_data()
    target = data["models"][0]["fields"][0]  # type: ignore[index]
    target["primaryKey"] = False

    assert any("must be primary key or unique" in message for message in _messages(data))


def test_validate_relations_rejects_auto_increment_local_field() -> None:
    data = _valid_relation_data()
    local = data["models"][1]["fields"][1]  # type: ignore[index]
    local["primaryKey"] = True
    local["autoIncrement"] = True

    assert any("cannot be auto increment" in message for message in _messages(data))


def test_validate_relations_rejects_reused_local_field() -> None:
    data = _valid_relation_data()
    relation = data["models"][1]["relations"][0]  # type: ignore[index]
    duplicate = deepcopy(relation)
    duplicate["name"] = "billing_customer"
    data["models"][1]["relations"].append(duplicate)  # type: ignore[index]

    assert any("used by multiple relations" in message for message in _messages(data))
