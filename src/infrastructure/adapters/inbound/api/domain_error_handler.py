from fastapi import Request
from fastapi.responses import JSONResponse


async def handle_invalid_upload(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})