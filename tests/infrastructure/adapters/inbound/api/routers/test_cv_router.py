from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.ports.inbound.cv_optimization_use_case import (
    CVOptimizationUseCase,
)
from src.application.ports.inbound.cv_query_use_case import CVQueryUseCase
from src.application.ports.inbound.cv_upload_use_case import (
    CVUploadUseCase,
    FileUpload,
)
from src.application.ports.out.user_port import UserRepositoryPort
from src.domain.cv_status import CVStatus
from src.domain.entities.cv import CV
from src.domain.entities.user import User
from src.domain.errors import CVFailedError, CVNotFoundError, CVNotReadyError
from src.domain.optimized_cv import OptimizedCV
from src.domain.personal_info import Location, PersonalInfo, ProfessionalLinks
from src.infrastructure.adapters.inbound.api.routers.auth_router import (
    get_user_repository,
)
from src.infrastructure.adapters.inbound.api.routers.cv_router import (
    get_cv_optimization_use_case,
    get_cv_processing_task,
    get_cv_query_use_case,
    get_cv_upload_use_case,
)
from src.infrastructure.security import create_access_token
from src.main import app

_USER_ID = 7
_JOB_DESCRIPTION = "We are looking for a Python backend engineer."


def _user() -> User:
    return User(
        id=_USER_ID,
        name="Juan Perez",
        email="juan@example.com",
        password="hashed-password",
        created_at=datetime.now(timezone.utc),
    )


def _cv(**overrides: object) -> CV:
    values: dict[str, object] = {
        "id": uuid4(),
        "user_id": _USER_ID,
        "s3_key": "users/7/cvs/cv.pdf",
        "filename": "cv.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "status": CVStatus.UPLOADED,
    }
    values.update(overrides)
    return CV(**values)  # type: ignore[arg-type]


def _optimized() -> OptimizedCV:
    return OptimizedCV(
        content="Optimized backend engineer body.",
        original_variance_score=0.8,
        optimized_variance_score=0.1,
        writer_attempts=1,
        personal_info=PersonalInfo(
            full_name="Ana Developer",
            headline="Backend Developer",
            email="ana@example.com",
            location=Location(city="Lima", country="Peru"),
            links=ProfessionalLinks(github="github.com/ana"),
        ),
    )


def _auth_headers() -> dict[str, str]:
    token = create_access_token(subject="juan@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_repository() -> AsyncMock:
    repository = AsyncMock(spec=UserRepositoryPort)
    repository.get_by_email.return_value = _user()
    return repository


@pytest.fixture
def query_use_case() -> AsyncMock:
    return AsyncMock(spec=CVQueryUseCase)


@pytest.fixture
def upload_use_case() -> AsyncMock:
    return AsyncMock(spec=CVUploadUseCase)


@pytest.fixture
def optimization_use_case() -> AsyncMock:
    return AsyncMock(spec=CVOptimizationUseCase)


@pytest.fixture
def processing_task() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def client(
    user_repository: AsyncMock,
    query_use_case: AsyncMock,
    upload_use_case: AsyncMock,
    optimization_use_case: AsyncMock,
    processing_task: AsyncMock,
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_user_repository] = lambda: user_repository
    app.dependency_overrides[get_cv_query_use_case] = lambda: query_use_case
    app.dependency_overrides[get_cv_upload_use_case] = lambda: upload_use_case
    app.dependency_overrides[get_cv_optimization_use_case] = lambda: (
        optimization_use_case
    )
    app.dependency_overrides[get_cv_processing_task] = lambda: processing_task
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def test_upload_requires_authentication(
    client: AsyncClient,
    upload_use_case: AsyncMock,
) -> None:
    response = await client.post(
        "/api/v1/cvs",
        files={"cv_file": ("cv.pdf", b"%PDF-1.7 fake", "application/pdf")},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    upload_use_case.execute.assert_not_awaited()


async def test_upload_returns_202_and_schedules_processing(
    client: AsyncClient,
    upload_use_case: AsyncMock,
    processing_task: AsyncMock,
) -> None:
    cv = _cv()
    upload_use_case.execute.return_value = cv

    response = await client.post(
        "/api/v1/cvs",
        headers=_auth_headers(),
        files={"cv_file": ("cv.pdf", b"%PDF-1.7 fake", "application/pdf")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == str(cv.id)
    assert body["filename"] == "cv.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == 1024
    assert body["sha256"] == "a" * 64
    assert body["status"] == "UPLOADED"
    assert body["action_required"] == "WAIT_FOR_PARSING"

    upload, user_id = upload_use_case.execute.await_args.args
    assert isinstance(upload, FileUpload)
    assert upload.filename == "cv.pdf"
    assert upload.content_type == "application/pdf"
    assert upload.content == b"%PDF-1.7 fake"
    assert user_id == _USER_ID
    processing_task.assert_awaited_once_with(cv.id)


async def test_get_returns_the_cv_status(
    client: AsyncClient,
    query_use_case: AsyncMock,
) -> None:
    cv = _cv(status=CVStatus.PARSED)
    query_use_case.get.return_value = cv

    response = await client.get(
        f"/api/v1/cvs/{cv.id}",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(cv.id)
    assert body["status"] == "PARSED"
    assert body["action_required"] is None
    assert body["error_code"] is None
    assert body["error_message"] is None
    query_use_case.get.assert_awaited_once_with(cv.id, _USER_ID)


async def test_get_exposes_the_stored_failure(
    client: AsyncClient,
    query_use_case: AsyncMock,
) -> None:
    cv = _cv(
        status=CVStatus.ERROR,
        error_code="PARSE_FAILED",
        error_message="The CV could not be processed.",
    )
    query_use_case.get.return_value = cv

    response = await client.get(
        f"/api/v1/cvs/{cv.id}",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ERROR"
    assert body["error_code"] == "PARSE_FAILED"
    assert body["error_message"] == "The CV could not be processed."
    assert body["action_required"] == "REUPLOAD_CV"


async def test_get_returns_404_for_an_unknown_cv(
    client: AsyncClient,
    query_use_case: AsyncMock,
) -> None:
    query_use_case.get.side_effect = CVNotFoundError("The CV does not exist.")

    response = await client.get(
        f"/api/v1/cvs/{uuid4()}",
        headers=_auth_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "The CV does not exist."}


async def test_list_returns_the_users_cvs(
    client: AsyncClient,
    query_use_case: AsyncMock,
) -> None:
    cvs = [_cv(), _cv(status=CVStatus.PARSED)]
    query_use_case.list.return_value = cvs

    response = await client.get("/api/v1/cvs", headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(cv.id) for cv in cvs]
    assert body[0]["action_required"] == "WAIT_FOR_PARSING"
    assert body[1]["action_required"] is None
    query_use_case.list.assert_awaited_once_with(_USER_ID)


async def test_optimize_returns_the_optimized_cv(
    client: AsyncClient,
    optimization_use_case: AsyncMock,
) -> None:
    cv_id = uuid4()
    optimization_use_case.execute.return_value = _optimized()

    response = await client.post(
        f"/api/v1/cvs/{cv_id}/optimize",
        headers=_auth_headers(),
        json={"job_description": _JOB_DESCRIPTION},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["optimized_content"].startswith("Ana Developer")
    assert body["optimized_body"] == "Optimized backend engineer body."
    assert body["original_variance_score"] == 0.8
    assert body["optimized_variance_score"] == 0.1
    assert body["writer_attempts"] == 1
    assert body["is_within_threshold"] is True
    assert body["personal_info"]["full_name"] == "Ana Developer"
    assert body["personal_info"]["location"] == {
        "city": "Lima",
        "country": "Peru",
    }
    optimization_use_case.execute.assert_awaited_once_with(
        cv_id,
        _USER_ID,
        _JOB_DESCRIPTION,
    )


async def test_optimize_accepts_the_legacy_job_description_alias(
    client: AsyncClient,
    optimization_use_case: AsyncMock,
) -> None:
    optimization_use_case.execute.return_value = _optimized()

    response = await client.post(
        f"/api/v1/cvs/{uuid4()}/optimize",
        headers=_auth_headers(),
        json={"job_description_text": _JOB_DESCRIPTION},
    )

    assert response.status_code == 200
    assert optimization_use_case.execute.await_args.args[2] == _JOB_DESCRIPTION


async def test_optimize_returns_409_when_the_cv_is_not_ready(
    client: AsyncClient,
    optimization_use_case: AsyncMock,
) -> None:
    optimization_use_case.execute.side_effect = CVNotReadyError(
        "The CV is not ready for optimization."
    )

    response = await client.post(
        f"/api/v1/cvs/{uuid4()}/optimize",
        headers=_auth_headers(),
        json={"job_description": _JOB_DESCRIPTION},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The CV is not ready for optimization.",
        "action_required": "WAIT_FOR_PARSING",
    }


async def test_optimize_returns_409_when_the_cv_failed(
    client: AsyncClient,
    optimization_use_case: AsyncMock,
) -> None:
    optimization_use_case.execute.side_effect = CVFailedError(
        "PARSE_FAILED",
        "The CV could not be processed.",
    )

    response = await client.post(
        f"/api/v1/cvs/{uuid4()}/optimize",
        headers=_auth_headers(),
        json={"job_description": _JOB_DESCRIPTION},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The CV could not be processed.",
        "error_code": "PARSE_FAILED",
        "action_required": "REUPLOAD_CV",
    }


async def test_optimize_returns_404_for_an_unknown_cv(
    client: AsyncClient,
    optimization_use_case: AsyncMock,
) -> None:
    optimization_use_case.execute.side_effect = CVNotFoundError(
        "The CV does not exist."
    )

    response = await client.post(
        f"/api/v1/cvs/{uuid4()}/optimize",
        headers=_auth_headers(),
        json={"job_description": _JOB_DESCRIPTION},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "The CV does not exist."}


async def test_optimize_rejects_an_empty_job_description(
    client: AsyncClient,
    optimization_use_case: AsyncMock,
) -> None:
    response = await client.post(
        f"/api/v1/cvs/{uuid4()}/optimize",
        headers=_auth_headers(),
        json={"job_description": ""},
    )

    assert response.status_code == 422
    optimization_use_case.execute.assert_not_awaited()
