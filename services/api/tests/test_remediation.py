from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.assessments import (
    AssessmentItem,
    AssessmentSession,
    PublicChoice,
    _remediation_status_for_classification,
)
from app.remediation import (
    LearningResource,
    PracticeSet,
    PracticeSetCreateRequest,
    RemediationCycleCreateRequest,
    RemediationUnavailable,
    ResourceEventRequest,
    _student_uuid,
)


def _public_session() -> AssessmentSession:
    question_id = str(uuid4())
    item = AssessmentItem(
        id=str(uuid4()),
        question_id=question_id,
        position=1,
        prompt="Which sentence is clearest?",
        context=None,
        choices=[
            PublicChoice(id="A", text="The first choice."),
            PublicChoice(id="B", text="The second choice."),
        ],
    )
    return AssessmentSession(
        id=str(uuid4()),
        subject="english",
        purpose="practice",
        status="in_progress",
        items=[item],
    )


def test_cycle_request_requires_a_skill_or_recommendation() -> None:
    with pytest.raises(ValidationError):
        RemediationCycleCreateRequest()

    skill_id = uuid4()
    request = RemediationCycleCreateRequest(skill_id=skill_id)
    assert request.skill_id == skill_id


def test_practice_request_has_small_bounded_defaults() -> None:
    request = PracticeSetCreateRequest()

    assert request.target_count == 5
    assert request.assembly_version == "practice-v1"

    with pytest.raises(ValidationError):
        PracticeSetCreateRequest(target_count=0)
    with pytest.raises(ValidationError):
        PracticeSetCreateRequest(target_count=51)


def test_resource_event_type_is_trimmed_and_blank_values_are_rejected() -> None:
    request = ResourceEventRequest(resource_id=uuid4(), event_type=" resource_opened ")

    assert request.event_type == "resource_opened"
    with pytest.raises(ValidationError):
        ResourceEventRequest(resource_id=uuid4(), event_type="   ")


def test_practice_set_reuses_public_assessment_shapes_without_answer_keys() -> None:
    session = _public_session()
    practice_set = PracticeSet(
        id=str(uuid4()),
        cycle_id=str(uuid4()),
        assessment_session_id=session.id,
        status="in_progress",
        target_count=1,
        assembly_version="practice-v1",
        created_at=datetime.now(timezone.utc),
        assessment_session=session,
    )
    serialized = practice_set.model_dump_json()

    assert isinstance(practice_set.assessment_session, AssessmentSession)
    assert isinstance(practice_set.assessment_session.items[0], AssessmentItem)
    assert "is_correct" not in serialized
    assert "answer_key" not in serialized
    assert "correct_answer" not in serialized


def test_learning_resource_is_public_metadata_only() -> None:
    resource = LearningResource(
        id=str(uuid4()),
        provider="Khan Academy",
        title="Punctuation",
        url="https://example.com/punctuation",
        resource_type="lesson",
    )

    assert resource.focus_note is None
    assert "answer" not in resource.model_dump_json()


def test_invalid_authenticated_identity_is_unavailable() -> None:
    with pytest.raises(RemediationUnavailable):
        _student_uuid("not-a-uuid")


@pytest.mark.parametrize(
    ("classification", "expected"),
    [
        ("strong_evidence_of_mastery", "mastered"),
        ("likely_mastered", "mastered"),
        ("insufficient_evidence", "needs_more_evidence"),
        ("developing", "repeat_recommended"),
    ],
)
def test_reassessment_classification_maps_to_cycle_outcome(classification: str, expected: str) -> None:
    assert _remediation_status_for_classification(classification) == expected
