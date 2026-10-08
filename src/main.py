from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.composition import build_optimize_cv_use_case
from src.domain.errors import AuditFailedError, InvalidUploadError
from src.infrastructure.adapters.inbound.api.audit_error_handler import (
    handle_audit_failure,
)
from src.infrastructure.adapters.inbound.api.cv_controller import (
    router as cv_router,
)
from src.infrastructure.adapters.inbound.api.cv_optimize_controller import (
    router as cv_optimize_router,
)
from src.infrastructure.adapters.inbound.api.domain_error_handler import (
    handle_invalid_upload,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    build_optimize_cv_use_case()
    yield


app = FastAPI(
    title="CV Aligner AI Backend",
    description="Hexagonal Architecture Multi-Agent CV Optimizer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(InvalidUploadError, handle_invalid_upload)
app.add_exception_handler(AuditFailedError, handle_audit_failure)
app.include_router(cv_router)
app.include_router(cv_optimize_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
