import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.domain.errors import AuditFailedError
from src.infrastructure.adapters.inbound.api.audit_error_handler import (
    handle_audit_failure,
)
from src.main import app

_EXC = AuditFailedError("The optimized CV did not pass the variance audit.")


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_maps_an_audit_failure_to_422() -> None:
    probe_app = FastAPI()
    probe_app.add_exception_handler(AuditFailedError, handle_audit_failure)

    @probe_app.get("/probe")
    async def _raise() -> None:
        raise _EXC

    probe_client = AsyncClient(
        transport=ASGITransport(app=probe_app),
        base_url="http://test",
    )

    response = await probe_client.get("/probe")

    assert response.status_code == 422
    assert response.json()["detail"] == str(_EXC)


async def test_the_upload_handler_does_not_capture_an_audit_failure() -> None:
    from src.infrastructure.adapters.inbound.api.domain_error_handler import (
        handle_invalid_upload,
    )

    invalid_upload_handler = await handle_invalid_upload(None, _EXC)  # type: ignore[arg-type]

    assert invalid_upload_handler.status_code == 400


async def test_the_handler_returns_a_json_response_directly() -> None:
    response = await handle_audit_failure(None, _EXC)  # type: ignore[arg-type]

    assert response.status_code == 422
    assert b"variance audit" in response.body


async def test_an_invalid_upload_still_maps_to_400(client: AsyncClient) -> None:
    response = await client.post(
        "/cv/upload",
        files={
            "cv_file": ("cv.txt", b"plain", "text/plain"),
            "job_description_file": ("job.txt", b"spec", "text/plain"),
        },
    )

    assert response.status_code == 400


async def test_audit_failure_is_not_an_invalid_upload() -> None:
    from src.domain.errors import InvalidUploadError

    assert not issubclass(AuditFailedError, InvalidUploadError)
