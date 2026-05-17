"""Inbound application ports for spec use cases."""

from __future__ import annotations

from typing import Protocol


class ValidateSpecPort(Protocol):
    """Input contract used by inbound adapters to validate specs."""

    def run_bytes(self, data: bytes) -> None:
        ...
