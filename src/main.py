from fastapi import FastAPI

from src.domain.errors import InvalidUploadError
from src.infrastructure.adapters.inbound.api.cv_controller import (
    router as cv_router,
)
from src.infrastructure.adapters.inbound.api.domain_error_handler import (
    handle_invalid_upload,
)

app = FastAPI(
    title="CV Aligner AI Backend",
    description="Hexagonal Architecture Multi-Agent CV Optimizer",
    version="0.1.0",
)

app.add_exception_handler(InvalidUploadError, handle_invalid_upload)
app.include_router(cv_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}