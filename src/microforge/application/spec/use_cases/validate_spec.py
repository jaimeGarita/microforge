"""Spec validation use case."""

from __future__ import annotations

from microforge.application.spec.ports.inbound import ValidateSpecPort
from microforge.application.spec.ports.outbound import SpecLoaderPort
from microforge.domain.spec.semantics import validate_semantics


class ValidateSpecUseCase(ValidateSpecPort):
    """Use case: load a spec and run semantic validation."""

    def __init__(self, loader: SpecLoaderPort):
        self.loader = loader

    def run_bytes(self, data: bytes) -> None:
        spec = self.loader.load_bytes(data)
        validate_semantics(spec)
