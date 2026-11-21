import dataclasses

import pytest

from src.domain.job_posting_content import JobPostingContent


def test_create_job_posting_content() -> None:
    content = JobPostingContent(
        title="Backend Engineer",
        company="Acme Corp",
        description="Buscamos Python y FastAPI.",
    )

    assert content.title == "Backend Engineer"
    assert content.company == "Acme Corp"
    assert content.description == "Buscamos Python y FastAPI."


def test_allows_missing_metadata() -> None:
    content = JobPostingContent(title=None, company=None, description="Una oferta.")

    assert content.title is None
    assert content.company is None


def test_is_immutable() -> None:
    content = JobPostingContent(title=None, company=None, description="Una oferta.")

    with pytest.raises(dataclasses.FrozenInstanceError):
        content.description = "Otra oferta."  # type: ignore[misc]
