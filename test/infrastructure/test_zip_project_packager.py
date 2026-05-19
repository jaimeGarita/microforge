import io
import zipfile

import pytest

from microforge.domain.generation.project_file import ProjectFile
from microforge.infrastructure.outbound.generation.zip_project_packager import ZipProjectPackager


def test_zip_project_packager_returns_zip_bytes() -> None:
    files = [
        ProjectFile(path="README.md", content=b"# demo\n"),
        ProjectFile(path="src/main.py", content=b"print('ok')\n"),
    ]

    archive = ZipProjectPackager().package(files)

    with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
        assert sorted(zip_file.namelist()) == ["README.md", "src/main.py"]
        assert zip_file.read("README.md") == b"# demo\n"


def test_zip_project_packager_rejects_unsafe_paths() -> None:
    files = [ProjectFile(path="../secret.txt", content=b"nope")]

    with pytest.raises(ValueError, match="Unsafe generated file path"):
        ZipProjectPackager().package(files)
