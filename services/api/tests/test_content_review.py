from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.content_review import (
    ContentReviewCounts,
    ContentReviewRequest,
    ContentReviewResult,
)


def _request(**overrides: object) -> ContentReviewRequest:
    values: dict[str, object] = {
        "blueprint_id": uuid4(),
        "content_source_ids": [uuid4()],
        "decision": "publish",
        "confirm_review": True,
        "confirm_content_review": True,
        "confirm_rights_clearance": True,
        "confirm_answer_key_review": True,
        "notes": "Reviewed for the narrow English pilot slice.",
    }
    values.update(overrides)
    return ContentReviewRequest(**values)


def test_publish_request_requires_all_explicit_confirmation_flags() -> None:
    with pytest.raises(ValidationError, match="confirm_rights_clearance"):
        _request(confirm_rights_clearance=False)

    request = _request()
    assert request.decision == "publish"
    assert request.confirm_answer_key_review is True


def test_reject_request_requires_review_confirmation_but_not_publish_gates() -> None:
    request = _request(
        decision="reject",
        confirm_rights_clearance=False,
        confirm_answer_key_review=False,
        notes="The slice contains an unresolved provenance concern.",
    )

    assert request.decision == "reject"
    assert request.confirm_review is True

    with pytest.raises(ValidationError, match="confirm_content_review"):
        _request(
            decision="reject",
            confirm_content_review=False,
            confirm_rights_clearance=False,
            confirm_answer_key_review=False,
        )


def test_request_is_strict_about_extra_fields_and_boolean_types() -> None:
    with pytest.raises(ValidationError):
        _request(unexpected="not allowed")
    with pytest.raises(ValidationError):
        _request(confirm_review="true")


def test_request_rejects_duplicate_sources_and_blank_notes() -> None:
    source_id = uuid4()
    with pytest.raises(ValidationError, match="duplicates"):
        _request(content_source_ids=[source_id, source_id])
    with pytest.raises(ValidationError, match="blank"):
        _request(notes="   ")


def test_result_contains_only_safe_review_metadata() -> None:
    result = ContentReviewResult(
        blueprint_id=uuid4(),
        subject="english",
        purpose="diagnostic",
        version="taxonomy-v1-diagnostic-v1",
        decision="publish",
        lifecycle_status="approved",
        counts=ContentReviewCounts(sources=1, tests=1, sections=1, passages=1, questions=8),
        reviewer_id=uuid4(),
        reviewed_at=datetime.now(timezone.utc),
    )

    serialized = result.model_dump_json()
    assert result.counts.questions == 8
    assert "answer_key" not in serialized
    assert "correct_choice" not in serialized
    assert "is_correct" not in serialized
    assert "optionA" not in serialized


def test_result_rejects_unsupported_subject_and_negative_counts() -> None:
    with pytest.raises(ValidationError):
        ContentReviewResult(
            blueprint_id=uuid4(),
            subject="science",
            purpose="diagnostic",
            version="v1",
            decision="reject",
            lifecycle_status="retired",
            counts=ContentReviewCounts(sources=1, tests=1, sections=1, passages=1, questions=1),
            reviewer_id=uuid4(),
            reviewed_at=datetime.now(timezone.utc),
        )

    with pytest.raises(ValidationError):
        ContentReviewCounts(sources=-1, tests=0, sections=0, passages=0, questions=0)
    with pytest.raises(ValidationError):
        ContentReviewCounts(sources="1", tests=0, sections=0, passages=0, questions=0)
