from collections.abc import Callable
from unittest.mock import AsyncMock

import httpx
import pytest

from src.domain.errors import InvalidJobUrlError, JobDescriptionFetchError
from src.infrastructure.adapters.out.job_description_source_adapter import (
    JobDescriptionSourceAdapter,
)
from src.infrastructure.config import JobFetchSettings

_URL = "https://example.com/jobs/1"
_REDIRECT_URL = "https://example.com/jobs/2"
_HTML_HEADERS = {"content-type": "text/html; charset=utf-8"}


async def _allow(_: str) -> None:
    return None


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetches_and_parses_a_job_posting() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == _URL
        return httpx.Response(
            200,
            text=(
                '<html><script type="application/ld+json">'
                '{"@type":"JobPosting","description":"<p>Buscamos Python.</p>"}'
                "</script></html>"
            ),
            headers=_HTML_HEADERS,
        )

    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=_allow)
        content = await adapter.fetch_content(_URL)

    assert content.title is None
    assert content.company is None
    assert content.description == "Buscamos Python."


async def test_follows_and_revalidates_redirects() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url) == _URL:
            return httpx.Response(302, headers={"location": "/jobs/2"})
        return httpx.Response(
            200,
            text="<html><main><p>Texto final.</p></main></html>",
            headers=_HTML_HEADERS,
        )

    resolver = AsyncMock(side_effect=[None, None])
    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=resolver)
        content = await adapter.fetch_content(_URL)

    assert seen == [_URL, _REDIRECT_URL]
    assert resolver.await_count == 2
    assert content.description == "Texto final."


async def test_rejects_a_redirect_to_a_private_address() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})

    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=_allow)
        with pytest.raises(InvalidJobUrlError):
            await adapter.fetch_content(_URL)


async def test_rejects_a_host_that_resolves_to_a_private_ip() -> None:
    async def reject(_: str) -> None:
        raise JobDescriptionFetchError("La URL apunta a una dirección no pública.")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("No se debe realizar la petición HTTP.")

    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=reject)
        with pytest.raises(JobDescriptionFetchError):
            await adapter.fetch_content(_URL)


async def test_rejects_an_oversized_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="x" * 100, headers=_HTML_HEADERS)

    settings = JobFetchSettings(max_bytes=10)
    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(
            settings, client=client, resolve_host=_allow
        )
        with pytest.raises(JobDescriptionFetchError):
            await adapter.fetch_content(_URL)


async def test_rejects_an_http_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=_allow)
        with pytest.raises(JobDescriptionFetchError):
            await adapter.fetch_content(_URL)


async def test_rejects_an_unsupported_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"%PDF-1.4",
            headers={"content-type": "application/pdf"},
        )

    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=_allow)
        with pytest.raises(JobDescriptionFetchError):
            await adapter.fetch_content(_URL)


async def test_accepts_plain_text_responses() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="Buscamos desarrollador backend.",
            headers={"content-type": "text/plain; charset=utf-8"},
        )

    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=_allow)
        content = await adapter.fetch_content(_URL)

    assert content.title is None
    assert content.company is None
    assert content.description == "Buscamos desarrollador backend."


async def test_fetches_title_and_company_from_the_html() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                '<html><body><h1 class="top-card-layout__title topcard__title">'
                "Frontend Engineer</h1>"
                '<a class="topcard__org-name-link">Nexa Labs</a>'
                "<main><p>Buscamos React.</p></main></body></html>"
            ),
            headers=_HTML_HEADERS,
        )

    async with _client(handler) as client:
        adapter = JobDescriptionSourceAdapter(client=client, resolve_host=_allow)
        content = await adapter.fetch_content(_URL)

    assert content.title == "Frontend Engineer"
    assert content.company == "Nexa Labs"
    assert content.description == "Buscamos React."
