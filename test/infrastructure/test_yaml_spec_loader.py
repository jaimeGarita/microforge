import pytest

from microforge.domain.spec.errors import SpecFormatError
from microforge.infrastructure.outbound.spec.yaml_spec_loader import YamlSpecLoader


def test_load_bytes_parses_valid_yaml() -> None:
    payload = b"""
specVersion: 1
target:
  language: python
  framework: fastapi
models: []
"""
    loader = YamlSpecLoader()
    spec = loader.load_bytes(payload)
    assert spec.spec_version == 1


def test_load_bytes_rejects_invalid_yaml() -> None:
    payload = b"specVersion: ["
    loader = YamlSpecLoader()
    try:
        loader.load_bytes(payload)
    except SpecFormatError as exc:
        assert str(exc) == "The YAML payload is invalid."
        assert exc.code == "invalid_yaml"
        assert exc.issues[0].code == "invalid_yaml"
        assert exc.issues[0].path == "line 1, column 15"
    else:
        raise AssertionError("Expected SpecFormatError for malformed YAML")


def test_load_bytes_rejects_invalid_structure() -> None:
    payload = b"[]"
    loader = YamlSpecLoader()
    try:
        loader.load_bytes(payload)
    except SpecFormatError as exc:
        assert str(exc) == "The specification structure is invalid."
        assert exc.code == "invalid_spec_structure"
        assert exc.issues[0].path == "$"
    else:
        raise AssertionError("Expected SpecFormatError for invalid structure")


@pytest.mark.parametrize(
    "payload",
    [
        b"specVersion: 2\n",
        b"specVersion: 1\nunexpected: true\n",
        b"specVersion: 1\nmodels:\n  - name: User\n    fields:\n      - name: id\n        type: int\n        primariKey: true\n",
    ],
)
def test_load_bytes_rejects_unsupported_versions_and_unknown_fields(payload: bytes) -> None:
    with pytest.raises(SpecFormatError, match="The specification structure is invalid"):
        YamlSpecLoader().load_bytes(payload)


def test_load_bytes_reports_machine_readable_field_path() -> None:
    payload = b"""
specVersion: 1
models:
  - name: User
    fields:
      - name: id
        type: unknown
"""

    with pytest.raises(SpecFormatError) as exc_info:
        YamlSpecLoader().load_bytes(payload)

    issue = exc_info.value.issues[0]
    assert issue.code == "invalid_enum_value"
    assert issue.path == "models[0].fields[0].type"
