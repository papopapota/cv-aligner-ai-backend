from fastapi import APIRouter, Depends, File, UploadFile

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
    job_description_file: UploadFile = File(...),
    use_case: UploadCVUseCase = Depends(get_upload_cv_use_case),
) -> CVUploadResponse:
    cv_content = await cv_file.read()
    jd_content = await job_description_file.read()
    candidate, job_description = await use_case.execute(
        cv=FileUpload(
            filename=cv_file.filename or "",
            content_type=cv_file.content_type or "",
            content=cv_content,
        ),
        job_description=FileUpload(
            filename=job_description_file.filename or "",
            content_type=job_description_file.content_type or "",
            content=jd_content,
        ),
    )
    return _to_response(candidate, job_description)


def _to_response(candidate: CandidateCV, job_description: JobDescription) -> CVUploadResponse:
    cv_metadata = candidate.metadata
    jd_metadata = job_description.metadata
    return CVUploadResponse(
        filename=cv_metadata.filename,
        content_type=cv_metadata.content_type,
        size_bytes=cv_metadata.size_bytes,
        sha256=cv_metadata.sha256,
        extracted_text=candidate.raw_text,
        characters_extracted=len(candidate.raw_text),
        jd_filename=jd_metadata.filename,
        jd_content_type=jd_metadata.content_type,
        jd_size_bytes=jd_metadata.size_bytes,
        jd_sha256=jd_metadata.sha256,
        jd_extracted_text=job_description.raw_text,
        jd_characters_extracted=len(job_description.raw_text),
    )