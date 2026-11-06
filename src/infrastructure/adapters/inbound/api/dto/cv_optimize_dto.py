from pydantic import BaseModel


class CVOptimizeResponse(BaseModel):
    optimized_content: str
    original_variance_score: float
    optimized_variance_score: float
    writer_attempts: int
    is_within_threshold: bool
    original_ic: float | None
    optimized_ic: float | None
    original_per_dimension: dict[str, float]
    optimized_per_dimension: dict[str, float]
    gap_report: str
