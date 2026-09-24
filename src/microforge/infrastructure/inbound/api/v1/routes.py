"""HTTP routes."""

from __future__ import annotations

from pathlib import PurePath
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from microforge.application.generation.ports.inbound import GenerateProjectPort
from microforge.application.spec.ports.inbound import ValidateSpecPort
from microforge.domain.spec.errors import SpecError, SpecFormatError, SpecValidationErrors
from microforge.infrastructure.inbound.api.v1.providers import (
    get_generate_project_port,
    get_validate_spec_port,
)

router = APIRouter()
SUPPORTED_EXT = (".yaml", ".yml")
MAX_SPEC_BYTES = 1024 * 1024


@router.get("/health")
def health() -> dict[str, str]:
    """Return a basic liveness response."""
    return {"status": "ok"}


@router.post("/spec/validate")
async def validate_spec(
    file: Annotated[UploadFile, File(...)],
    service: Annotated[ValidateSpecPort, Depends(get_validate_spec_port)],
) -> dict[str, bool]:
    """Validate a YAML spec uploaded as multipart/form-data."""
    content = await _read_yaml_upload(file)
    try:
        service.run_bytes(content)
    except SpecError as exc:
        _raise_spec_http_error(exc)
    return {"ok": True}


@router.post("/spec/generate")
async def generate_project(
    file: Annotated[UploadFile, File(...)],
    service: Annotated[GenerateProjectPort, Depends(get_generate_project_port)],
) -> Response:
    """Generate a FastAPI project ZIP from a YAML spec."""
    content = await _read_yaml_upload(file)
    try:
        zip_content = service.run_bytes(content)
    except SpecError as exc:
        _raise_spec_http_error(exc)
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{_zip_filename(file)}"'},
    )


async def _read_yaml_upload(file: UploadFile) -> bytes:
    filename = (file.filename or "").lower()
    if not filename.endswith(SUPPORTED_EXT):
        _raise_api_error(
            400,
            code="unsupported_file_type",
            message="Only .yaml/.yml files are accepted.",
        )
    content = await file.read(MAX_SPEC_BYTES + 1)
    if len(content) > MAX_SPEC_BYTES:
        _raise_api_error(
            413,
            code="spec_too_large",
            message=f"Spec file exceeds the {MAX_SPEC_BYTES}-byte limit.",
        )
    return content


def _zip_filename(file: UploadFile) -> str:
    raw_filename = (file.filename or "microforge-project.yaml").replace("\\", "/")
    filename = PurePath(raw_filename).name
    filename = "".join(character for character in filename if character >= " " and character != '"')
    filename = filename or "microforge-project.yaml"
    lower_filename = filename.lower()
    if lower_filename.endswith(".yaml"):
        return f"{filename[:-5]}.zip"
    if lower_filename.endswith(".yml"):
        return f"{filename[:-4]}.zip"
    return f"{filename}.zip"


def _raise_spec_http_error(error: SpecError) -> NoReturn:
    if isinstance(error, SpecValidationErrors):
        detail = {
            "code": "invalid_spec_semantics",
            "message": "The specification contains semantic errors.",
            "errors": [issue.to_dict() for issue in error.errors],
        }
    elif isinstance(error, SpecFormatError):
        detail = {
            "code": error.code,
            "message": str(error),
            "errors": [issue.to_dict() for issue in error.issues],
        }
    else:
        detail = {
            "code": "invalid_spec",
            "message": str(error),
            "errors": [],
        }
    raise HTTPException(status_code=400, detail=detail) from error


def _raise_api_error(status_code: int, *, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "errors": []},
    )
