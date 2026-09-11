from uuid import uuid4

from app.assessments import ScoredItem


def test_scored_item_can_carry_post_submit_explanation_without_answer_key() -> None:
    item = ScoredItem(
        session_item_id=str(uuid4()),
        question_id=str(uuid4()),
        choice_id="B",
        correct=False,
        explanation="This choice changes the intended relationship between the clauses.",
    )

    serialized = item.model_dump_json()
    assert item.explanation is not None
    assert "correct_choice" not in serialized
    assert "answer_key" not in serialized
