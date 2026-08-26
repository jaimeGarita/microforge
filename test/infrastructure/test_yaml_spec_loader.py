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
        assert "Invalid YAML payload" in str(exc)
    else:
        raise AssertionError("Expected SpecFormatError for malformed YAML")


def test_load_bytes_rejects_invalid_structure() -> None:
    payload = b"[]"
    loader = YamlSpecLoader()
    try:
        loader.load_bytes(payload)
    except SpecFormatError as exc:
        assert "Invalid spec structure" in str(exc)
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
    with pytest.raises(SpecFormatError, match="Invalid spec structure"):
        YamlSpecLoader().load_bytes(payload)
