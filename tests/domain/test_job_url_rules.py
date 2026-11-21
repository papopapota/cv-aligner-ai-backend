import pytest

from src.domain.errors import InvalidJobUrlError
from src.domain.job_url_rules import MAX_JOB_URL_LENGTH, ensure_public_ip, ensure_safe_job_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/ofertas/123",
        "http://jobs.example.org/job?id=42",
    ],
)
def test_accepts_public_http_urls(url: str) -> None:
    assert ensure_safe_job_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "ftp://example.com/job",
        "example.com/job",
        "https://user:secret@example.com/job",
        "http://localhost:8000/job",
        "http://jobs.local/job",
        "http://127.0.0.1/job",
        "http://10.0.0.5/job",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/job",
        "https://example.com:" + "8" * 6,
        "https://example.com/" + "a" * MAX_JOB_URL_LENGTH,
    ],
)
def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(InvalidJobUrlError):
        ensure_safe_job_url(url)


def test_rejects_private_ip_without_dns() -> None:
    with pytest.raises(InvalidJobUrlError):
        ensure_public_ip("192.168.1.10")


def test_accepts_public_ip() -> None:
    ensure_public_ip("8.8.8.8")
