from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.progress import (
    MasteryHistory,
    MasteryOverview,
    MasterySnapshotRecord,
    ProgressNotFound,
    ProgressUnavailable,
    RecommendationRecord,
    RemediationCycleSummary,
    _path_uuid,
    _student_uuid,
)


def _snapshot() -> MasterySnapshotRecord:
    return MasterySnapshotRecord(
        id=str(uuid4()),
        skill_id=str(uuid4()),
        skill_key="english.conventions.sentence-structure",
        skill_name="Sentence structure",
        mean=0.64,
        lower_bound=0.42,
        upper_bound=0.86,
        effective_evidence=2.0,
        correct_count=2,
        incorrect_count=1,
        omitted_count=0,
        classification="developing",
        reason="Based on 2 correct and 1 incorrect scored response.",
        model_version="beta-binomial-v1",
        calculated_at=datetime.now(timezone.utc),
    )


def _recommendation(snapshot: MasterySnapshotRecord) -> RecommendationRecord:
    return RecommendationRecord(
        id=str(uuid4()),
        skill_id=snapshot.skill_id,
        skill_key=snapshot.skill_key,
        skill_name=snapshot.skill_name,
        rank=1,
        priority_score=0.24,
        weakness_score=0.15,
        importance_score=1.0,
        confidence_score=0.5,
        readiness=True,
        explanation="Work on sentence structure with the approved learning path.",
        formula_version="priority-v1",
        status="current",
        created_at=datetime.now(timezone.utc),
    )


def test_mastery_overview_reuses_public_snapshot_and_recommendation_shapes() -> None:
    snapshot = _snapshot()
    overview = MasteryOverview(
        subject="english",
        snapshots=[snapshot],
        recommendations=[_recommendation(snapshot)],
    )

    assert overview.snapshots[0].skill_id == snapshot.skill_id
    assert overview.recommendations[0].formula_version == "priority-v1"
    serialized = overview.model_dump_json()
    assert "answer_key" not in serialized
    assert "correct_answer" not in serialized
    assert "is_correct" not in serialized


def test_mastery_history_is_chronological_shape_with_skill_context() -> None:
    snapshot = _snapshot()
    history = MasteryHistory(
        subject="english",
        skill_id=snapshot.skill_id,
        skill_key=snapshot.skill_key,
        skill_name=snapshot.skill_name,
        snapshots=[snapshot],
    )

    assert history.skill_key == "english.conventions.sentence-structure"
    assert history.snapshots[0].calculated_at.tzinfo is not None


def test_remediation_cycle_summary_has_progress_card_fields_without_items() -> None:
    cycle = RemediationCycleSummary(
        id=str(uuid4()),
        subject="math",
        skill_id=str(uuid4()),
        skill_key="math.algebra.linear-equations",
        skill_name="Linear equations",
        status="practicing",
        attempt_number=1,
        resource_count=2,
        practice_set_status="in_progress",
        reassessment_status=None,
    )

    assert cycle.resource_count == 2
    assert cycle.practice_set_status == "in_progress"
    assert cycle.resources == []
    assert "answer_key" not in cycle.model_dump_json()


def test_progress_models_reject_unknown_subjects() -> None:
    with pytest.raises(ValidationError):
        MasteryOverview(subject="science")
    with pytest.raises(ValidationError):
        RemediationCycleSummary(
            id=str(uuid4()),
            subject="science",
            skill_id=str(uuid4()),
            skill_key="science.skill",
            skill_name="Not supported",
            status="recommended",
            attempt_number=1,
            resource_count=0,
        )


def test_invalid_authenticated_or_path_uuid_maps_to_safe_domain_errors() -> None:
    with pytest.raises(ProgressUnavailable):
        _student_uuid("not-a-uuid")
    with pytest.raises(ProgressNotFound):
        _path_uuid("not-a-uuid", "Mastery history was not found")
