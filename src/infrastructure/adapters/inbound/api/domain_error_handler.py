from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.errors import CVFailedError
from src.infrastructure.adapters.inbound.api.dto.cv_dto import (
    ACTION_REQUIRED_REUPLOAD_CV,
    ACTION_REQUIRED_WAIT_FOR_PARSING,
)


async def handle_invalid_upload(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def handle_cv_not_found(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def handle_cv_not_ready(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "action_required": ACTION_REQUIRED_WAIT_FOR_PARSING,
        },
    )


async def handle_cv_failed(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    error = exc if isinstance(exc, CVFailedError) else None
    return JSONResponse(
        status_code=409,
        content={
            "detail": (
                error.error_message
                if error is not None
                else "The CV could not be processed."
            ),
            "error_code": error.error_code if error is not None else None,
            "action_required": ACTION_REQUIRED_REUPLOAD_CV,
        },
    )


async def handle_storage_error(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "Storage service unavailable."},
    )
