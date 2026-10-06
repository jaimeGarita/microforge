"""Outbound application ports for specification dependencies."""

from __future__ import annotations

from typing import Protocol

from microforge.domain.spec.models import SpecV1


class SpecLoaderPort(Protocol):
    """Abstraction for loading specs from different sources."""

    def load_bytes(self, data: bytes) -> SpecV1: ...


class SpecAdvisorPort(Protocol):
    """Abstraction for recommendation providers."""

    def advise(self, spec: SpecV1) -> dict[str, object]: ...
