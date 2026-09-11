from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.analytics import (
    AnalyticsNotFound,
    PilotExport,
    PilotExportRow,
    _pilot_id,
    _validate_experiment_key,
)


def test_export_uses_a_stable_keyed_pilot_pseudonym() -> None:
    first = _pilot_id("student-1", "export-secret")
    second = _pilot_id("student-1", "export-secret")
    different_secret = _pilot_id("student-1", "other-secret")

    assert first == second
    assert first != different_secret
    assert first.startswith("pilot_")
    assert "student-1" not in first


def test_experiment_keys_are_bounded_and_safe() -> None:
    assert _validate_experiment_key("pilot-2026") == "pilot-2026"
    with pytest.raises(AnalyticsNotFound):
        _validate_experiment_key("../../students")
    with pytest.raises(AnalyticsNotFound):
        _validate_experiment_key(" ")


def test_export_shape_contains_no_direct_identity_or_answer_fields() -> None:
    export = PilotExport(
        experiment_key="pilot-2026",
        generated_at=datetime.now(timezone.utc),
        rows=[
            PilotExportRow(
                pilot_id="pilot_1234567890123456",
                variant="control",
                subject="english",
                tutor_skill_keys=["english.skill"],
                system_skill_keys=["english.skill"],
                diagnostic_sessions=1,
                completed_reassessments=1,
                remediation_outcomes=["mastered"],
            )
        ],
    )

    with pytest.raises(ValidationError):
        PilotExportRow(
            pilot_id="short",
            variant="control",
            subject="english",
            diagnostic_sessions=1,
            completed_reassessments=0,
        )
    serialized = export.model_dump_json()
    assert "email" not in serialized
    assert "answer_key" not in serialized
    assert "correct_answer" not in serialized
