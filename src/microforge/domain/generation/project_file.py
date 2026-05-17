"""Generated project file value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectFile:
    path: str
    content: bytes
