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
        job_description: JobDescription,
    ) -> CandidateCV:
        metadata = UploadedFileMetadata.from_bytes(
            cv.filename,
            cv.content_type,
            cv.content,
        )
        raw_text = await self._cv_parser.parse(cv.filename, cv.content)
        return CandidateCV(metadata=metadata, raw_text=raw_text)