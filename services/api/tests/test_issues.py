from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.issues import IssueConflict, IssueReport, IssueReportRequest, IssueResolutionRequest


def test_issue_report_request_strips_text_and_rejects_extra_fields() -> None:
    report = IssueReportRequest(
        entity_type="resource",
        entity_id=uuid4(),
        category="  broken_link ",
        description="  The resource does not open. ",
    )

    assert report.category == "broken_link"
    assert report.description == "The resource does not open."
    with pytest.raises(ValidationError):
        IssueReportRequest(
            entity_type="resource",
            entity_id=uuid4(),
            category="link",
            description="problem",
            unexpected="nope",
        )


def test_issue_report_request_rejects_blank_or_unknown_values() -> None:
    with pytest.raises(ValidationError):
        IssueReportRequest(
            entity_type="not-a-supported-entity",
            entity_id=uuid4(),
            category="link",
            description="problem",
        )
    with pytest.raises(ValidationError):
        IssueReportRequest(
            entity_type="question",
            entity_id=uuid4(),
            category=" ",
            description="problem",
        )


def test_issue_response_excludes_reporter_identity_and_resolution_fields() -> None:
    report = IssueReport(
        id=str(uuid4()),
        entity_type="diagnosis",
        entity_id=str(uuid4()),
        category="diagnosis",
        description="This target did not feel relevant.",
        status="open",
        created_at=datetime.now(timezone.utc),
    )

    serialized = report.model_dump_json()
    assert "reporter_id" not in serialized
    assert "resolution" not in serialized


def test_issue_resolution_requires_a_non_blank_safe_decision() -> None:
    resolution = IssueResolutionRequest(status="resolved", resolution="  Link fixed. ")

    assert resolution.resolution == "Link fixed."
    with pytest.raises(ValidationError):
        IssueResolutionRequest(status="open", resolution="not a terminal decision")
    with pytest.raises(ValidationError):
        IssueResolutionRequest(status="dismissed", resolution=" ")


def test_issue_idempotency_key_rejects_blank_or_oversized_values() -> None:
    payload = IssueReportRequest(
        entity_type="question",
        entity_id=uuid4(),
        category="question",
        description="The question is confusing.",
    )

    with pytest.raises(IssueConflict):
        from app.issues import create_issue_report

        create_issue_report(None, str(uuid4()), payload, " ")
    with pytest.raises(IssueConflict):
        from app.issues import create_issue_report

        create_issue_report(None, str(uuid4()), payload, "x" * 256)
