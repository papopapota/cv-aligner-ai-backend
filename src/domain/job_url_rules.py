from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from src.domain.errors import InvalidJobUrlError

MAX_JOB_URL_LENGTH = 2048
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal")


def ensure_public_ip(address: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    """Rechaza direcciones IP que no sean públicamente enrutables."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError as exc:
        raise InvalidJobUrlError("La URL contiene una dirección IP inválida.") from exc
    if not ip.is_global:
        raise InvalidJobUrlError("La URL apunta a una dirección IP no pública.")


def ensure_safe_job_url(url: str) -> str:
    """Valida la URL de una oferta antes de hacer cualquier petición HTTP."""
    candidate = url.strip()
    if not candidate:
        raise InvalidJobUrlError("La URL de la oferta está vacía.")
    if len(candidate) > MAX_JOB_URL_LENGTH:
        raise InvalidJobUrlError("La URL de la oferta es demasiado larga.")

    try:
        parts = urlsplit(candidate)
        scheme = parts.scheme.lower()
        hostname = parts.hostname
        _ = parts.port
    except ValueError as exc:
        raise InvalidJobUrlError("La URL de la oferta no es válida.") from exc

    if scheme not in _ALLOWED_SCHEMES:
        raise InvalidJobUrlError("Solo se permiten URLs http o https.")
    if parts.username is not None or parts.password is not None:
        raise InvalidJobUrlError("La URL de la oferta no puede incluir credenciales.")
    if hostname is None:
        raise InvalidJobUrlError("La URL de la oferta no incluye un dominio.")

    normalized_host = hostname.lower().rstrip(".")
    if normalized_host in _BLOCKED_HOSTNAMES or normalized_host.endswith(_BLOCKED_SUFFIXES):
        raise InvalidJobUrlError("La URL de la oferta apunta a un dominio interno.")

    try:
        ipaddress.ip_address(normalized_host)
    except ValueError:
        pass
    else:
        ensure_public_ip(normalized_host)

    return candidate
