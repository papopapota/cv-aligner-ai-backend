from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.application.ports.inbound.upload_cv_use_case import (
    FileUpload,
    UploadCVUseCase,
)
from src.application.services.upload_cv_service import UploadCVService
from src.domain.candidate_cv import CandidateCV
from src.domain.job_description import JobDescription
from src.infrastructure.adapters.inbound.api.dto.cv_upload_dto import (
    CVUploadResponse,
)
from src.infrastructure.adapters.out.document_parser_adapter import (
    DocumentParserAdapter,
)

router = APIRouter(tags=["cv"])


def get_upload_cv_use_case() -> UploadCVUseCase:
    return UploadCVService(DocumentParserAdapter())


@router.post("/cv/upload", response_model=CVUploadResponse)
async def upload_cv(
    cv_file: UploadFile = File(...),
    job_description: str = Form(...),
    use_case: UploadCVUseCase = Depends(get_upload_cv_use_case),
) -> CVUploadResponse:
    content = await cv_file.read()
    candidate = await use_case.execute(
        cv=FileUpload(
            filename=cv_file.filename or "",
            content_type=cv_file.content_type or "",
            content=content,
        ),
        job_description=JobDescription(raw_text=job_description),
    )
    return _to_response(candidate)


def _to_response(candidate: CandidateCV) -> CVUploadResponse:
    metadata = candidate.metadata
    return CVUploadResponse(
        filename=metadata.filename,
        content_type=metadata.content_type,
        size_bytes=metadata.size_bytes,
        sha256=metadata.sha256,
        extracted_text=candidate.raw_text,
        characters_extracted=len(candidate.raw_text),
    )