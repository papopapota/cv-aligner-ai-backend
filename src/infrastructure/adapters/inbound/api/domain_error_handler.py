from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.errors import InvalidUploadError


async def handle_invalid_upload(
    request: Request,
    exc: InvalidUploadError,
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})