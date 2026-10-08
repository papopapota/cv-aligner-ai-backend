from fastapi import Request, status
from fastapi.responses import JSONResponse


async def handle_audit_failure(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )
