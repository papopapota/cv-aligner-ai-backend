from pydantic import BaseModel


class CVUploadResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    extracted_text: str
    characters_extracted: int