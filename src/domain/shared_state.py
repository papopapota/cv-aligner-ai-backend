from dataclasses import dataclass, field

from src.domain.compatibility_score import CompatibilityScore
from src.domain.semantic_profile import SemanticProfile


@dataclass(slots=True)
class SharedState:
    candidate_cv_text: str
    job_description_text: str
    extracted_profile: str = ""
    candidate_profile: SemanticProfile | None = None
    job_profile: SemanticProfile | None = None
    baseline_match: CompatibilityScore | None = None
    optimized_match: CompatibilityScore | None = None
    gap_analysis: str = ""
    optimized_text: str = ""
    original_variance_score: float = 1.0
    optimized_variance_score: float = 1.0
    audit_reason: str = ""
    writer_attempts: int = 0
    best_text: str = ""
    best_r_total: float = 0.0
    best_variance: float = 1.0
    best_per_dimension: dict[str, float] = field(default_factory=dict)
