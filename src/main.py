import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from src.infrastructure.adapters.inbound.api.routers.auth_router import router as auth_router
from src.infrastructure.database import dispose_engine

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    build_optimize_cv_use_case()
    yield
    await dispose_engine()


app = FastAPI(
    title="CV Aligner AI Backend",
    description="Hexagonal Architecture Multi-Agent CV Optimizer",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(InvalidUploadError, handle_invalid_upload)
app.add_exception_handler(AuditFailedError, handle_audit_failure)
app.include_router(cv_router)
app.include_router(cv_optimize_router)
app.include_router(auth_router, prefix="/auth")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
