from pydantic import BaseModel


class CVOptimizeResponse(BaseModel):
    optimized_content: str
    original_variance_score: float
    optimized_variance_score: float
    writer_attempts: int
    is_within_threshold: bool
