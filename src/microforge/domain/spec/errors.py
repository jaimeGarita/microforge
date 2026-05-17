"""Domain-level error types."""


class SpecError(Exception):
    """Base class for specification-related errors."""


class SpecFormatError(SpecError):
    """Raised when spec content cannot be parsed or validated structurally."""


class SpecSemanticError(SpecError):
    """Semantic validation errors for the spec (invalid field references, bad queries, incoherent features)."""

    def __init__(self, message: str, *, model: str | None = None):
        self.raw_message = message
        self.model = model
        if model:
            message = f"[Model: {model}] {message}"
        super().__init__(message)

    def to_dict(self) -> dict[str, str]:
        """Serialize error in a transport-friendly format."""
        payload = {"message": self.raw_message}
        if self.model:
            payload["model"] = self.model
        return payload


class SpecValidationErrors(SpecError):
    """Container for multiple semantic validation errors."""

    def __init__(self, errors: list[SpecSemanticError]):
        self.errors = errors
        message = "; ".join(str(err) for err in errors)
        super().__init__(message)
