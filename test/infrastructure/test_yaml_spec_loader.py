from microforge.domain.spec.errors import SpecFormatError
from microforge.infrastructure.spec.yaml_spec_loader import YamlSpecLoader


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


def test_load_from_missing_path_raises_file_not_found() -> None:
    loader = YamlSpecLoader()
    try:
        loader.load("examples/does-not-exist.yaml")
    except FileNotFoundError as exc:
        assert "Spec not found at" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for a missing file")
