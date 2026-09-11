"""Authenticated issue reporting for student-visible pilot content.

Reports are deliberately small and durable.  Before inserting a report, the
target is checked against the authenticated student's owned sessions/cycles or
exposures so the endpoint cannot be used to discover another student's data.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

IssueEntityType = Literal["diagnosis", "question", "resource", "explanation"]
IssueStatus = Literal["open", "in_review", "resolved", "dismissed"]


class IssueError(Exception):
    """Base class for safe issue-reporting errors."""


class IssueNotFound(IssueError):
    """The report target is absent or not visible to the reporter."""


class IssueUnavailable(IssueError):
    """The issue-reporting dependency is unavailable."""


class IssueReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: IssueEntityType
    entity_id: UUID
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("category", "description")
    @classmethod
    def non_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class IssueReport(BaseModel):
    id: str
    entity_type: IssueEntityType
    entity_id: str | None
    category: str
    description: str
    status: IssueStatus
    created_at: datetime


class IssueResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["resolved", "dismissed"]
    resolution: str = Field(min_length=1, max_length=2000)

    @field_validator("resolution")
    @classmethod
    def non_blank_resolution(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("resolution must not be blank")
        return value


def _student_uuid(student_id: str) -> UUID:
    try:
        return UUID(student_id)
    except (TypeError, ValueError) as exc:
        raise IssueUnavailable("The authenticated user ID is not a UUID") from exc


def _connect(database_url: str | None) -> Any:
    if not database_url:
        raise IssueUnavailable("Issue reporting database is not configured")
    try:
        import psycopg
    except ImportError as exc:
        raise IssueUnavailable("Database dependencies are unavailable") from exc
    try:
        return psycopg.connect(database_url)
    except Exception as exc:
        raise IssueUnavailable("Issue reporting database is unavailable") from exc


def _target_is_visible(cursor: Any, reporter_id: UUID, payload: IssueReportRequest) -> bool:
    if payload.entity_type == "diagnosis":
        cursor.execute(
            """
            SELECT 1
            FROM assessment_sessions
            WHERE id = %s AND student_id = %s
            UNION ALL
            SELECT 1
            FROM remediation_cycles
            WHERE id = %s AND student_id = %s
            LIMIT 1
            """,
            (payload.entity_id, reporter_id, payload.entity_id, reporter_id),
        )
    elif payload.entity_type in {"question", "explanation"}:
        cursor.execute(
            """
            SELECT 1
            FROM item_exposures exposure
            JOIN assessment_sessions session
              ON session.id = exposure.assessment_session_id
            WHERE exposure.question_id = %s
              AND session.student_id = %s
            LIMIT 1
            """,
            (payload.entity_id, reporter_id),
        )
    else:
        cursor.execute(
            """
            SELECT 1
            FROM learning_resources resource
            JOIN remediation_cycles cycle ON cycle.skill_id = resource.skill_id
            WHERE resource.id = %s
              AND cycle.student_id = %s
              AND resource.status = 'approved'
            LIMIT 1
            """,
            (payload.entity_id, reporter_id),
        )
    return cursor.fetchone() is not None


def create_issue_report(
    database_url: str | None,
    reporter_id: str,
    payload: IssueReportRequest,
) -> IssueReport:
    """Create a report only for an entity visible to the authenticated student."""

    reporter_uuid = _student_uuid(reporter_id)
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                if not _target_is_visible(cursor, reporter_uuid, payload):
                    raise IssueNotFound("Issue report target was not found")
                cursor.execute(
                    """
                    INSERT INTO issue_reports
                      (reporter_id, entity_type, entity_id, category, description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, entity_type, entity_id, category, description,
                              status, created_at
                    """,
                    (
                        reporter_uuid,
                        payload.entity_type,
                        payload.entity_id,
                        payload.category,
                        payload.description,
                    ),
                )
                row = cursor.fetchone()
                if not row:
                    raise IssueUnavailable("Issue report could not be created")
                return IssueReport(
                    id=str(row[0]),
                    entity_type=row[1],
                    entity_id=str(row[2]) if row[2] else None,
                    category=str(row[3]),
                    description=str(row[4]),
                    status=row[5],
                    created_at=row[6],
                )
    except IssueError:
        raise
    except Exception as exc:
        raise IssueUnavailable("Issue report could not be saved") from exc


def _issue_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise IssueNotFound("Issue report was not found") from exc


def list_issue_reports(
    database_url: str | None,
    status: IssueStatus | None = None,
) -> list[IssueReport]:
    """List report metadata for reviewers without exposing reporter identity."""

    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                if status:
                    cursor.execute(
                        """
                        SELECT id, entity_type, entity_id, category, description,
                               status, created_at
                        FROM issue_reports
                        WHERE status = %s
                        ORDER BY created_at DESC, id DESC
                        """,
                        (status,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, entity_type, entity_id, category, description,
                               status, created_at
                        FROM issue_reports
                        ORDER BY created_at DESC, id DESC
                        """
                    )
                return [
                    IssueReport(
                        id=str(row[0]),
                        entity_type=row[1],
                        entity_id=str(row[2]) if row[2] else None,
                        category=str(row[3]),
                        description=str(row[4]),
                        status=row[5],
                        created_at=row[6],
                    )
                    for row in cursor.fetchall()
                ]
    except IssueError:
        raise
    except Exception as exc:
        raise IssueUnavailable("Issue reports could not be loaded") from exc


def resolve_issue_report(
    database_url: str | None,
    issue_id: str,
    payload: IssueResolutionRequest,
) -> IssueReport:
    """Resolve or dismiss one report with an explicit reviewer decision."""

    report_uuid = _issue_uuid(issue_id)
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE issue_reports
                    SET status = %s, resolution = %s, resolved_at = now()
                    WHERE id = %s
                    RETURNING id, entity_type, entity_id, category, description,
                              status, created_at
                    """,
                    (payload.status, payload.resolution, report_uuid),
                )
                row = cursor.fetchone()
                if not row:
                    raise IssueNotFound("Issue report was not found")
                return IssueReport(
                    id=str(row[0]),
                    entity_type=row[1],
                    entity_id=str(row[2]) if row[2] else None,
                    category=str(row[3]),
                    description=str(row[4]),
                    status=row[5],
                    created_at=row[6],
                )
    except IssueError:
        raise
    except Exception as exc:
        raise IssueUnavailable("Issue report could not be updated") from exc


__all__ = [
    "IssueEntityType",
    "IssueError",
    "IssueNotFound",
    "IssueReport",
    "IssueReportRequest",
    "IssueResolutionRequest",
    "IssueStatus",
    "IssueUnavailable",
    "create_issue_report",
    "list_issue_reports",
    "resolve_issue_report",
]
