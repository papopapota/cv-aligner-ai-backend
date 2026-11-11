import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.composition import build_file_storage, build_optimize_cv_use_case
from src.domain.errors import (
    CVFailedError,
    CVNotFoundError,
    CVNotReadyError,
    InvalidUploadError,
    StorageError,
)
from src.infrastructure.adapters.inbound.api.cv_controller import (
    router as cv_router,
)
from src.infrastructure.adapters.inbound.api.cv_optimize_controller import (
    router as cv_optimize_router,
)
from src.infrastructure.adapters.inbound.api.domain_error_handler import (
    handle_cv_failed,
    handle_cv_not_found,
    handle_cv_not_ready,
    handle_invalid_upload,
    handle_storage_error,
)
from src.infrastructure.adapters.inbound.api.routers.application_router import (
    router as application_router,
)
from src.infrastructure.adapters.inbound.api.routers.auth_router import router as auth_router
from src.infrastructure.adapters.inbound.api.routers.cv_router import (
    router as cvs_router,
)
from src.infrastructure.config import CORSSettings
from src.infrastructure.database import dispose_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    build_optimize_cv_use_case()
    try:
        await build_file_storage().ensure_bucket()
    except StorageError:
        logger.warning("Could not ensure the CV storage bucket exists.")
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
    allow_origins=CORSSettings().allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(InvalidUploadError, handle_invalid_upload)
app.add_exception_handler(CVNotFoundError, handle_cv_not_found)
app.add_exception_handler(CVNotReadyError, handle_cv_not_ready)
app.add_exception_handler(CVFailedError, handle_cv_failed)
app.add_exception_handler(StorageError, handle_storage_error)
app.include_router(cv_router)
app.include_router(cv_optimize_router)
app.include_router(cvs_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(application_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
