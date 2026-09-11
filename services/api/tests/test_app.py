import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.main import app
from app.settings import get_settings


def setup_module() -> None:
    get_settings.cache_clear()


def test_health_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"x-request-id": "health-test"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "health-test"


def test_me_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_accepts_explicit_local_test_token(monkeypatch) -> None:
    monkeypatch.setenv("ACT_API_ALLOW_TEST_USER", "true")
    get_settings.cache_clear()

    with TestClient(app) as client:
        response = client.get("/v1/me", headers={"authorization": "Bearer prototype-test-token"})

    assert response.status_code == 200
    assert response.json() == {"id": "test-user", "role": "student"}
    get_settings.cache_clear()


def test_content_preview_requires_reviewer_access() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/internal/imports/preview", json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_content_preview_returns_safe_import_summary() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="reviewer-test", role="reviewer"
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/internal/imports/preview",
                json={"subject": "english"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()[0]
    assert body["subject"] == "english"
    assert body["row_counts"]["skills"] == 39
    assert body["row_counts"]["questions"] == 300
    assert body["ready_for_assignment"] is False
    assert {warning["code"] for warning in body["warnings"]} >= {
        "primary_skill_mapping_required",
        "rights_status_requires_review",
    }
    assert "correctOption" not in str(body)
    assert "optionA" not in str(body)


def test_content_import_requires_a_configured_database() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="reviewer-test", role="reviewer"
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/internal/imports",
                json={"subject": "english"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_student_assessment_endpoints_require_a_configured_database() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("ACT_API_ALLOW_TEST_USER", "true")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/v1/diagnostics",
                headers={"authorization": "Bearer prototype-test-token"},
            )
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_submit_requires_a_configured_database() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("ACT_API_ALLOW_TEST_USER", "true")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/assessment-sessions/not-a-session/submit",
                headers={
                    "authorization": "Bearer prototype-test-token",
                    "Idempotency-Key": "submit-test",
                },
            )
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_remediation_endpoints_require_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/remediation-cycles/not-a-cycle")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_remediation_cycle_requires_a_configured_database() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("ACT_API_ALLOW_TEST_USER", "true")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/remediation-cycles",
                headers={"authorization": "Bearer prototype-test-token"},
                json={"skill_id": "00000000-0000-0000-0000-000000000001"},
            )
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_issue_reports_require_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/issue-reports",
            json={
                "entity_type": "diagnosis",
                "entity_id": "00000000-0000-0000-0000-000000000001",
                "category": "diagnosis",
                "description": "This did not look relevant.",
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_issue_reports_require_a_configured_database() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("ACT_API_ALLOW_TEST_USER", "true")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/issue-reports",
                headers={"authorization": "Bearer prototype-test-token"},
                json={
                    "entity_type": "diagnosis",
                    "entity_id": "00000000-0000-0000-0000-000000000001",
                    "category": "diagnosis",
                    "description": "This did not look relevant.",
                },
            )
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_pilot_export_requires_reviewer_access() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/internal/experiments/pilot-2026/export")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_pilot_export_requires_a_configured_database() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="reviewer-test", role="reviewer"
    )
    try:
        with TestClient(app) as client:
            response = client.get("/v1/internal/experiments/pilot-2026/export")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_experiment_assignment_requires_reviewer_access() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/internal/experiments/pilot-2026/assignments",
            json={
                "student_id": "00000000-0000-0000-0000-000000000001",
                "variant": "control",
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_tutor_assessment_requires_a_configured_database() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="reviewer-test", role="reviewer"
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/internal/tutor-assessments",
                json={
                    "student_id": "00000000-0000-0000-0000-000000000001",
                    "subject": "english",
                    "skill_id": "00000000-0000-0000-0000-000000000002",
                    "rating": 3,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_issue_queue_requires_reviewer_access() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/internal/issues")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_issue_queue_requires_a_configured_database() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="reviewer-test", role="reviewer"
    )
    try:
        with TestClient(app) as client:
            response = client.get("/v1/internal/issues?status=open")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"


def test_content_review_requires_reviewer_access() -> None:
    blueprint_id = "00000000-0000-0000-0000-000000000001"
    with TestClient(app) as client:
        response = client.post(
            f"/v1/internal/content/{blueprint_id}/reviews",
            json={
                "blueprint_id": blueprint_id,
                "content_source_ids": ["00000000-0000-0000-0000-000000000002"],
                "decision": "publish",
                "confirm_review": True,
                "confirm_content_review": True,
                "confirm_rights_clearance": True,
                "confirm_answer_key_review": True,
                "notes": "Reviewed slice.",
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_content_review_requires_a_configured_database() -> None:
    blueprint_id = "00000000-0000-0000-0000-000000000001"
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="reviewer-test", role="reviewer"
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/v1/internal/content/{blueprint_id}/reviews",
                json={
                    "blueprint_id": blueprint_id,
                    "content_source_ids": ["00000000-0000-0000-0000-000000000002"],
                    "decision": "reject",
                    "confirm_review": True,
                    "confirm_content_review": True,
                    "confirm_rights_clearance": False,
                    "confirm_answer_key_review": False,
                    "notes": "The slice needs more review.",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "request_failed"
