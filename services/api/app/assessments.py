import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .content import SubjectSlug

ChoiceId = Literal["A", "B", "C", "D"]
SessionStatus = Literal["created", "in_progress"]


class AssessmentBlueprint(BaseModel):
    id: str
    subject: SubjectSlug
    purpose: Literal["diagnostic"]
    version: str
    item_count: int = Field(ge=1)
    scoring_version: str
    mastery_model_version: str


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: SubjectSlug
    purpose: Literal["diagnostic"] = "diagnostic"


class PublicChoice(BaseModel):
    id: ChoiceId
    text: str


class AssessmentItem(BaseModel):
    id: str
    question_id: str
    position: int = Field(ge=1)
    prompt: str
    context: str | None = None
    choices: list[PublicChoice]


class AssessmentSession(BaseModel):
    id: str
    subject: SubjectSlug
    purpose: Literal["diagnostic"]
    status: SessionStatus
    items: list[AssessmentItem]


class ResponseSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice_id: ChoiceId | None = None
    client_revision: int = Field(ge=1)


class ResponseSaveResult(BaseModel):
    session_item_id: str
    client_revision: int
    saved_at: datetime


class AssessmentConflict(Exception):
    pass


class AssessmentUnavailable(Exception):
    pass


class AssessmentNotFound(Exception):
    pass


def _student_uuid(student_id: str) -> UUID:
    try:
        return UUID(student_id)
    except ValueError as exc:
        raise AssessmentUnavailable("The authenticated user ID is not a UUID") from exc


def _item_count(rules: Any) -> int:
    if not isinstance(rules, dict):
        return 0
    try:
        count = int(rules.get("itemCount", 0))
        return count if count > 0 else 0
    except (TypeError, ValueError):
        return 0


def _blueprint_from_row(row: tuple[Any, ...]) -> AssessmentBlueprint:
    return AssessmentBlueprint(
        id=str(row[0]),
        subject=row[1],
        purpose="diagnostic",
        version=str(row[3]),
        item_count=_item_count(row[4]),
        scoring_version=str(row[5]),
        mastery_model_version=str(row[6]),
    )


def list_diagnostics(database_url: str, subject: SubjectSlug | None = None) -> list[AssessmentBlueprint]:
    try:
        import psycopg
    except ImportError as exc:
        raise AssessmentUnavailable("Database dependencies are unavailable") from exc

    query = """
        SELECT ab.id, s.slug, ab.purpose::text, ab.version, ab.rules,
               ab.scoring_version, ab.mastery_model_version
        FROM assessment_blueprints ab
        JOIN subjects s ON s.id = ab.subject_id
        WHERE ab.purpose = 'diagnostic'
          AND ab.status = 'approved'
          AND s.active = true
    """
    params: list[Any] = []
    if subject:
        query += " AND s.slug = %s"
        params.append(subject)
    query += " ORDER BY s.slug, ab.version"

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return [_blueprint_from_row(row) for row in cursor.fetchall()]


def _load_session(cursor: Any, student_id: UUID, session_id: str) -> AssessmentSession:
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise AssessmentNotFound("Assessment session was not found") from exc
    cursor.execute(
        """
        SELECT session.id, subject.slug, session.purpose::text, session.status::text
        FROM assessment_sessions session
        JOIN assessment_blueprints blueprint ON blueprint.id = session.blueprint_id
        JOIN subjects subject ON subject.id = blueprint.subject_id
        WHERE session.id = %s AND session.student_id = %s
        """,
        (session_uuid, student_id),
    )
    session_row = cursor.fetchone()
    if not session_row:
        raise AssessmentNotFound("Assessment session was not found")

    cursor.execute(
        """
        SELECT item.id, item.question_id, item.position, question.stem, passage.body
        FROM assessment_session_items item
        JOIN questions question ON question.id = item.question_id
        LEFT JOIN passages passage ON passage.id = question.passage_id
        WHERE item.session_id = %s
        ORDER BY item.position
        """,
        (session_uuid,),
    )
    item_rows = cursor.fetchall()
    question_ids = [row[1] for row in item_rows]
    choices_by_question: dict[str, list[PublicChoice]] = {str(question_id): [] for question_id in question_ids}
    if question_ids:
        cursor.execute(
            """
            SELECT question_id, label, content
            FROM answer_choices
            WHERE question_id = ANY(%s)
            ORDER BY question_id, position
            """,
            (question_ids,),
        )
        for question_id, label, content in cursor.fetchall():
            if label in {"A", "B", "C", "D"}:
                choices_by_question[str(question_id)].append(PublicChoice(id=label, text=content))

    return AssessmentSession(
        id=str(session_row[0]),
        subject=session_row[1],
        purpose="diagnostic",
        status=session_row[3],
        items=[
            AssessmentItem(
                id=str(row[0]),
                question_id=str(row[1]),
                position=row[2],
                prompt=row[3],
                context=row[4],
                choices=choices_by_question[str(row[1])],
            )
            for row in item_rows
        ],
    )


def create_or_resume_session(database_url: str, student_id: str, payload: SessionCreateRequest) -> AssessmentSession:
    try:
        import psycopg
    except ImportError as exc:
        raise AssessmentUnavailable("Database dependencies are unavailable") from exc

    student_uuid = _student_uuid(student_id)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ab.id, s.slug, ab.purpose::text, ab.version, ab.rules,
                       ab.scoring_version, ab.mastery_model_version, s.id
                FROM assessment_blueprints ab
                JOIN subjects s ON s.id = ab.subject_id
                WHERE s.slug = %s AND ab.purpose = 'diagnostic' AND ab.status = 'approved'
                ORDER BY ab.version DESC
                LIMIT 1
                """,
                (payload.subject,),
            )
            blueprint_row = cursor.fetchone()
            if not blueprint_row:
                raise AssessmentUnavailable("No approved diagnostic blueprint is available")
            item_count = _item_count(blueprint_row[4])
            if not item_count:
                raise AssessmentUnavailable("Diagnostic blueprint has no valid item count")

            cursor.execute(
                """
                SELECT id
                FROM assessment_sessions
                WHERE student_id = %s AND blueprint_id = %s
                  AND status IN ('created', 'in_progress')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (student_uuid, blueprint_row[0]),
            )
            existing_row = cursor.fetchone()
            if existing_row:
                return _load_session(cursor, student_uuid, str(existing_row[0]))

            cursor.execute(
                """
                SELECT DISTINCT question.id
                FROM questions question
                JOIN tests test ON test.source_id = question.source_id
                JOIN question_skills question_skill ON question_skill.question_id = question.id
                  AND question_skill.role = 'primary'
                WHERE question.source_id IN (
                  SELECT source.id
                  FROM content_sources source
                  WHERE source.rights_status = 'approved'
                )
                  AND question.status = 'approved'
                  AND question.review_status = 'approved'
                  AND test.subject_id = %s
                  AND NOT EXISTS (
                    SELECT 1
                    FROM item_exposures exposure
                    WHERE exposure.student_id = %s
                      AND exposure.question_id = question.id
                  )
                ORDER BY question.id
                LIMIT %s
                """,
                (blueprint_row[7], student_uuid, item_count),
            )
            question_rows = cursor.fetchall()
            if len(question_rows) < item_count:
                raise AssessmentUnavailable("Approved diagnostic inventory is insufficient")

            cursor.execute(
                """
                INSERT INTO assessment_sessions
                  (student_id, blueprint_id, purpose, status, started_at)
                VALUES (%s, %s, 'diagnostic', 'in_progress', now())
                ON CONFLICT (student_id, blueprint_id)
                  WHERE status IN ('created', 'in_progress')
                DO NOTHING
                RETURNING id
                """,
                (student_uuid, blueprint_row[0]),
            )
            session_row = cursor.fetchone()
            if not session_row:
                cursor.execute(
                    """
                    SELECT id
                    FROM assessment_sessions
                    WHERE student_id = %s AND blueprint_id = %s
                      AND status IN ('created', 'in_progress')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (student_uuid, blueprint_row[0]),
                )
                session_row = cursor.fetchone()
            if not session_row:
                raise AssessmentUnavailable("Assessment session could not be created")

            for position, question_row in enumerate(question_rows, start=1):
                cursor.execute(
                    """
                    INSERT INTO assessment_session_items (session_id, question_id, position)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (session_id, question_id) DO NOTHING
                    """,
                    (session_row[0], question_row[0], position),
                )
                cursor.execute(
                    """
                    INSERT INTO item_exposures (student_id, question_id, session_id, purpose)
                    VALUES (%s, %s, %s, 'diagnostic')
                    ON CONFLICT (student_id, question_id, purpose) DO NOTHING
                    """,
                    (student_uuid, question_row[0], session_row[0]),
                )
            return _load_session(cursor, student_uuid, str(session_row[0]))


def load_session(database_url: str, student_id: str, session_id: str) -> AssessmentSession:
    try:
        import psycopg
    except ImportError as exc:
        raise AssessmentUnavailable("Database dependencies are unavailable") from exc

    student_uuid = _student_uuid(student_id)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            return _load_session(cursor, student_uuid, session_id)


def _request_hash(session_id: str, item_id: str, payload: ResponseSaveRequest) -> str:
    encoded = json.dumps(
        {
            "sessionId": session_id,
            "itemId": item_id,
            "choiceId": payload.choice_id,
            "clientRevision": payload.client_revision,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def save_response(
    database_url: str,
    student_id: str,
    session_id: str,
    item_id: str,
    payload: ResponseSaveRequest,
    idempotency_key: str,
) -> ResponseSaveResult:
    if not idempotency_key.strip() or len(idempotency_key) > 255:
        raise AssessmentConflict("An Idempotency-Key header is required")
    student_uuid = _student_uuid(student_id)
    try:
        session_uuid = UUID(session_id)
        item_uuid = UUID(item_id)
    except ValueError as exc:
        raise AssessmentNotFound("Assessment item was not found") from exc
    request_hash = _request_hash(session_id, item_id, payload)

    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise AssessmentUnavailable("Database dependencies are unavailable") from exc

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            scope = f"assessment-response:{session_id}:{item_id}"
            cursor.execute(
                """
                SELECT request_hash, status, response_status, response_body
                FROM idempotency_keys
                WHERE owner_id = %s AND scope = %s AND key = %s
                FOR UPDATE
                """,
                (student_uuid, scope, idempotency_key),
            )
            idempotency_row = cursor.fetchone()
            if idempotency_row:
                if idempotency_row[0] != request_hash:
                    raise AssessmentConflict("Idempotency-Key was reused for a different request")
                if idempotency_row[1] == "completed" and isinstance(idempotency_row[3], dict):
                    return ResponseSaveResult.model_validate(idempotency_row[3])
            else:
                cursor.execute(
                    """
                    INSERT INTO idempotency_keys (owner_id, scope, key, request_hash)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (owner_id, scope, key) DO NOTHING
                    """,
                    (student_uuid, scope, idempotency_key, request_hash),
                )
                cursor.execute(
                    """
                    SELECT request_hash, status, response_status, response_body
                    FROM idempotency_keys
                    WHERE owner_id = %s AND scope = %s AND key = %s
                    FOR UPDATE
                    """,
                    (student_uuid, scope, idempotency_key),
                )
                idempotency_row = cursor.fetchone()
                if not idempotency_row or idempotency_row[0] != request_hash:
                    raise AssessmentConflict("Idempotency-Key was reused for a different request")
                if idempotency_row[1] == "completed" and isinstance(idempotency_row[3], dict):
                    return ResponseSaveResult.model_validate(idempotency_row[3])

            cursor.execute(
                """
                SELECT item.question_id, response.id, response.client_revision
                FROM assessment_session_items item
                JOIN assessment_sessions session ON session.id = item.session_id
                LEFT JOIN responses response ON response.session_item_id = item.id
                WHERE item.id = %s AND item.session_id = %s
                  AND session.student_id = %s
                  AND session.status IN ('created', 'in_progress')
                FOR UPDATE OF item, session, response
                """,
                (item_uuid, session_uuid, student_uuid),
            )
            item_row = cursor.fetchone()
            if not item_row:
                raise AssessmentNotFound("Assessment item was not found")
            current_revision = item_row[2] or 0
            if payload.client_revision <= current_revision:
                raise AssessmentConflict("Response revision is stale")

            choice_uuid = None
            if payload.choice_id is not None:
                cursor.execute(
                    """
                    SELECT id
                    FROM answer_choices
                    WHERE question_id = %s AND label = %s
                    """,
                    (item_row[0], payload.choice_id),
                )
                choice_row = cursor.fetchone()
                if not choice_row:
                    raise AssessmentConflict("Response choice is not assigned to this item")
                choice_uuid = choice_row[0]

            saved_at = datetime.now(timezone.utc)
            cursor.execute(
                """
                INSERT INTO responses
                  (session_item_id, student_id, answer_choice_id, is_omitted,
                   client_revision, answered_at, saved_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_item_id)
                DO UPDATE SET answer_choice_id = EXCLUDED.answer_choice_id,
                              is_omitted = EXCLUDED.is_omitted,
                              client_revision = EXCLUDED.client_revision,
                              answered_at = EXCLUDED.answered_at,
                              saved_at = EXCLUDED.saved_at
                RETURNING id
                """,
                (
                    item_uuid,
                    student_uuid,
                    choice_uuid,
                    payload.choice_id is None,
                    payload.client_revision,
                    saved_at if payload.choice_id is not None else None,
                    saved_at,
                ),
            )
            response_row = cursor.fetchone()
            if not response_row:
                raise AssessmentUnavailable("Response could not be saved")
            cursor.execute(
                """
                INSERT INTO response_events (response_id, event_type, payload)
                VALUES (%s, 'response_saved', %s)
                """,
                (response_row[0], Jsonb({"clientRevision": payload.client_revision})),
            )
            result = ResponseSaveResult(
                session_item_id=item_id,
                client_revision=payload.client_revision,
                saved_at=saved_at,
            )
            cursor.execute(
                """
                UPDATE idempotency_keys
                SET status = 'completed', response_status = 200,
                    response_body = %s, completed_at = now()
                WHERE owner_id = %s AND scope = %s AND key = %s
                """,
                (Jsonb(result.model_dump(mode="json")), student_uuid, scope, idempotency_key),
            )
            return result
