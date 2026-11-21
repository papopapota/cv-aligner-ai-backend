from __future__ import annotations

import asyncio
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin, urlsplit

import httpx

from src.application.ports.out.job_description_source_port import JobDescriptionSourcePort
from src.domain import job_url_rules
from src.domain.errors import InvalidJobUrlError, JobDescriptionFetchError
from src.domain.job_posting_content import JobPostingContent
from src.infrastructure.adapters.out import job_description_html_parser
from src.infrastructure.config import JobFetchSettings

HostResolver = Callable[[str], Awaitable[None]]

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", ""})
_TEXT_CONTENT_TYPES = frozenset({"text/plain", "application/json"})
_HEADERS = {
    "User-Agent": "cv-aligner-ai/0.1 (+job-description-extractor)",
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
}


class JobDescriptionSourceAdapter(JobDescriptionSourcePort):
    def __init__(
        self,
        settings: JobFetchSettings | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        resolve_host: HostResolver | None = None,
    ) -> None:
        self._settings = settings or JobFetchSettings()
        self._client = client
        self._resolve_host = resolve_host or _resolve_public_host

    async def fetch_content(self, url: str) -> JobPostingContent:
        safe_url = job_url_rules.ensure_safe_job_url(url)
        if self._client is not None:
            return await self._fetch_with(self._client, safe_url)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._settings.timeout_seconds),
            headers=_HEADERS,
        ) as client:
            return await self._fetch_with(client, safe_url)

    async def _fetch_with(
        self, client: httpx.AsyncClient, url: str
    ) -> JobPostingContent:
        current = url
        for _ in range(self._settings.max_redirects + 1):
            await self._resolve_host(current)
            try:
                async with client.stream(
                    "GET", current, headers=_HEADERS, follow_redirects=False
                ) as response:
                    if response.status_code in _REDIRECT_STATUSES:
                        location = response.headers.get("location")
                        if not location:
                            raise JobDescriptionFetchError(
                                "La URL redirigió sin indicar un destino."
                            )
                        current = job_url_rules.ensure_safe_job_url(
                            urljoin(current, location)
                        )
                        continue
                    if response.status_code != 200:
                        raise JobDescriptionFetchError(
                            f"La URL devolvió HTTP {response.status_code}."
                        )
                    content_type = (
                        response.headers.get("content-type", "")
                        .split(";")[0]
                        .strip()
                        .lower()
                    )
                    encoding = response.encoding or "utf-8"
                    body = await self._read_body(response)
            except httpx.HTTPError as exc:
                raise JobDescriptionFetchError(
                    "No se pudo descargar la descripción de la oferta."
                ) from exc

            return self._to_content(body, content_type, encoding)

        raise JobDescriptionFetchError("La URL redirigió demasiadas veces.")

    async def _read_body(self, response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > self._settings.max_bytes:
                raise JobDescriptionFetchError("La página de la oferta es demasiado grande.")
            chunks.append(chunk)
        return b"".join(chunks)

    def _to_content(
        self, body: bytes, content_type: str, encoding: str
    ) -> JobPostingContent:
        text = body.decode(encoding, errors="replace")
        if content_type in _HTML_CONTENT_TYPES:
            return job_description_html_parser.extract_job_posting(
                text, self._settings.max_description_chars
            )
        if content_type in _TEXT_CONTENT_TYPES:
            return JobPostingContent(
                title=None,
                company=None,
                description=job_description_html_parser.normalize_text(
                    text, self._settings.max_description_chars
                ),
            )
        raise JobDescriptionFetchError("El contenido de la URL no es texto ni HTML.")


async def _resolve_public_host(url: str) -> None:
    hostname = urlsplit(url).hostname or ""
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except (socket.gaierror, UnicodeError) as exc:
        raise JobDescriptionFetchError(
            "No se pudo resolver el dominio de la URL."
        ) from exc
    for address in addresses:
        try:
            job_url_rules.ensure_public_ip(str(address[4][0]))
        except InvalidJobUrlError as exc:
            raise JobDescriptionFetchError(
                "La URL apunta a una dirección no pública."
            ) from exc
