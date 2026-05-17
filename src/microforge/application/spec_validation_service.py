"""Application use cases."""

from __future__ import annotations

from microforge.application.spec_ports import SpecLoaderPort
from microforge.domain.spec_semantics import validate_semantics


class ValidateSpecService:
    """Use case: load a spec and run semantic validation."""

    def __init__(self, loader: SpecLoaderPort):
        self.loader = loader

    def run(self, path: str) -> None:
        spec = self.loader.load(path)
        validate_semantics(spec)

    def run_bytes(self, data: bytes) -> None:
        spec = self.loader.load_bytes(data)
        validate_semantics(spec)
