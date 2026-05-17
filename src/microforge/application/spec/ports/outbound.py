"""Outbound application ports for spec dependencies."""

from __future__ import annotations

from typing import Protocol

from microforge.domain.spec.models import SpecV1


class SpecLoaderPort(Protocol):
    """Abstraction for loading specs from different sources."""

    def load_bytes(self, data: bytes) -> SpecV1:
        ...
