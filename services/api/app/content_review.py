"""Reviewer content-approval primitives.

This module intentionally does not register routes.  An internal FastAPI
handler can validate :class:`ContentReviewRequest`, require reviewer access,
and call :func:`review_content_slice` from a worker thread.

The current schema has no blueprint-to-source join table.  A review request
therefore names the content sources that make up the slice explicitly.  The
database operation keeps that scope fixed, records a review row for every
question in the slice, and returns only safe lifecycle/count metadata.  It
never returns question text, choices, correctness, or candidate payloads.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from .content import SubjectSlug

AssessmentPurpose = Literal["diagnostic", "practice", "reassessment"]
ReviewDecision = Literal["publish", "reject"]
ContentLifecycleStatus = Literal["approved", "retired"]

_BLOCKED_RIGHTS_STATUSES = frozenset({"blocked", "denied", "prohibited", "restricted"})
_UNREVIEWABLE_QUESTION_STATUSES = frozenset({"rejected", "needs_adjudication"})


class ContentReviewError(Exception):
    """Base class for safe reviewer-domain errors."""


class ContentReviewNotFound(ContentReviewError):
    """The blueprint or explicitly selected source slice was not found."""


class ContentReviewConflict(ContentReviewError):
    """The requested review cannot be applied to the current content state."""


class ContentReviewUnavailable(ContentReviewError):
    """The database or its Python dependency is unavailable."""


class ContentReviewRequest(BaseModel):
    """An explicit reviewer decision for one draft blueprint and source slice."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    blueprint_id: UUID
    content_source_ids: list[UUID] = Field(min_length=1, max_length=100)
    decision: ReviewDecision
    confirm_review: StrictBool
    confirm_content_review: StrictBool
    confirm_rights_clearance: StrictBool
    confirm_answer_key_review: StrictBool
    notes: StrictStr = Field(min_length=1, max_length=2_000)

    @field_validator("content_source_ids")
    @classmethod
    def require_unique_source_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("content_source_ids must not contain duplicates")
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def require_non_blank_notes(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("notes must not be blank")
        return value

    @model_validator(mode="after")
    def require_explicit_confirmations(self) -> "ContentReviewRequest":
        required = ["confirm_review", "confirm_content_review"]
        if self.decision == "publish":
            required.extend(("confirm_rights_clearance", "confirm_answer_key_review"))

        missing = [name for name in required if not getattr(self, name)]
        if missing:
            raise ValueError(
                f"{self.decision} requires explicit confirmation: {', '.join(missing)}"
            )
        return self


class ContentReviewCounts(BaseModel):
    """Counts safe to return to a reviewer without exposing content."""

    model_config = ConfigDict(extra="forbid")

    sources: StrictInt = Field(ge=0)
    tests: StrictInt = Field(ge=0)
    sections: StrictInt = Field(ge=0)
    passages: StrictInt = Field(ge=0)
    questions: StrictInt = Field(ge=0)


class ContentReviewResult(BaseModel):
    """Safe result of a publish/reject operation."""

    model_config = ConfigDict(extra="forbid")

    blueprint_id: UUID
    subject: SubjectSlug
    purpose: AssessmentPurpose
    version: StrictStr
    decision: ReviewDecision
    lifecycle_status: ContentLifecycleStatus
    counts: ContentReviewCounts
    reviewer_id: UUID
    reviewed_at: datetime


def _reviewer_uuid(reviewer_id: str) -> UUID:
    try:
        return UUID(reviewer_id)
    except (TypeError, ValueError) as exc:
        raise ContentReviewUnavailable("The reviewer ID is not a UUID") from exc


def _connect(database_url: str | None) -> Any:
    if not database_url:
        raise ContentReviewUnavailable("Content review database is not configured")
    try:
        import psycopg
    except ImportError as exc:
        raise ContentReviewUnavailable("Database dependencies are unavailable") from exc
    try:
        return psycopg.connect(database_url)
    except Exception as exc:
        raise ContentReviewUnavailable("Content review database is unavailable") from exc


def _load_blueprint(cursor: Any, blueprint_id: UUID) -> tuple[Any, ...]:
    cursor.execute(
        """
        SELECT blueprint.id, subject.id, subject.slug, blueprint.purpose::text,
               blueprint.version, blueprint.status::text
        FROM assessment_blueprints blueprint
        JOIN subjects subject ON subject.id = blueprint.subject_id
        WHERE blueprint.id = %s
        FOR UPDATE
        """,
        (blueprint_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise ContentReviewNotFound("Assessment blueprint was not found")
    if row[5] != "draft":
        raise ContentReviewConflict("Only a draft assessment blueprint can be reviewed")
    return row


def _load_sources(cursor: Any, source_ids: list[UUID], subject_id: UUID) -> list[tuple[Any, ...]]:
    cursor.execute(
        """
        SELECT source.id, source.rights_status,
               count(DISTINCT test.id), count(DISTINCT question.id)
        FROM content_sources source
        JOIN tests test ON test.source_id = source.id
        LEFT JOIN questions question ON question.source_id = source.id
        WHERE source.id = ANY(%s) AND test.subject_id = %s
        GROUP BY source.id, source.rights_status
        ORDER BY source.id
        """,
        (source_ids, subject_id),
    )
    rows = cursor.fetchall()
    found_ids = {row[0] for row in rows}
    if found_ids != set(source_ids):
        raise ContentReviewNotFound("One or more selected content sources were not found for the blueprint")
    return rows


def _load_question_checks(cursor: Any, source_ids: list[UUID], subject_id: UUID) -> list[tuple[Any, ...]]:
    cursor.execute(
        """
        SELECT question.id, question.status::text, question.review_status::text,
               count(DISTINCT choice.id),
               count(DISTINCT choice.id) FILTER (WHERE choice.is_correct),
               count(DISTINCT question_skill.skill_id)
                 FILTER (WHERE question_skill.role = 'primary')
        FROM questions question
        JOIN tests test ON test.source_id = question.source_id
        LEFT JOIN answer_choices choice ON choice.question_id = question.id
        LEFT JOIN question_skills question_skill ON question_skill.question_id = question.id
        WHERE question.source_id = ANY(%s) AND test.subject_id = %s
        GROUP BY question.id, question.status, question.review_status
        ORDER BY question.id
        """,
        (source_ids, subject_id),
    )
    return cursor.fetchall()


def _load_content_counts(cursor: Any, source_ids: list[UUID], subject_id: UUID) -> ContentReviewCounts:
    cursor.execute(
        """
        SELECT count(DISTINCT source.id), count(DISTINCT test.id),
               count(DISTINCT section.id), count(DISTINCT passage.id),
               count(DISTINCT question.id)
        FROM content_sources source
        JOIN tests test ON test.source_id = source.id AND test.subject_id = %s
        LEFT JOIN sections section ON section.test_id = test.id
        LEFT JOIN passages passage ON passage.source_id = source.id
        LEFT JOIN questions question ON question.source_id = source.id
        WHERE source.id = ANY(%s)
        """,
        (subject_id, source_ids),
    )
    row = cursor.fetchone()
    if not row:
        raise ContentReviewConflict("The selected content slice could not be counted")
    return ContentReviewCounts(
        sources=int(row[0]),
        tests=int(row[1]),
        sections=int(row[2]),
        passages=int(row[3]),
        questions=int(row[4]),
    )


def _validate_publishable_slice(
    payload: ContentReviewRequest,
    source_rows: list[tuple[Any, ...]],
    question_rows: list[tuple[Any, ...]],
) -> None:
    unusable_sources = [
        str(row[0])
        for row in source_rows
        if str(row[1]).lower() not in {"unreviewed", "approved"}
        or str(row[1]).lower() in _BLOCKED_RIGHTS_STATUSES
    ]
    if unusable_sources:
        raise ContentReviewConflict("The selected content slice contains unusable provenance")

    if not question_rows:
        raise ContentReviewConflict("The selected content slice contains no questions")

    invalid_questions = [
        str(row[0])
        for row in question_rows
        if str(row[1]) == "retired" or str(row[2]) in _UNREVIEWABLE_QUESTION_STATUSES
    ]
    if invalid_questions:
        raise ContentReviewConflict("The selected content slice contains retired or rejected questions")

    incomplete_questions = [
        str(row[0])
        for row in question_rows
        if int(row[3]) < 2 or int(row[4]) != 1 or int(row[5]) < 1
    ]
    if incomplete_questions:
        raise ContentReviewConflict(
            "Every question must have choices, exactly one correct choice, and a primary skill mapping"
        )

    if payload.decision != "publish":
        raise ContentReviewConflict("A publish validation was requested for a non-publish decision")


def _record_question_reviews(
    cursor: Any,
    question_rows: list[tuple[Any, ...]],
    reviewer_id: UUID,
    payload: ContentReviewRequest,
    verdict: Literal["approved", "rejected"],
) -> None:
    from psycopg.types.json import Jsonb

    for row in question_rows:
        cursor.execute(
            """
            INSERT INTO content_reviews
              (question_id, reviewer_id, review_type, verdict, rubric_version, findings)
            VALUES (%s, %s, %s, %s, 'content-review-v1', %s)
            """,
            (
                row[0],
                reviewer_id,
                f"blueprint_{payload.decision}",
                verdict,
                Jsonb(
                    {
                        "blueprintId": str(payload.blueprint_id),
                        "decision": payload.decision,
                        "notes": payload.notes,
                    }
                ),
            ),
        )


def _publish_slice(
    cursor: Any,
    payload: ContentReviewRequest,
    source_ids: list[UUID],
    source_rows: list[tuple[Any, ...]],
    question_rows: list[tuple[Any, ...]],
    subject_id: UUID,
) -> None:
    _validate_publishable_slice(payload, source_rows, question_rows)
    cursor.execute(
        "UPDATE content_sources SET rights_status = 'approved' WHERE id = ANY(%s)",
        (source_ids,),
    )
    cursor.execute(
        """
        UPDATE tests
        SET status = 'approved'
        WHERE source_id = ANY(%s) AND subject_id = %s AND status <> 'retired'
        """,
        (source_ids, subject_id),
    )
    cursor.execute(
        """
        UPDATE sections
        SET status = 'approved'
        WHERE test_id IN (
          SELECT id FROM tests WHERE source_id = ANY(%s) AND subject_id = %s
        ) AND status <> 'retired'
        """,
        (source_ids, subject_id),
    )
    cursor.execute(
        """
        UPDATE passages
        SET status = 'approved'
        WHERE source_id = ANY(%s) AND status <> 'retired'
        """,
        (source_ids,),
    )
    cursor.execute(
        """
        UPDATE questions
        SET status = 'approved', review_status = 'approved'
        WHERE source_id = ANY(%s)
          AND EXISTS (
            SELECT 1 FROM tests
            WHERE tests.source_id = questions.source_id
              AND tests.subject_id = %s
          )
          AND status <> 'retired'
          AND review_status NOT IN ('rejected', 'needs_adjudication')
        """,
        (source_ids, subject_id),
    )
    cursor.execute(
        """
        UPDATE generated_candidates
        SET review_status = 'approved'
        WHERE question_id IN (
          SELECT question.id
          FROM questions question
          WHERE question.source_id = ANY(%s)
            AND EXISTS (
              SELECT 1 FROM tests
              WHERE tests.source_id = question.source_id
                AND tests.subject_id = %s
            )
        ) AND review_status NOT IN ('rejected', 'needs_adjudication')
        """,
        (source_ids, subject_id),
    )


def _reject_slice(
    cursor: Any,
    source_ids: list[UUID],
    question_rows: list[tuple[Any, ...]],
    subject_id: UUID,
) -> None:
    del question_rows
    cursor.execute(
        """
        UPDATE questions
        SET review_status = 'rejected'
        WHERE source_id = ANY(%s)
          AND EXISTS (
            SELECT 1 FROM tests
            WHERE tests.source_id = questions.source_id
              AND tests.subject_id = %s
          )
          AND status <> 'retired'
        """,
        (source_ids, subject_id),
    )
    cursor.execute(
        """
        UPDATE generated_candidates
        SET review_status = 'rejected'
        WHERE question_id IN (
          SELECT question.id
          FROM questions question
          WHERE question.source_id = ANY(%s)
            AND EXISTS (
              SELECT 1 FROM tests
              WHERE tests.source_id = question.source_id
                AND tests.subject_id = %s
            )
        )
        """,
        (source_ids, subject_id),
    )


def review_content_slice(
    database_url: str | None,
    reviewer_id: str,
    payload: ContentReviewRequest,
) -> ContentReviewResult:
    """Publish or reject one explicitly selected blueprint/content slice.

    Publish promotes the selected source-backed content to the public
    lifecycle only after the request's confirmation gates and database checks
    pass.  Reject retires the blueprint and marks its questions rejected so
    they cannot be assigned, while retaining the source rows for audit.
    """

    request = ContentReviewRequest.model_validate(payload)
    reviewer_uuid = _reviewer_uuid(reviewer_id)

    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                blueprint = _load_blueprint(cursor, request.blueprint_id)
                source_rows = _load_sources(cursor, request.content_source_ids, blueprint[1])
                question_rows = _load_question_checks(cursor, request.content_source_ids, blueprint[1])

                if request.decision == "publish":
                    _validate_publishable_slice(request, source_rows, question_rows)
                    _publish_slice(
                        cursor,
                        request,
                        request.content_source_ids,
                        source_rows,
                        question_rows,
                        blueprint[1],
                    )
                    lifecycle_status: ContentLifecycleStatus = "approved"
                    verdict: Literal["approved", "rejected"] = "approved"
                else:
                    _reject_slice(
                        cursor,
                        request.content_source_ids,
                        question_rows,
                        blueprint[1],
                    )
                    lifecycle_status = "retired"
                    verdict = "rejected"

                cursor.execute(
                    "UPDATE assessment_blueprints SET status = %s::content_lifecycle WHERE id = %s",
                    (lifecycle_status, request.blueprint_id),
                )
                _record_question_reviews(cursor, question_rows, reviewer_uuid, request, verdict)
                counts = _load_content_counts(cursor, request.content_source_ids, blueprint[1])
                return ContentReviewResult(
                    blueprint_id=blueprint[0],
                    subject=blueprint[2],
                    purpose=blueprint[3],
                    version=blueprint[4],
                    decision=request.decision,
                    lifecycle_status=lifecycle_status,
                    counts=counts,
                    reviewer_id=reviewer_uuid,
                    reviewed_at=datetime.now(timezone.utc),
                )
    except ContentReviewError:
        raise
    except Exception as exc:
        raise ContentReviewUnavailable("Content review could not be completed") from exc


def publish_content_slice(
    database_url: str | None,
    reviewer_id: str,
    payload: ContentReviewRequest,
) -> ContentReviewResult:
    """Convenience wrapper for an endpoint dedicated to publishing."""

    if payload.decision != "publish":
        raise ContentReviewConflict("The content review decision must be publish")
    return review_content_slice(database_url, reviewer_id, payload)


def reject_content_slice(
    database_url: str | None,
    reviewer_id: str,
    payload: ContentReviewRequest,
) -> ContentReviewResult:
    """Convenience wrapper for an endpoint dedicated to rejecting."""

    if payload.decision != "reject":
        raise ContentReviewConflict("The content review decision must be reject")
    return review_content_slice(database_url, reviewer_id, payload)
