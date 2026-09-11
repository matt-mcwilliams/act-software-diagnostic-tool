"""Database-backed remediation-cycle primitives.

This module deliberately has no FastAPI route registration.  Route handlers can
call these functions from a thread pool and map the domain exceptions below to
HTTP responses.  Assessment items are loaded through the existing public
assessment loader, which selects prompts and choice labels only; answer keys
never cross this boundary.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .assessments import (
    AssessmentItem,
    AssessmentNotFound,
    AssessmentSession,
    AssessmentUnavailable,
    _item_count,
    _load_session,
)
from .content import SubjectSlug

RemediationStatus = Literal[
    "recommended",
    "learning",
    "practicing",
    "ready_to_reassess",
    "reassessing",
    "mastered",
    "repeat_recommended",
    "needs_more_evidence",
    "abandoned",
]
PracticeSetStatus = Literal["created", "in_progress", "completed"]

_TERMINAL_CYCLE_STATUSES = ("mastered", "abandoned")
_PRACTICE_PURPOSE = "practice"
_REASSESSMENT_PURPOSE = "reassessment"


class RemediationError(Exception):
    """Base class for errors that a route handler can expose safely."""


class RemediationNotFound(RemediationError):
    """The requested resource is absent or is owned by another student."""


class RemediationConflict(RemediationError):
    """The requested state transition or content selection is not allowed."""


class RemediationUnavailable(RemediationError):
    """The service cannot fulfill the request because a dependency is unavailable."""


class RemediationCycleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: UUID | None = None
    recommendation_id: UUID | None = None

    @model_validator(mode="after")
    def require_target(self) -> "RemediationCycleCreateRequest":
        if self.skill_id is None and self.recommendation_id is None:
            raise ValueError("skill_id or recommendation_id is required")
        return self


class LearningResource(BaseModel):
    id: str
    provider: str
    title: str
    url: str
    resource_type: str
    focus_note: str | None = None


class RemediationCycle(BaseModel):
    id: str
    subject: SubjectSlug
    skill_id: str
    skill_key: str
    skill_name: str
    recommendation_id: str | None = None
    status: RemediationStatus
    baseline_snapshot_id: str | None = None
    attempt_number: int = Field(ge=1)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    resources: list[LearningResource] = Field(default_factory=list)
    practice_set_id: str | None = None
    practice_session_id: str | None = None
    reassessment_session_id: str | None = None


class ResourceEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: UUID
    event_type: str = Field(min_length=1, max_length=100)

    @field_validator("event_type")
    @classmethod
    def non_blank_event_type(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("event_type must not be blank")
        return value


class ResourceEvent(BaseModel):
    id: str
    cycle_id: str
    resource_id: str
    event_type: str
    occurred_at: datetime


class PracticeSetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_count: int = Field(default=5, ge=1, le=50)
    assembly_version: str = Field(default="practice-v1", min_length=1, max_length=100)


class PracticeSet(BaseModel):
    id: str
    cycle_id: str
    assessment_session_id: str
    status: PracticeSetStatus
    target_count: int = Field(ge=1)
    assembly_version: str
    created_at: datetime
    completed_at: datetime | None = None
    assessment_session: AssessmentSession


class PracticeSetCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReassessmentSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The approved reassessment blueprint remains authoritative.  This field
    # is only a bounded opt-in for a shorter set during an internal pilot.
    target_count: int | None = Field(default=None, ge=1, le=50)


def _student_uuid(student_id: str) -> UUID:
    try:
        return UUID(student_id)
    except (TypeError, ValueError) as exc:
        raise RemediationUnavailable("The authenticated user ID is not a UUID") from exc


def _path_uuid(value: str, message: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise RemediationNotFound(message) from exc


def _connect(database_url: str) -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RemediationUnavailable("Database dependencies are unavailable") from exc
    return psycopg.connect(database_url)


def _load_cycle(cursor: Any, student_id: UUID, cycle_id: UUID) -> RemediationCycle:
    cursor.execute(
        """
        SELECT cycle.id, cycle.skill_id, skill.external_key, skill.name,
               cycle.recommendation_id, cycle.status::text,
               cycle.baseline_snapshot_id, cycle.attempt_number,
               cycle.started_at, cycle.completed_at, subject.slug
        FROM remediation_cycles cycle
        JOIN skills skill ON skill.id = cycle.skill_id
        JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
        JOIN subjects subject ON subject.id = taxonomy.subject_id
        WHERE cycle.id = %s AND cycle.student_id = %s
        """,
        (cycle_id, student_id),
    )
    row = cursor.fetchone()
    if not row:
        raise RemediationNotFound("Remediation cycle was not found")
    cursor.execute(
        """
        SELECT id, provider, title, url, resource_type, focus_note
        FROM learning_resources
        WHERE skill_id = %s AND status = 'approved'
        ORDER BY id
        """,
        (row[1],),
    )
    resources = [
        LearningResource(
            id=str(resource[0]),
            provider=str(resource[1]),
            title=str(resource[2]),
            url=str(resource[3]),
            resource_type=str(resource[4]),
            focus_note=resource[5],
        )
        for resource in cursor.fetchall()
    ]
    cursor.execute(
        """
        SELECT id, assessment_session_id
        FROM practice_sets
        WHERE cycle_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (cycle_id,),
    )
    practice_row = cursor.fetchone()
    cursor.execute(
        """
        SELECT assessment_session_id
        FROM reassessment_links
        WHERE cycle_id = %s
        ORDER BY attempt_number DESC, assessment_session_id DESC
        LIMIT 1
        """,
        (cycle_id,),
    )
    reassessment_row = cursor.fetchone()
    return RemediationCycle(
        id=str(row[0]),
        subject=row[10],
        skill_id=str(row[1]),
        skill_key=str(row[2]),
        skill_name=str(row[3]),
        recommendation_id=str(row[4]) if row[4] else None,
        status=row[5],
        baseline_snapshot_id=str(row[6]) if row[6] else None,
        attempt_number=int(row[7]),
        started_at=row[8],
        completed_at=row[9],
        resources=resources,
        practice_set_id=str(practice_row[0]) if practice_row else None,
        practice_session_id=str(practice_row[1]) if practice_row and practice_row[1] else None,
        reassessment_session_id=str(reassessment_row[0]) if reassessment_row else None,
    )


def get_remediation_cycle(
    database_url: str,
    student_id: str,
    cycle_id: str,
) -> RemediationCycle:
    student_uuid = _student_uuid(student_id)
    cycle_uuid = _path_uuid(cycle_id, "Remediation cycle was not found")
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            return _load_cycle(cursor, student_uuid, cycle_uuid)


def create_or_get_remediation_cycle(
    database_url: str,
    student_id: str,
    payload: RemediationCycleCreateRequest,
) -> RemediationCycle:
    """Create or resume the authenticated student's active cycle for a target."""
    student_uuid = _student_uuid(student_id)
    recommendation_uuid = payload.recommendation_id
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            skill_id: UUID
            if recommendation_uuid is not None:
                cursor.execute(
                    """
                    SELECT recommendation.skill_id, recommendation.readiness,
                           recommendation.status, skill.status,
                           recommendation.id
                    FROM recommendations recommendation
                    JOIN recommendation_runs run ON run.id = recommendation.run_id
                    JOIN skills skill ON skill.id = recommendation.skill_id
                    WHERE recommendation.id = %s
                      AND run.student_id = %s
                      AND recommendation.status = 'current'
                      AND skill.status = 'approved'
                    """,
                    (recommendation_uuid, student_uuid),
                )
                recommendation_row = cursor.fetchone()
                if not recommendation_row:
                    raise RemediationNotFound("Approved recommendation was not found")
                if not bool(recommendation_row[1]):
                    raise RemediationConflict(
                        "The recommendation does not have an approved learning path"
                    )
                skill_id = UUID(str(recommendation_row[0]))
                if payload.skill_id is not None and payload.skill_id != skill_id:
                    raise RemediationConflict(
                        "The skill does not match the selected recommendation"
                    )
            else:
                skill_id = payload.skill_id  # validated by the model validator
                cursor.execute(
                    """
                    SELECT id
                    FROM skills
                    WHERE id = %s AND status = 'approved'
                    """,
                    (skill_id,),
                )
                if not cursor.fetchone():
                    raise RemediationNotFound("Approved skill was not found")

            cycle_query = """
                SELECT id
                FROM remediation_cycles
                WHERE student_id = %s AND skill_id = %s
                  AND status IN ('recommended', 'learning', 'practicing',
                                 'ready_to_reassess', 'reassessing')
            """
            cycle_params: list[Any] = [student_uuid, skill_id]
            if recommendation_uuid is not None:
                cycle_query += " AND recommendation_id = %s"
                cycle_params.append(recommendation_uuid)
            cycle_query += """
                ORDER BY attempt_number DESC, id DESC
                LIMIT 1
                FOR UPDATE
            """
            cursor.execute(cycle_query, cycle_params)
            existing_row = cursor.fetchone()
            if existing_row:
                return _load_cycle(cursor, student_uuid, existing_row[0])

            cursor.execute(
                """
                SELECT id
                FROM mastery_snapshots
                WHERE student_id = %s AND skill_id = %s
                ORDER BY calculated_at DESC, id DESC
                LIMIT 1
                """,
                (student_uuid, skill_id),
            )
            baseline_row = cursor.fetchone()
            baseline_snapshot_id = baseline_row[0] if baseline_row else None

            cursor.execute(
                """
                SELECT COALESCE(MAX(attempt_number), 0) + 1
                FROM remediation_cycles
                WHERE student_id = %s AND skill_id = %s
                """,
                (student_uuid, skill_id),
            )
            attempt_number = int(cursor.fetchone()[0])
            cursor.execute(
                """
                INSERT INTO remediation_cycles
                  (student_id, skill_id, recommendation_id, status,
                   baseline_snapshot_id, attempt_number, started_at)
                VALUES (%s, %s, %s, 'recommended', %s, %s, now())
                RETURNING id
                """,
                (
                    student_uuid,
                    skill_id,
                    recommendation_uuid,
                    baseline_snapshot_id,
                    attempt_number,
                ),
            )
            inserted_row = cursor.fetchone()
            if not inserted_row:
                raise RemediationUnavailable("Remediation cycle could not be created")
            return _load_cycle(cursor, student_uuid, inserted_row[0])


def record_resource_event(
    database_url: str,
    student_id: str,
    cycle_id: str,
    payload: ResourceEventRequest,
) -> ResourceEvent:
    """Record an event only for an approved resource on the student's cycle."""
    student_uuid = _student_uuid(student_id)
    cycle_uuid = _path_uuid(cycle_id, "Remediation cycle was not found")
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT cycle.status::text, resource.id
                FROM remediation_cycles cycle
                JOIN learning_resources resource ON resource.skill_id = cycle.skill_id
                WHERE cycle.id = %s AND cycle.student_id = %s
                  AND resource.id = %s AND resource.status = 'approved'
                FOR UPDATE OF cycle
                """,
                (cycle_uuid, student_uuid, payload.resource_id),
            )
            cycle_row = cursor.fetchone()
            if not cycle_row:
                raise RemediationNotFound(
                    "Approved learning resource was not found for this cycle"
                )
            if cycle_row[0] in _TERMINAL_CYCLE_STATUSES:
                raise RemediationConflict("The remediation cycle is no longer active")

            cursor.execute(
                """
                INSERT INTO resource_events (cycle_id, resource_id, event_type)
                VALUES (%s, %s, %s)
                RETURNING id, cycle_id, resource_id, event_type, occurred_at
                """,
                (cycle_uuid, payload.resource_id, payload.event_type),
            )
            event_row = cursor.fetchone()
            if not event_row:
                raise RemediationUnavailable("Resource event could not be recorded")

            if payload.event_type == "resource_opened" and cycle_row[0] == "recommended":
                cursor.execute(
                    """
                    UPDATE remediation_cycles
                    SET status = 'learning', started_at = COALESCE(started_at, now())
                    WHERE id = %s AND student_id = %s
                    """,
                    (cycle_uuid, student_uuid),
                )
            return ResourceEvent(
                id=str(event_row[0]),
                cycle_id=str(event_row[1]),
                resource_id=str(event_row[2]),
                event_type=str(event_row[3]),
                occurred_at=event_row[4],
            )


def _load_public_session(cursor: Any, student_id: UUID, session_id: UUID) -> AssessmentSession:
    try:
        return _load_session(cursor, student_id, str(session_id))
    except AssessmentNotFound as exc:
        raise RemediationNotFound("Assessment session was not found") from exc
    except AssessmentUnavailable as exc:
        raise RemediationUnavailable(str(exc)) from exc


def _load_practice_set(cursor: Any, student_id: UUID, practice_set_id: UUID) -> PracticeSet:
    cursor.execute(
        """
        SELECT practice_set.id, practice_set.cycle_id,
               practice_set.assessment_session_id, practice_set.status,
               practice_set.target_count, practice_set.assembly_version,
               practice_set.created_at, practice_set.completed_at
        FROM practice_sets practice_set
        JOIN remediation_cycles cycle ON cycle.id = practice_set.cycle_id
        WHERE practice_set.id = %s AND cycle.student_id = %s
        """,
        (practice_set_id, student_id),
    )
    row = cursor.fetchone()
    if not row or not row[2]:
        raise RemediationNotFound("Practice set was not found")
    return PracticeSet(
        id=str(row[0]),
        cycle_id=str(row[1]),
        assessment_session_id=str(row[2]),
        status=row[3],
        target_count=int(row[4]),
        assembly_version=str(row[5]),
        created_at=row[6],
        completed_at=row[7],
        assessment_session=_load_public_session(cursor, student_id, row[2]),
    )


def get_practice_set(
    database_url: str,
    student_id: str,
    practice_set_id: str,
) -> PracticeSet:
    student_uuid = _student_uuid(student_id)
    practice_set_uuid = _path_uuid(practice_set_id, "Practice set was not found")
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            return _load_practice_set(cursor, student_uuid, practice_set_uuid)


def _approved_blueprint(
    cursor: Any,
    subject_id: UUID,
    purpose: Literal["practice", "reassessment"],
) -> tuple[Any, ...]:
    cursor.execute(
        """
        SELECT id, rules, scoring_version, mastery_model_version
        FROM assessment_blueprints
        WHERE subject_id = %s AND purpose = %s AND status = 'approved'
        ORDER BY version DESC, id DESC
        LIMIT 1
        """,
        (subject_id, purpose),
    )
    row = cursor.fetchone()
    if not row:
        raise RemediationUnavailable(f"No approved {purpose} blueprint is available")
    item_count = _item_count(row[1])
    if not item_count:
        raise RemediationUnavailable(f"Approved {purpose} blueprint has no valid item count")
    return row[0], item_count


def _approved_unseen_questions(
    cursor: Any,
    student_id: UUID,
    skill_id: UUID,
    subject_id: UUID,
    purpose: Literal["practice", "reassessment"],
    item_count: int,
) -> list[Any]:
    cursor.execute(
        """
        SELECT DISTINCT question.id
        FROM questions question
        JOIN content_sources source ON source.id = question.source_id
        JOIN tests test ON test.source_id = question.source_id
        JOIN question_skills question_skill
          ON question_skill.question_id = question.id
         AND question_skill.skill_id = %s
         AND question_skill.role = 'primary'
        WHERE test.subject_id = %s
          AND test.status = 'approved'
          AND source.rights_status = 'approved'
          AND question.status = 'approved'
          AND question.review_status = 'approved'
          AND NOT EXISTS (
            SELECT 1
            FROM item_exposures exposure
            WHERE exposure.student_id = %s
              AND exposure.question_id = question.id
          )
        ORDER BY question.id
        LIMIT %s
        """,
        (skill_id, subject_id, student_id, item_count),
    )
    question_rows = cursor.fetchall()
    if len(question_rows) < item_count:
        raise RemediationUnavailable(
            f"Approved unseen {purpose} inventory is insufficient for this skill"
        )
    return [row[0] for row in question_rows]


def _insert_assessment_session(
    cursor: Any,
    student_id: UUID,
    blueprint_id: UUID,
    purpose: Literal["practice", "reassessment"],
) -> UUID:
    cursor.execute(
        """
        INSERT INTO assessment_sessions
          (student_id, blueprint_id, purpose, status, started_at)
        VALUES (%s, %s, %s, 'in_progress', now())
        ON CONFLICT (student_id, blueprint_id)
          WHERE status IN ('created', 'in_progress')
        DO NOTHING
        RETURNING id
        """,
        (student_id, blueprint_id, purpose),
    )
    row = cursor.fetchone()
    if not row:
        raise RemediationConflict(
            f"An open {purpose} assessment already exists for this student"
        )
    return row[0]


def _insert_session_items_and_exposures(
    cursor: Any,
    student_id: UUID,
    session_id: UUID,
    question_ids: list[Any],
    purpose: Literal["practice", "reassessment"],
) -> None:
    for position, question_id in enumerate(question_ids, start=1):
        cursor.execute(
            """
            INSERT INTO assessment_session_items (session_id, question_id, position)
            VALUES (%s, %s, %s)
            """,
            (session_id, question_id, position),
        )
        cursor.execute(
            """
            INSERT INTO item_exposures (student_id, question_id, session_id, purpose)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (student_id, question_id, purpose) DO NOTHING
            """,
            (student_id, question_id, session_id, purpose),
        )


def _insert_practice_set_items(
    cursor: Any,
    practice_set_id: UUID,
    question_ids: list[Any],
) -> None:
    for position, question_id in enumerate(question_ids, start=1):
        cursor.execute(
            """
            INSERT INTO practice_set_items (practice_set_id, question_id, position)
            VALUES (%s, %s, %s)
            """,
            (practice_set_id, question_id, position),
        )


def create_or_get_practice_set(
    database_url: str,
    student_id: str,
    cycle_id: str,
    payload: PracticeSetCreateRequest | None = None,
) -> PracticeSet:
    """Assemble one approved, unseen practice set for an owned cycle."""
    student_uuid = _student_uuid(student_id)
    cycle_uuid = _path_uuid(cycle_id, "Remediation cycle was not found")
    request = payload or PracticeSetCreateRequest()
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT cycle.skill_id, taxonomy.subject_id, cycle.status::text
                FROM remediation_cycles cycle
                JOIN skills skill ON skill.id = cycle.skill_id
                JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
                WHERE cycle.id = %s AND cycle.student_id = %s
                FOR UPDATE OF cycle
                """,
                (cycle_uuid, student_uuid),
            )
            cycle_row = cursor.fetchone()
            if not cycle_row:
                raise RemediationNotFound("Remediation cycle was not found")
            if cycle_row[2] in _TERMINAL_CYCLE_STATUSES:
                raise RemediationConflict("The remediation cycle is no longer active")

            cursor.execute(
                """
                SELECT id
                FROM practice_sets
                WHERE cycle_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                FOR UPDATE
                """,
                (cycle_uuid,),
            )
            existing_row = cursor.fetchone()
            if existing_row:
                return _load_practice_set(cursor, student_uuid, existing_row[0])

            blueprint_id, blueprint_count = _approved_blueprint(
                cursor, cycle_row[1], _PRACTICE_PURPOSE
            )
            target_count = min(request.target_count, blueprint_count)
            question_ids = _approved_unseen_questions(
                cursor,
                student_uuid,
                cycle_row[0],
                cycle_row[1],
                _PRACTICE_PURPOSE,
                target_count,
            )
            session_id = _insert_assessment_session(
                cursor, student_uuid, blueprint_id, _PRACTICE_PURPOSE
            )
            _insert_session_items_and_exposures(
                cursor, student_uuid, session_id, question_ids, _PRACTICE_PURPOSE
            )
            cursor.execute(
                """
                INSERT INTO practice_sets
                  (cycle_id, assessment_session_id, status, target_count,
                   assembly_version)
                VALUES (%s, %s, 'in_progress', %s, %s)
                RETURNING id
                """,
                (cycle_uuid, session_id, target_count, request.assembly_version),
            )
            practice_set_row = cursor.fetchone()
            if not practice_set_row:
                raise RemediationUnavailable("Practice set could not be created")
            _insert_practice_set_items(cursor, practice_set_row[0], question_ids)
            cursor.execute(
                """
                UPDATE remediation_cycles
                SET status = 'practicing'
                WHERE id = %s AND student_id = %s
                  AND status IN ('recommended', 'learning', 'ready_to_reassess')
                """,
                (cycle_uuid, student_uuid),
            )
            return _load_practice_set(cursor, student_uuid, practice_set_row[0])


def mark_practice_set_complete(
    database_url: str,
    student_id: str,
    practice_set_id: str,
) -> PracticeSet:
    """Complete an owned set after its linked practice assessment is submitted."""
    student_uuid = _student_uuid(student_id)
    practice_set_uuid = _path_uuid(practice_set_id, "Practice set was not found")
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT practice_set.status, assessment_session.status::text,
                       practice_set.cycle_id
                FROM practice_sets practice_set
                JOIN remediation_cycles cycle ON cycle.id = practice_set.cycle_id
                JOIN assessment_sessions assessment_session
                  ON assessment_session.id = practice_set.assessment_session_id
                WHERE practice_set.id = %s AND cycle.student_id = %s
                FOR UPDATE OF practice_set, cycle, assessment_session
                """,
                (practice_set_uuid, student_uuid),
            )
            row = cursor.fetchone()
            if not row:
                raise RemediationNotFound("Practice set was not found")
            if row[0] == "completed":
                return _load_practice_set(cursor, student_uuid, practice_set_uuid)
            if row[0] not in {"created", "in_progress"}:
                raise RemediationConflict("Practice set cannot be completed from its current state")
            if row[1] not in {"submitted", "scoring", "scored"}:
                raise RemediationConflict(
                    "The linked practice assessment must be submitted before completion"
                )

            cursor.execute(
                """
                UPDATE practice_sets
                SET status = 'completed', completed_at = now()
                WHERE id = %s
                """,
                (practice_set_uuid,),
            )
            cursor.execute(
                """
                UPDATE remediation_cycles
                SET status = 'ready_to_reassess'
                WHERE id = %s AND student_id = %s
                  AND status IN ('practicing', 'learning', 'recommended')
                """,
                (row[2], student_uuid),
            )
            return _load_practice_set(cursor, student_uuid, practice_set_uuid)


def _load_linked_reassessment(
    cursor: Any,
    student_id: UUID,
    cycle_id: UUID,
) -> AssessmentSession | None:
    cursor.execute(
        """
        SELECT link.assessment_session_id
        FROM reassessment_links link
        JOIN assessment_sessions session
          ON session.id = link.assessment_session_id
        WHERE link.cycle_id = %s AND session.student_id = %s
        ORDER BY link.attempt_number DESC
        LIMIT 1
        """,
        (cycle_id, student_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return _load_public_session(cursor, student_id, row[0])


def get_reassessment_session(
    database_url: str,
    student_id: str,
    cycle_id: str,
) -> AssessmentSession:
    student_uuid = _student_uuid(student_id)
    cycle_uuid = _path_uuid(cycle_id, "Remediation cycle was not found")
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            session = _load_linked_reassessment(cursor, student_uuid, cycle_uuid)
            if session is None:
                raise RemediationNotFound("Reassessment session was not found")
            return session


def create_reassessment_session(
    database_url: str,
    student_id: str,
    cycle_id: str,
    payload: ReassessmentSessionCreateRequest | None = None,
) -> AssessmentSession:
    """Create or resume an unseen reassessment linked to the owned cycle."""
    student_uuid = _student_uuid(student_id)
    cycle_uuid = _path_uuid(cycle_id, "Remediation cycle was not found")
    request = payload or ReassessmentSessionCreateRequest()
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT cycle.skill_id, cycle.status::text, taxonomy.subject_id
                FROM remediation_cycles cycle
                JOIN skills skill ON skill.id = cycle.skill_id
                JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
                WHERE cycle.id = %s AND cycle.student_id = %s
                FOR UPDATE OF cycle
                """,
                (cycle_uuid, student_uuid),
            )
            cycle_row = cursor.fetchone()
            if not cycle_row:
                raise RemediationNotFound("Remediation cycle was not found")
            if cycle_row[1] in _TERMINAL_CYCLE_STATUSES:
                raise RemediationConflict("The remediation cycle is no longer active")

            existing_session = _load_linked_reassessment(cursor, student_uuid, cycle_uuid)
            if existing_session is not None:
                return existing_session

            cursor.execute(
                """
                SELECT id
                FROM practice_sets
                WHERE cycle_id = %s AND status = 'completed'
                ORDER BY completed_at DESC, id DESC
                LIMIT 1
                """,
                (cycle_uuid,),
            )
            if not cursor.fetchone():
                raise RemediationConflict(
                    "Complete the linked practice set before reassessment"
                )

            blueprint_id, blueprint_count = _approved_blueprint(
                cursor, cycle_row[2], _REASSESSMENT_PURPOSE
            )
            target_count = request.target_count or blueprint_count
            if target_count > blueprint_count:
                raise RemediationConflict(
                    "Reassessment target count exceeds the approved blueprint"
                )
            question_ids = _approved_unseen_questions(
                cursor,
                student_uuid,
                cycle_row[0],
                cycle_row[2],
                _REASSESSMENT_PURPOSE,
                target_count,
            )
            session_id = _insert_assessment_session(
                cursor, student_uuid, blueprint_id, _REASSESSMENT_PURPOSE
            )
            _insert_session_items_and_exposures(
                cursor, student_uuid, session_id, question_ids, _REASSESSMENT_PURPOSE
            )
            cursor.execute(
                """
                SELECT COALESCE(MAX(attempt_number), 0) + 1
                FROM reassessment_links
                WHERE cycle_id = %s
                """,
                (cycle_uuid,),
            )
            attempt_number = int(cursor.fetchone()[0])
            cursor.execute(
                """
                INSERT INTO reassessment_links (cycle_id, assessment_session_id, attempt_number)
                VALUES (%s, %s, %s)
                """,
                (cycle_uuid, session_id, attempt_number),
            )
            cursor.execute(
                """
                UPDATE remediation_cycles
                SET status = 'reassessing'
                WHERE id = %s AND student_id = %s
                """,
                (cycle_uuid, student_uuid),
            )
            return _load_public_session(cursor, student_uuid, session_id)


# These aliases make the intended route vocabulary easy to adopt without
# duplicating transaction logic in a future main.py integration.
create_remediation_cycle = create_or_get_remediation_cycle
create_practice_set = create_or_get_practice_set
complete_practice_set = mark_practice_set_complete
create_or_get_reassessment_session = create_reassessment_session


__all__ = [
    "AssessmentItem",
    "AssessmentSession",
    "PracticeSet",
    "PracticeSetCompleteRequest",
    "PracticeSetCreateRequest",
    "PracticeSetStatus",
    "ReassessmentSessionCreateRequest",
    "RemediationConflict",
    "RemediationCycle",
    "RemediationCycleCreateRequest",
    "RemediationError",
    "RemediationNotFound",
    "RemediationStatus",
    "RemediationUnavailable",
    "ResourceEvent",
    "ResourceEventRequest",
    "complete_practice_set",
    "create_or_get_practice_set",
    "create_or_get_reassessment_session",
    "create_or_get_remediation_cycle",
    "create_practice_set",
    "create_reassessment_session",
    "create_remediation_cycle",
    "get_practice_set",
    "get_reassessment_session",
    "get_remediation_cycle",
    "mark_practice_set_complete",
    "record_resource_event",
]
