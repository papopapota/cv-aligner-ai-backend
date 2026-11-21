from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobPostingContent:
    """Contenido estructurado extraído de una oferta de trabajo pública."""

    title: str | None
    company: str | None
    description: str
