"""HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from microforge.application.generation.ports.inbound import GenerateProjectPort
from microforge.application.spec.ports.inbound import ValidateSpecPort
from microforge.domain.spec.errors import SpecError, SpecValidationErrors
from microforge.infrastructure.inbound.api.v1.providers import (
    get_generate_project_port,
    get_validate_spec_port,
)

router = APIRouter()
SUPPORTED_EXT = (".yaml", ".yml")


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
    except SpecValidationErrors as exc:
        detail = [err.to_dict() for err in exc.errors]
        raise HTTPException(status_code=400, detail=detail) from exc
    except SpecError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    except SpecValidationErrors as exc:
        detail = [err.to_dict() for err in exc.errors]
        raise HTTPException(status_code=400, detail=detail) from exc
    except SpecError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="microforge-project.zip"'},
    )


async def _read_yaml_upload(file: UploadFile) -> bytes:
    filename = (file.filename or "").lower()
    if not filename.endswith(SUPPORTED_EXT):
        raise HTTPException(
            status_code=400,
            detail="Only .yaml/.yml files are accepted",
        )
    return await file.read()
