"""ZIP project packager adapter."""

from __future__ import annotations

import io
import posixpath
import zipfile

from microforge.application.generation.ports.outbound import ProjectPackagerPort
from microforge.domain.generation.project_file import ProjectFile


class ZipProjectPackager(ProjectPackagerPort):
    """Package generated files as ZIP bytes."""

    def package(self, files: list[ProjectFile]) -> bytes:
        buffer = io.BytesIO()
        paths = [_safe_zip_path(project_file.path) for project_file in files]
        if len(paths) != len(set(paths)):
            duplicates = sorted(path for path in set(paths) if paths.count(path) > 1)
            raise ValueError(f"Duplicate generated file paths: {duplicates}")
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, project_file in zip(paths, files, strict=True):
                archive.writestr(path, project_file.content)
        return buffer.getvalue()


def _safe_zip_path(path: str) -> str:
    normalized = posixpath.normpath(path.replace("\\", "/"))
    if normalized in ("", "."):
        raise ValueError("Generated file path cannot be empty.")
    if normalized.startswith("../") or normalized == ".." or normalized.startswith("/"):
        raise ValueError(f"Unsafe generated file path: {path}")
    return normalized
