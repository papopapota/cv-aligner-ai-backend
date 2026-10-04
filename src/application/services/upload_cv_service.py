from src.application.ports.inbound.upload_cv_use_case import (
    FileUpload,
    UploadCVUseCase,
)
from src.application.ports.out.cv_parser_port import CVParserPort
from src.domain.candidate_cv import CandidateCV
from src.domain.job_description import JobDescription
from src.domain.uploaded_file_metadata import UploadedFileMetadata


class UploadCVService(UploadCVUseCase):
    def __init__(self, cv_parser: CVParserPort) -> None:
        self._cv_parser = cv_parser

    async def execute(
        self,
        cv: FileUpload,
        job_description: FileUpload,
    ) -> tuple[CandidateCV, JobDescription]:
        cv_metadata = UploadedFileMetadata.from_bytes(
            cv.filename,
            cv.content_type,
            cv.content,
        )
        cv_raw_text = await self._cv_parser.parse(cv.filename, cv.content)
        candidate_cv = CandidateCV(metadata=cv_metadata, raw_text=cv_raw_text)

        jd_metadata = UploadedFileMetadata.from_job_description_bytes(
            job_description.filename,
            job_description.content_type,
            job_description.content,
        )
        jd_raw_text = await self._cv_parser.parse(job_description.filename, job_description.content)
        job_desc = JobDescription(metadata=jd_metadata, raw_text=jd_raw_text)

        return candidate_cv, job_desc