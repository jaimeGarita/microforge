from __future__ import annotations

from typing import Any

import yaml
from pydantic import ValidationError

from microforge.application.spec.ports.outbound import SpecLoaderPort
from microforge.domain.spec.errors import SpecFormatError
from microforge.domain.spec.models import SpecV1


class YamlSpecLoader(SpecLoaderPort):
    """Load a YAML spec from disk or bytes and validate it with Pydantic."""

    def load_bytes(self, data: bytes) -> SpecV1:
        try:
            parsed = yaml.safe_load(data)
        except yaml.YAMLError as exc:
            raise SpecFormatError(f"Invalid YAML payload: {exc}") from exc
        return self._validate(parsed)

    def _validate(self, data: Any) -> SpecV1:
        try:
            return SpecV1.model_validate(data)
        except ValidationError as exc:
            raise SpecFormatError(f"Invalid spec structure: {exc}") from exc
