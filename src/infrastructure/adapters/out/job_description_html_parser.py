from __future__ import annotations

import html
import json
import re
from collections.abc import Iterator
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from src.domain.job_posting_content import JobPostingContent

_JSONLD_CONTENT_TYPE = "application/ld+json"
_SKIP_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
    "svg",
    "button",
    "template",
)
_BLOCK_TAGS = (
    "p",
    "div",
    "section",
    "article",
    "li",
    "ul",
    "ol",
    "tr",
    "table",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
)
_CONTENT_SELECTORS = (
    "main",
    "article",
    "[role=main]",
    "#job-description",
    ".job-description",
)
_TITLE_SELECTORS = (
    "h1.top-card-layout__title",
    ".topcard__title",
    '[class~="top-card-layout__title"]',
)
_COMPANY_SELECTORS = (
    "a.topcard__org-name-link",
    ".topcard__org-name-link",
    ".topcard__flavor",
)
_GENERIC_H1_SELECTORS = ("main h1", "article h1", "[role=main] h1", "h1")
_SEPARATORS = frozenset({"·", "•", "|", "-", "–", "—", "/"})
_BLANK_LINES = re.compile(r"\n{3,}")
_EXTRA_SPACES = re.compile(r"[ \t]+")
_RESIDUAL_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^>]*)?/?>")
_RESIDUAL_ENTITY = re.compile(r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);")
_MAX_ENTITY_PASSES = 5

JsonLdNode = dict[str, Any]


def extract_job_posting(html: str, max_chars: int) -> JobPostingContent:
    """Extrae título, empresa y descripción de una oferta pública."""
    soup = BeautifulSoup(html, "html.parser")
    nodes = list(_job_posting_nodes(soup))

    title = (
        _first_text(soup, _TITLE_SELECTORS)
        or _jsonld_title(nodes)
        or _first_text(soup, _GENERIC_H1_SELECTORS)
    )
    company = _first_text(soup, _COMPANY_SELECTORS) or _jsonld_company(nodes)

    return JobPostingContent(
        title=title,
        company=company,
        description=_description_from(soup, nodes, max_chars),
    )


def extract_description(html: str, max_chars: int) -> str:
    """Extrae únicamente la descripción (wrapper de ``extract_job_posting``)."""
    return extract_job_posting(html, max_chars).description


def normalize_text(text: str, max_chars: int) -> str:
    """Normaliza espacios y saltos de línea, y aplica el tope de caracteres."""
    lines = [
        _EXTRA_SPACES.sub(" ", line.strip())
        for line in text.replace("\r\n", "\n").split("\n")
    ]
    cleaned = _BLANK_LINES.sub("\n\n", "\n".join(line for line in lines if line))
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[:max_chars]
    return (truncated.rsplit("\n", 1)[0] or truncated).rstrip()


def _description_from(
    soup: BeautifulSoup, nodes: list[JsonLdNode], max_chars: int
) -> str:
    structured = _jsonld_description(nodes)
    fragment = structured if structured is not None else str(_main_content(soup))
    return normalize_text(_strip_residual_markup(_visible_text(fragment)), max_chars)


def _decode_entities(text: str) -> str:
    """Decodifica entidades HTML aunque estén escapadas varias veces."""
    decoded = text
    for _ in range(_MAX_ENTITY_PASSES):
        previous = decoded
        decoded = html.unescape(decoded)
        if decoded == previous:
            break
    return decoded


def _strip_residual_markup(text: str) -> str:
    """Elimina etiquetas o entidades que hayan sobrevivido al parseo."""
    text = text.replace("\xa0", " ")
    text = _RESIDUAL_TAG.sub("", text)
    return _RESIDUAL_ENTITY.sub("", text)


def _first_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        for tag in soup.select(selector):
            text = _clean_text(tag.get_text(" ", strip=True))
            if text and text not in _SEPARATORS:
                return text
    return None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _jsonld_description(nodes: list[JsonLdNode]) -> str | None:
    for node in nodes:
        description = _clean_text(node.get("description"))
        if description:
            return description
    return None


def _jsonld_title(nodes: list[JsonLdNode]) -> str | None:
    for node in nodes:
        title = _clean_text(node.get("title"))
        if title:
            return title
    return None


def _jsonld_company(nodes: list[JsonLdNode]) -> str | None:
    for node in nodes:
        organization = node.get("hiringOrganization")
        if isinstance(organization, dict):
            company = _clean_text(organization.get("name"))
        else:
            company = _clean_text(organization)
        if company:
            return company
    return None


def _job_posting_nodes(soup: BeautifulSoup) -> Iterator[JsonLdNode]:
    for script in soup.find_all("script", attrs={"type": _JSONLD_CONTENT_TYPE}):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            payload: Any = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _iter_nodes(payload):
            if isinstance(node, dict) and _is_job_posting(node.get("@type")):
                yield node


def _iter_nodes(value: Any) -> Iterator[Any]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nodes(child)


def _is_job_posting(node_type: Any) -> bool:
    if isinstance(node_type, str):
        return node_type.lower() == "jobposting"
    if isinstance(node_type, list):
        return any(
            isinstance(item, str) and item.lower() == "jobposting" for item in node_type
        )
    return False


def _main_content(soup: BeautifulSoup) -> Tag:
    for selector in _CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if node is not None:
            return node
    return soup.body or soup


def _visible_text(fragment: str) -> str:
    soup = BeautifulSoup(_decode_entities(fragment), "html.parser")
    for tag in soup.find_all(_SKIP_TAGS):
        tag.decompose()
    for tag in soup.find_all("br"):
        tag.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.append("\n")
    return soup.get_text("")
