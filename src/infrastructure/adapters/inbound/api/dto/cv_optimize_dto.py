from pydantic import BaseModel


class CVOptimizeResponse(BaseModel):
    optimized_content: str
    variance_score: float
    writer_attempts: int
    is_within_threshold: bool
    r_total: float | None
    per_dimension: dict[str, float]
    gap_report: str
