from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.content_ops import InventoryReadiness


def test_inventory_readiness_is_safe_and_explicit_about_assignment_gates() -> None:
    report = InventoryReadiness(
        subject="english",
        purpose="practice",
        blueprint_id=str(uuid4()),
        blueprint_status="approved",
        item_count=5,
        approved_question_count=8,
        approved_primary_mapping_count=8,
        approved_resource_count=1,
        ready_for_assignment=True,
    )

    assert report.ready_for_assignment is True
    serialized = report.model_dump_json()
    assert "stem" not in serialized
    assert "answer_key" not in serialized
    assert "correct_answer" not in serialized


def test_inventory_readiness_rejects_invalid_purpose_and_counts() -> None:
    with pytest.raises(ValidationError):
        InventoryReadiness(
            subject="english",
            purpose="other",
            blueprint_id=str(uuid4()),
            blueprint_status="draft",
            item_count=0,
            approved_question_count=0,
            approved_primary_mapping_count=0,
            approved_resource_count=0,
            ready_for_assignment=False,
        )
