from __future__ import annotations

import pathlib
from typing import Any

import yaml
from pydantic import ValidationError

from microforge.application.spec_ports import SpecLoaderPort
from microforge.domain.spec_errors import SpecFormatError
from microforge.domain.spec_models import SpecV1


class YamlSpecLoader(SpecLoaderPort):
    """Load a YAML spec from disk or bytes and validate it with Pydantic."""

    def load(self, path: str) -> SpecV1:
        data = self._read_yaml(path)
        return self._validate(data)

    def load_bytes(self, data: bytes) -> SpecV1:
        try:
            parsed = yaml.safe_load(data)
        except yaml.YAMLError as exc:
            raise SpecFormatError(f"Invalid YAML payload: {exc}") from exc
        return self._validate(parsed)

    def _read_yaml(self, path: str) -> Any:
        file_path = pathlib.Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Spec not found at {file_path}")
        with file_path.open("r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise SpecFormatError(f"Invalid YAML payload: {exc}") from exc

    def _validate(self, data: Any) -> SpecV1:
        try:
            return SpecV1.model_validate(data)
        except ValidationError as exc:
            raise SpecFormatError(f"Invalid spec structure: {exc}") from exc
