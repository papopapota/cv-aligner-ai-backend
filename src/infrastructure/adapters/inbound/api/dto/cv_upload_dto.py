from pydantic import BaseModel


class CVUploadResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    extracted_text: str
    characters_extracted: int
    jd_filename: str
    jd_content_type: str
    jd_size_bytes: int
    jd_sha256: str
    jd_extracted_text: str
    jd_characters_extracted: int