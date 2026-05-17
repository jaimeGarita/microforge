"""HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from microforge.api.v1.providers import get_validate_service
from microforge.application.spec.validate_spec import ValidateSpecService
from microforge.domain.spec.errors import SpecError, SpecValidationErrors

router = APIRouter()
SUPPORTED_EXT = (".yaml", ".yml")


@router.get("/health")
def health() -> dict[str, str]:
    """Return a basic liveness response."""
    return {"status": "ok"}


@router.post("/spec/validate")
async def validate_spec(
    file: Annotated[UploadFile, File(...)],
    service: Annotated[ValidateSpecService, Depends(get_validate_service)],
) -> dict[str, bool]:
    """Validate a YAML spec uploaded as multipart/form-data."""
    filename = (file.filename or "").lower()
    if not filename.endswith(SUPPORTED_EXT):
        raise HTTPException(
            status_code=400,
            detail="Only .yaml/.yml files are accepted",
        )
    content = await file.read()
    try:
        service.run_bytes(content)
    except SpecValidationErrors as exc:
        detail = [err.to_dict() for err in exc.errors]
        raise HTTPException(status_code=400, detail=detail) from exc
    except SpecError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}
