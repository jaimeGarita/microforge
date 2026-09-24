"""Domain-level error types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecIssue:
    """A machine-readable issue associated with a specification."""

    code: str
    message: str
    path: str | None = None
    model: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {"code": self.code, "message": self.message}
        if self.path is not None:
            payload["path"] = self.path
        if self.model is not None:
            payload["model"] = self.model
        return payload


class SpecError(Exception):
    """Base class for specification-related errors."""


class SpecFormatError(SpecError):
    """Raised when spec content cannot be parsed or validated structurally."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_spec_structure",
        issues: list[SpecIssue] | None = None,
    ):
        self.code = code
        self.issues = issues or []
        super().__init__(message)


class SpecSemanticError(SpecError):
    """Semantic validation errors for the spec (invalid field references, bad queries, incoherent features)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "semantic_error",
        path: str | None = None,
        model: str | None = None,
    ):
        self.raw_message = message
        self.code = code
        self.path = path
        self.model = model
        if model:
            message = f"[Model: {model}] {message}"
        super().__init__(message)

    def to_dict(self) -> dict[str, str]:
        """Serialize error in a transport-friendly format."""
        return SpecIssue(
            code=self.code,
            message=self.raw_message,
            path=self.path,
            model=self.model,
        ).to_dict()


class SpecValidationErrors(SpecError):
    """Container for multiple semantic validation errors."""

    def __init__(self, errors: list[SpecSemanticError]):
        self.errors = errors
        message = "; ".join(str(err) for err in errors)
        super().__init__(message)
