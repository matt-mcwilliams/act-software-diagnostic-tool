"""Read-only progress and history queries for the authenticated student.

This module intentionally does not register FastAPI routes.  Route handlers can
call the functions here in a thread pool and map :class:`ProgressNotFound` to
404 and :class:`ProgressUnavailable` to 503.  Every query is scoped by the
authenticated student's UUID; a missing or cross-student resource is reported
as not found so that the API does not reveal ownership information.

The queries only read mastery, recommendation, and remediation tables.  They
never select assessment choices, response correctness, explanations, or any
other answer-key data.
"""

from datetime import datetime
from typing import Any, Callable, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from .assessments import SessionStatus
from .content import SubjectSlug
from .mastery import MasterySnapshot, Recommendation
from .remediation import PracticeSetStatus, RemediationCycle


class ProgressError(Exception):
    """Base class for safe progress errors exposed by route handlers."""


class ProgressNotFound(ProgressError):
    """A resource is absent or is owned by another student."""


class ProgressUnavailable(ProgressError):
    """The progress database or its Python dependency is unavailable."""


class MasterySnapshotRecord(MasterySnapshot):
    """A reusable mastery snapshot with its immutable database identity/time."""

    id: str
    calculated_at: datetime


class RecommendationRecord(Recommendation):
    """A reusable recommendation with identity and current-run metadata."""

    id: str
    status: str = "current"
    created_at: datetime


class MasteryOverview(BaseModel):
    """The latest snapshot per skill and latest current recommendation per skill."""

    subject: SubjectSlug | None = None
    snapshots: list[MasterySnapshotRecord] = Field(default_factory=list)
    recommendations: list[RecommendationRecord] = Field(default_factory=list)


class MasteryHistory(BaseModel):
    """Chronological snapshots for one skill owned by the authenticated student."""

    subject: SubjectSlug
    skill_id: str
    skill_key: str
    skill_name: str
    snapshots: list[MasterySnapshotRecord] = Field(default_factory=list)


class RemediationCycleSummary(RemediationCycle):
    """A progress-card view of a cycle without question or answer details."""

    resource_count: int = Field(ge=0)
    practice_set_status: PracticeSetStatus | None = None
    reassessment_status: SessionStatus | None = None


_T = TypeVar("_T")
_SUBJECTS = frozenset(("english", "math"))


def _student_uuid(student_id: str) -> UUID:
    try:
        return UUID(student_id)
    except (TypeError, ValueError) as exc:
        raise ProgressUnavailable("The authenticated user ID is not a UUID") from exc


def _path_uuid(value: str, message: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise ProgressNotFound(message) from exc


def _subject_filter(subject: SubjectSlug | None) -> tuple[str, list[Any]]:
    if subject is None:
        return "", []
    if subject not in _SUBJECTS:
        raise ProgressNotFound("Subject was not found")
    return " AND subject.slug = %s", [subject]


def _connect(database_url: str | None) -> Any:
    if not database_url:
        raise ProgressUnavailable("Progress database is not configured")
    try:
        import psycopg
    except ImportError as exc:
        raise ProgressUnavailable("Database dependencies are unavailable") from exc
    try:
        return psycopg.connect(database_url)
    except Exception as exc:
        raise ProgressUnavailable("Progress database is unavailable") from exc


def _read(database_url: str | None, reader: Callable[[Any], _T]) -> _T:
    """Run one read-only cursor operation and normalize DB failures."""

    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                return reader(cursor)
    except ProgressError:
        raise
    except Exception as exc:
        raise ProgressUnavailable("Progress data is unavailable") from exc


def _snapshot_reason(classification: str, correct_count: int, incorrect_count: int) -> str:
    if classification == "insufficient_evidence":
        return "There are not yet enough scored responses to make a dependable call."
    response_count = correct_count + incorrect_count
    suffix = "" if response_count == 1 else "s"
    return f"Based on {correct_count} correct and {incorrect_count} incorrect scored response{suffix}."


def _snapshot_from_row(row: tuple[Any, ...]) -> MasterySnapshotRecord:
    classification = str(row[11])
    correct_count = int(row[8])
    incorrect_count = int(row[9])
    return MasterySnapshotRecord(
        id=str(row[0]),
        skill_id=str(row[1]),
        skill_key=str(row[2]),
        skill_name=str(row[3]),
        mean=float(row[4]),
        lower_bound=float(row[5]),
        upper_bound=float(row[6]),
        effective_evidence=float(row[7]),
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        omitted_count=int(row[10]),
        classification=classification,
        reason=_snapshot_reason(classification, correct_count, incorrect_count),
        model_version=str(row[12]),
        calculated_at=row[13],
    )


def _recommendation_from_row(row: tuple[Any, ...]) -> RecommendationRecord:
    return RecommendationRecord(
        id=str(row[0]),
        skill_id=str(row[1]),
        skill_key=str(row[2]),
        skill_name=str(row[3]),
        rank=int(row[4]),
        priority_score=float(row[5]),
        weakness_score=float(row[6]),
        importance_score=float(row[7]),
        confidence_score=float(row[8]),
        readiness=bool(row[9]),
        explanation=str(row[10]),
        formula_version=str(row[11]),
        status=str(row[12]),
        created_at=row[13],
    )


def _read_mastery(
    cursor: Any,
    student_uuid: UUID,
    subject: SubjectSlug | None,
) -> MasteryOverview:
    subject_sql, subject_params = _subject_filter(subject)
    cursor.execute(
        f"""
        SELECT current.id, current.skill_id, current.skill_key, current.skill_name,
               current.mean, current.lower_bound, current.upper_bound,
               current.effective_evidence, current.correct_count,
               current.incorrect_count, current.omitted_count, current.classification,
               current.model_version, current.calculated_at
        FROM (
          SELECT DISTINCT ON (snapshot.skill_id)
                 snapshot.id, snapshot.skill_id, skill.external_key AS skill_key,
                 skill.name AS skill_name, snapshot.mean, snapshot.lower_bound,
                 snapshot.upper_bound, snapshot.effective_evidence,
                 snapshot.correct_count, snapshot.incorrect_count,
                 snapshot.omitted_count, snapshot.classification,
                 snapshot.model_version, snapshot.calculated_at
          FROM mastery_snapshots snapshot
          JOIN skills skill ON skill.id = snapshot.skill_id
          JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
          JOIN subjects subject ON subject.id = taxonomy.subject_id
          WHERE snapshot.student_id = %s{subject_sql}
          ORDER BY snapshot.skill_id, snapshot.calculated_at DESC, snapshot.id DESC
        ) current
        ORDER BY current.skill_key, current.id
        """,
        [student_uuid, *subject_params],
    )
    snapshots = [_snapshot_from_row(row) for row in cursor.fetchall()]

    cursor.execute(
        f"""
        SELECT current.id, current.skill_id, current.skill_key, current.skill_name,
               current.rank, current.priority_score, current.weakness_score,
               current.importance_score, current.confidence_score, current.readiness,
               current.explanation, current.formula_version, current.status,
               current.created_at
        FROM (
          SELECT DISTINCT ON (recommendation.skill_id)
                 recommendation.id, recommendation.skill_id,
                 skill.external_key AS skill_key, skill.name AS skill_name,
                 recommendation.rank, recommendation.priority_score,
                 recommendation.weakness_score, recommendation.importance_score,
                 recommendation.confidence_score, recommendation.readiness,
                 recommendation.explanation, run.formula_version,
                 recommendation.status, run.created_at
          FROM recommendations recommendation
          JOIN recommendation_runs run ON run.id = recommendation.run_id
          JOIN skills skill ON skill.id = recommendation.skill_id
          JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
          JOIN subjects subject ON subject.id = taxonomy.subject_id
          WHERE run.student_id = %s
            AND recommendation.status = 'current'{subject_sql}
          ORDER BY recommendation.skill_id, run.created_at DESC,
                   run.id DESC, recommendation.rank, recommendation.id DESC
        ) current
        ORDER BY current.rank, current.skill_key, current.id
        """,
        [student_uuid, *subject_params],
    )
    recommendations = [_recommendation_from_row(row) for row in cursor.fetchall()]
    return MasteryOverview(
        subject=subject,
        snapshots=snapshots,
        recommendations=recommendations,
    )


def list_mastery(
    database_url: str | None,
    student_id: str,
    subject: SubjectSlug | None = None,
) -> MasteryOverview:
    """Return current mastery and recommendations for the authenticated student."""

    student_uuid = _student_uuid(student_id)
    return _read(database_url, lambda cursor: _read_mastery(cursor, student_uuid, subject))


def _read_mastery_history(cursor: Any, student_uuid: UUID, skill_uuid: UUID) -> MasteryHistory:
    cursor.execute(
        """
        SELECT snapshot.id, snapshot.skill_id, skill.external_key, skill.name,
               snapshot.mean, snapshot.lower_bound, snapshot.upper_bound,
               snapshot.effective_evidence, snapshot.correct_count,
               snapshot.incorrect_count, snapshot.omitted_count,
               snapshot.classification, snapshot.model_version,
               snapshot.calculated_at, subject.slug
        FROM mastery_snapshots snapshot
        JOIN skills skill ON skill.id = snapshot.skill_id
        JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
        JOIN subjects subject ON subject.id = taxonomy.subject_id
        WHERE snapshot.student_id = %s AND snapshot.skill_id = %s
        ORDER BY snapshot.calculated_at ASC, snapshot.id ASC
        """,
        (student_uuid, skill_uuid),
    )
    rows = cursor.fetchall()
    if not rows:
        raise ProgressNotFound("Mastery history was not found")
    snapshots = [
        _snapshot_from_row(
            (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10],
                row[11],
                row[12],
                row[13],
            )
        )
        for row in rows
    ]
    return MasteryHistory(
        subject=rows[0][14],
        skill_id=str(rows[0][1]),
        skill_key=str(rows[0][2]),
        skill_name=str(rows[0][3]),
        snapshots=snapshots,
    )


def get_mastery_history(
    database_url: str | None,
    student_id: str,
    skill_id: str,
) -> MasteryHistory:
    """Return chronological history only when the skill has student-owned data."""

    student_uuid = _student_uuid(student_id)
    skill_uuid = _path_uuid(skill_id, "Mastery history was not found")
    return _read(
        database_url,
        lambda cursor: _read_mastery_history(cursor, student_uuid, skill_uuid),
    )


def _read_remediation_cycles(
    cursor: Any,
    student_uuid: UUID,
    subject: SubjectSlug | None,
) -> list[RemediationCycleSummary]:
    subject_sql, subject_params = _subject_filter(subject)
    cursor.execute(
        f"""
        SELECT cycle.id, cycle.skill_id, skill.external_key, skill.name,
               cycle.recommendation_id, cycle.status::text,
               cycle.baseline_snapshot_id, cycle.attempt_number,
               cycle.started_at, cycle.completed_at, subject.slug,
               resources.resource_count, practice.id, practice.status,
               practice.assessment_session_id, reassessment.assessment_session_id,
               reassessment.status
        FROM remediation_cycles cycle
        JOIN skills skill ON skill.id = cycle.skill_id
        JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
        JOIN subjects subject ON subject.id = taxonomy.subject_id
        LEFT JOIN LATERAL (
          SELECT COUNT(*)::int AS resource_count
          FROM learning_resources resource
          WHERE resource.skill_id = cycle.skill_id
            AND resource.status = 'approved'
        ) resources ON TRUE
        LEFT JOIN LATERAL (
          SELECT practice_set.id, practice_set.status::text,
                 practice_set.assessment_session_id
          FROM practice_sets practice_set
          WHERE practice_set.cycle_id = cycle.id
          ORDER BY practice_set.created_at DESC, practice_set.id DESC
          LIMIT 1
        ) practice ON TRUE
        LEFT JOIN LATERAL (
          SELECT link.assessment_session_id, session.status::text AS status
          FROM reassessment_links link
          JOIN assessment_sessions session
            ON session.id = link.assessment_session_id
          WHERE link.cycle_id = cycle.id
            AND session.student_id = cycle.student_id
          ORDER BY link.attempt_number DESC, link.assessment_session_id DESC
          LIMIT 1
        ) reassessment ON TRUE
        WHERE cycle.student_id = %s{subject_sql}
        ORDER BY COALESCE(cycle.completed_at, cycle.started_at) DESC NULLS LAST,
                 cycle.id DESC
        """,
        [student_uuid, *subject_params],
    )
    return [
        RemediationCycleSummary(
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
            resources=[],
            practice_set_id=str(row[12]) if row[12] else None,
            practice_session_id=str(row[14]) if row[14] else None,
            reassessment_session_id=str(row[15]) if row[15] else None,
            resource_count=int(row[11] or 0),
            practice_set_status=row[13] if row[13] else None,
            reassessment_status=row[16] if row[16] else None,
        )
        for row in cursor.fetchall()
    ]


def list_remediation_cycles(
    database_url: str | None,
    student_id: str,
    subject: SubjectSlug | None = None,
) -> list[RemediationCycleSummary]:
    """List all remediation cycles belonging to the authenticated student."""

    student_uuid = _student_uuid(student_id)
    return _read(
        database_url,
        lambda cursor: _read_remediation_cycles(cursor, student_uuid, subject),
    )


__all__ = [
    "MasteryHistory",
    "MasteryOverview",
    "MasterySnapshotRecord",
    "ProgressError",
    "ProgressNotFound",
    "ProgressUnavailable",
    "RecommendationRecord",
    "RemediationCycleSummary",
    "get_mastery_history",
    "list_mastery",
    "list_remediation_cycles",
]
