from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml
from pydantic import ValidationError

from microforge.application.spec.ports.outbound import SpecLoaderPort
from microforge.domain.spec.errors import SpecFormatError, SpecIssue
from microforge.domain.spec.models import SpecV1


class YamlSpecLoader(SpecLoaderPort):
    """Load a YAML spec from disk or bytes and validate it with Pydantic."""

    def load_bytes(self, data: bytes) -> SpecV1:
        try:
            parsed = yaml.safe_load(data)
        except yaml.YAMLError as exc:
            issue = SpecIssue(
                code="invalid_yaml",
                message=str(exc),
                path=_yaml_error_path(exc),
            )
            raise SpecFormatError(
                "The YAML payload is invalid.", code="invalid_yaml", issues=[issue]
            ) from exc
        return self._validate(parsed)

    def _validate(self, data: Any) -> SpecV1:
        try:
            return SpecV1.model_validate(data)
        except ValidationError as exc:
            issues = [_pydantic_issue(error) for error in exc.errors(include_url=False)]
            raise SpecFormatError("The specification structure is invalid.", issues=issues) from exc


def _pydantic_issue(error: Mapping[str, Any]) -> SpecIssue:
    error_type = str(error["type"])
    return SpecIssue(
        code=_pydantic_error_code(error_type, tuple(error["loc"])),
        message=str(error["msg"]),
        path=_format_path(tuple(error["loc"])),
    )


def _pydantic_error_code(error_type: str, location: tuple[Any, ...]) -> str:
    if location == ("specVersion",) and error_type == "literal_error":
        return "unsupported_spec_version"
    if error_type == "extra_forbidden":
        return "unknown_property"
    if error_type == "missing":
        return "missing_field"
    if error_type == "enum":
        return "invalid_enum_value"
    if error_type == "literal_error":
        return "invalid_literal"
    return "invalid_value"


def _format_path(location: tuple[Any, ...]) -> str:
    path = ""
    for part in location:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)
    return path or "$"


def _yaml_error_path(error: yaml.YAMLError) -> str:
    mark = getattr(error, "problem_mark", None)
    if mark is None:
        return "$"
    return f"line {mark.line + 1}, column {mark.column + 1}"
