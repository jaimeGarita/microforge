"""Inbound application ports for project generation."""

from __future__ import annotations

from typing import Protocol


class GenerateProjectPort(Protocol):
    """Input contract used by inbound adapters to generate projects."""

    def run_bytes(self, data: bytes) -> bytes:
        ...
