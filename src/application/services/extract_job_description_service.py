from src.application.ports.inbound.extract_job_description_use_case import (
    ExtractJobDescriptionUseCase,
)
from src.application.ports.out.job_description_source_port import JobDescriptionSourcePort
from src.domain import job_url_rules, upload_rules
from src.domain.job_posting_content import JobPostingContent


class ExtractJobDescriptionService(ExtractJobDescriptionUseCase):
    def __init__(self, source: JobDescriptionSourcePort) -> None:
        self._source = source

    async def execute(self, url: str) -> JobPostingContent:
        safe_url = job_url_rules.ensure_safe_job_url(url)
        content = await self._source.fetch_content(safe_url)
        upload_rules.ensure_non_empty_text(content.description)
        return JobPostingContent(
            title=_optional_text(content.title),
            company=_optional_text(content.company),
            description=content.description.strip(),
        )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
