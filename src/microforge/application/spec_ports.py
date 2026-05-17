"""Application ports."""

from __future__ import annotations

from typing import Protocol

from microforge.domain.spec_models import SpecV1


class SpecLoaderPort(Protocol):
    """Abstraction for loading specs from different sources."""

    def load(self, path: str) -> SpecV1:
        ...

    def load_bytes(self, data: bytes) -> SpecV1:
        ...
