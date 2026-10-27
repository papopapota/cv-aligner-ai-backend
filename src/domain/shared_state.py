from dataclasses import dataclass


@dataclass(slots=True)
class SharedState:
    candidate_cv_text: str
    job_description_text: str
    extracted_profile: str = ""
    gap_analysis: str = ""
    optimized_text: str = ""
    original_variance_score: float = 1.0
    optimized_variance_score: float = 1.0
    audit_reason: str = ""
    writer_attempts: int = 0
