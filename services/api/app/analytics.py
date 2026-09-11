"""Small, de-identified pilot export for reviewer analysis."""

from datetime import datetime, timezone
import hashlib
import hmac
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .content import SubjectSlug


class AnalyticsError(Exception):
    """Base class for safe analytics/export errors."""


class AnalyticsNotFound(AnalyticsError):
    """The requested experiment has no registered pilot cohort."""


class AnalyticsConflict(AnalyticsError):
    """The requested pilot assignment conflicts with a frozen assignment."""


class AnalyticsUnavailable(AnalyticsError):
    """The export database or pseudonym configuration is unavailable."""


class PilotExportRow(BaseModel):
    """A cohort-level row with no direct student identity."""

    pilot_id: str = Field(min_length=16, max_length=64)
    variant: str = Field(min_length=1, max_length=100)
    subject: SubjectSlug
    tutor_skill_keys: list[str] = Field(default_factory=list)
    system_skill_keys: list[str] = Field(default_factory=list)
    diagnostic_sessions: int = Field(ge=0)
    completed_reassessments: int = Field(ge=0)
    remediation_outcomes: list[str] = Field(default_factory=list)


class PilotExport(BaseModel):
    experiment_key: str = Field(min_length=1, max_length=100)
    generated_at: datetime
    rows: list[PilotExportRow] = Field(default_factory=list)


class ExperimentAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1)
    variant: str = Field(min_length=1, max_length=100)

    @field_validator("student_id", "variant")
    @classmethod
    def non_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class ExperimentAssignment(BaseModel):
    id: str
    experiment_key: str
    student_id: str
    variant: str
    assigned_at: datetime


class TutorAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1)
    subject: SubjectSlug
    skill_id: str = Field(min_length=1)
    rating: int | None = Field(default=None, ge=1, le=5)
    rank: int | None = Field(default=None, ge=1)
    confidence: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def require_assessment_value(self) -> "TutorAssessmentRequest":
        if self.rating is None and self.rank is None:
            raise ValueError("rating or rank is required")
        return self


class TutorAssessment(BaseModel):
    id: str
    student_id: str
    tutor_id: str
    subject: SubjectSlug
    skill_id: str
    rating: int | None = None
    rank: int | None = None
    confidence: int | None = None
    sealed_at: datetime


_EXPERIMENT_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def _validate_experiment_key(experiment_key: str) -> str:
    if not _EXPERIMENT_KEY.fullmatch(experiment_key):
        raise AnalyticsNotFound("Experiment was not found")
    return experiment_key


def _connect(database_url: str | None) -> Any:
    if not database_url:
        raise AnalyticsUnavailable("Analytics database is not configured")
    try:
        import psycopg
    except ImportError as exc:
        raise AnalyticsUnavailable("Database dependencies are unavailable") from exc
    try:
        return psycopg.connect(database_url)
    except Exception as exc:
        raise AnalyticsUnavailable("Analytics database is unavailable") from exc


def _student_uuid(student_id: str) -> Any:
    from uuid import UUID

    try:
        return UUID(student_id)
    except (TypeError, ValueError) as exc:
        raise AnalyticsUnavailable("The student ID is not a UUID") from exc


def _tutor_uuid(tutor_id: str) -> Any:
    from uuid import UUID

    try:
        return UUID(tutor_id)
    except (TypeError, ValueError) as exc:
        raise AnalyticsUnavailable("The tutor ID is not a UUID") from exc


def assign_experiment(
    database_url: str | None,
    experiment_key: str,
    payload: ExperimentAssignmentRequest,
) -> ExperimentAssignment:
    """Create a stable assignment or return the existing assignment."""

    valid_key = _validate_experiment_key(experiment_key)
    student_uuid = _student_uuid(payload.student_id)
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO experiment_assignments (student_id, experiment_key, variant)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (student_id, experiment_key) DO NOTHING
                    RETURNING id, experiment_key, student_id, variant, assigned_at
                    """,
                    (student_uuid, valid_key, payload.variant),
                )
                row = cursor.fetchone()
                if not row:
                    cursor.execute(
                        """
                        SELECT id, experiment_key, student_id, variant, assigned_at
                        FROM experiment_assignments
                        WHERE student_id = %s AND experiment_key = %s
                        FOR SHARE
                        """,
                        (student_uuid, valid_key),
                    )
                    row = cursor.fetchone()
                    if not row:
                        raise AnalyticsUnavailable("Experiment assignment could not be loaded")
                    if str(row[3]) != payload.variant:
                        raise AnalyticsConflict("The student already has a different experiment variant")
                return ExperimentAssignment(
                    id=str(row[0]),
                    experiment_key=str(row[1]),
                    student_id=str(row[2]),
                    variant=str(row[3]),
                    assigned_at=row[4],
                )
    except AnalyticsError:
        raise
    except Exception as exc:
        raise AnalyticsUnavailable("Experiment assignment could not be saved") from exc


def capture_tutor_assessment(
    database_url: str | None,
    tutor_id: str,
    payload: TutorAssessmentRequest,
) -> TutorAssessment:
    """Capture a sealed tutor estimate before student results are revealed."""

    tutor_uuid = _tutor_uuid(tutor_id)
    student_uuid = _student_uuid(payload.student_id)
    try:
        from uuid import UUID

        skill_uuid = UUID(payload.skill_id)
    except (TypeError, ValueError) as exc:
        raise AnalyticsNotFound("Tutor assessment skill was not found") from exc
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT skill.id, subject.slug
                    FROM skills skill
                    JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
                    JOIN subjects subject ON subject.id = taxonomy.subject_id
                    WHERE skill.id = %s AND subject.slug = %s
                    """,
                    (skill_uuid, payload.subject),
                )
                skill_row = cursor.fetchone()
                if not skill_row:
                    raise AnalyticsNotFound("Tutor assessment skill was not found")
                cursor.execute(
                    """
                    INSERT INTO tutor_skill_assessments
                      (student_id, tutor_id, subject_id, taxonomy_version_id,
                       skill_id, rating, rank, confidence, sealed_at)
                    SELECT %s, %s, subject.id, skill.taxonomy_version_id,
                           skill.id, %s, %s, %s, now()
                    FROM skills skill
                    JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
                    JOIN subjects subject ON subject.id = taxonomy.subject_id
                    WHERE skill.id = %s AND subject.slug = %s
                    RETURNING id, student_id, tutor_id, skill_id,
                              rating, rank, confidence, sealed_at
                    """,
                    (
                        student_uuid,
                        tutor_uuid,
                        payload.rating,
                        payload.rank,
                        payload.confidence,
                        skill_uuid,
                        payload.subject,
                    ),
                )
                row = cursor.fetchone()
                if not row:
                    raise AnalyticsUnavailable("Tutor assessment could not be saved")
                return TutorAssessment(
                    id=str(row[0]),
                    student_id=str(row[1]),
                    tutor_id=str(row[2]),
                    subject=payload.subject,
                    skill_id=str(row[3]),
                    rating=int(row[4]) if row[4] is not None else None,
                    rank=int(row[5]) if row[5] is not None else None,
                    confidence=int(row[6]) if row[6] is not None else None,
                    sealed_at=row[7],
                )
    except AnalyticsError:
        raise
    except Exception as exc:
        raise AnalyticsUnavailable("Tutor assessment could not be saved") from exc


def _pilot_id(student_id: Any, secret: str) -> str:
    if not secret:
        raise AnalyticsUnavailable("Export pseudonym secret is not configured")
    digest = hmac.new(
        secret.encode("utf-8"),
        str(student_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"pilot_{digest[:24]}"


def _read_rows(cursor: Any, experiment_key: str, secret: str) -> list[PilotExportRow]:
    cursor.execute(
        """
        WITH cohort AS (
          SELECT student_id, variant
          FROM experiment_assignments
          WHERE experiment_key = %s
        ), student_subjects AS (
          SELECT cohort.student_id, cohort.variant, blueprint.subject_id
          FROM cohort
          JOIN assessment_sessions session ON session.student_id = cohort.student_id
          JOIN assessment_blueprints blueprint ON blueprint.id = session.blueprint_id
          UNION
          SELECT cohort.student_id, cohort.variant, tutor.subject_id
          FROM cohort
          JOIN tutor_skill_assessments tutor ON tutor.student_id = cohort.student_id
          UNION
          SELECT cohort.student_id, cohort.variant, taxonomy.subject_id
          FROM cohort
          JOIN remediation_cycles cycle ON cycle.student_id = cohort.student_id
          JOIN skills cycle_skill ON cycle_skill.id = cycle.skill_id
          JOIN taxonomy_versions taxonomy ON taxonomy.id = cycle_skill.taxonomy_version_id
        )
        SELECT student_subject.student_id,
               student_subject.variant,
               subject.slug,
               COALESCE(
                 ARRAY_AGG(DISTINCT tutor_skill.external_key)
                   FILTER (WHERE tutor_skill.id IS NOT NULL),
                 ARRAY[]::text[]
               ) AS tutor_skill_keys,
               COALESCE(
                 ARRAY_AGG(DISTINCT system_skill.external_key)
                   FILTER (WHERE system_taxonomy.id IS NOT NULL),
                 ARRAY[]::text[]
               ) AS system_skill_keys,
               COUNT(DISTINCT diagnostic.id)
                 FILTER (WHERE diagnostic_blueprint.id IS NOT NULL) AS diagnostic_sessions,
               COUNT(DISTINCT reassessment.id)
                 FILTER (WHERE reassessment.status = 'scored'
                   AND cycle_taxonomy.id IS NOT NULL) AS completed_reassessments,
               COALESCE(
                 ARRAY_AGG(DISTINCT cycle.status::text)
                   FILTER (WHERE cycle_taxonomy.id IS NOT NULL),
                 ARRAY[]::text[]
               ) AS remediation_outcomes
        FROM student_subjects student_subject
        JOIN subjects subject ON subject.id = student_subject.subject_id
        LEFT JOIN tutor_skill_assessments tutor
          ON tutor.student_id = student_subject.student_id
         AND tutor.subject_id = student_subject.subject_id
        LEFT JOIN skills tutor_skill ON tutor_skill.id = tutor.skill_id
        LEFT JOIN assessment_sessions diagnostic
          ON diagnostic.student_id = student_subject.student_id
         AND diagnostic.purpose = 'diagnostic'
        LEFT JOIN assessment_blueprints diagnostic_blueprint
          ON diagnostic_blueprint.id = diagnostic.blueprint_id
         AND diagnostic_blueprint.subject_id = student_subject.subject_id
        LEFT JOIN recommendation_runs recommendation_run
          ON recommendation_run.student_id = student_subject.student_id
        LEFT JOIN recommendations recommendation
          ON recommendation.run_id = recommendation_run.id
         AND recommendation.status = 'current'
        LEFT JOIN skills system_skill ON system_skill.id = recommendation.skill_id
        LEFT JOIN taxonomy_versions system_taxonomy
          ON system_taxonomy.id = system_skill.taxonomy_version_id
         AND system_taxonomy.subject_id = student_subject.subject_id
        LEFT JOIN remediation_cycles cycle
          ON cycle.student_id = student_subject.student_id
        LEFT JOIN skills cycle_skill ON cycle_skill.id = cycle.skill_id
        LEFT JOIN taxonomy_versions cycle_taxonomy
          ON cycle_taxonomy.id = cycle_skill.taxonomy_version_id
         AND cycle_taxonomy.subject_id = student_subject.subject_id
        LEFT JOIN reassessment_links reassessment_link ON reassessment_link.cycle_id = cycle.id
        LEFT JOIN assessment_sessions reassessment
          ON reassessment.id = reassessment_link.assessment_session_id
         AND reassessment.purpose = 'reassessment'
        WHERE diagnostic_blueprint.id IS NOT NULL
           OR tutor.id IS NOT NULL
           OR cycle_taxonomy.id IS NOT NULL
        GROUP BY student_subject.student_id, student_subject.variant, subject.slug
        ORDER BY student_subject.variant, subject.slug, student_subject.student_id
        """,
        (experiment_key,),
    )
    return [
        PilotExportRow(
            pilot_id=_pilot_id(row[0], secret),
            variant=str(row[1]),
            subject=row[2],
            tutor_skill_keys=sorted(str(value) for value in (row[3] or [])),
            system_skill_keys=sorted(str(value) for value in (row[4] or [])),
            diagnostic_sessions=int(row[5] or 0),
            completed_reassessments=int(row[6] or 0),
            remediation_outcomes=sorted(str(value) for value in (row[7] or [])),
        )
        for row in cursor.fetchall()
    ]


def export_pilot_data(
    database_url: str | None,
    export_secret: str | None,
    experiment_key: str,
) -> PilotExport:
    """Export only de-identified cohort facts for a reviewer experiment."""

    valid_key = _validate_experiment_key(experiment_key)
    if not export_secret:
        raise AnalyticsUnavailable("Export pseudonym secret is not configured")
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                rows = _read_rows(cursor, valid_key, export_secret)
                if not rows:
                    raise AnalyticsNotFound("Experiment was not found")
                return PilotExport(
                    experiment_key=valid_key,
                    generated_at=datetime.now(timezone.utc),
                    rows=rows,
                )
    except AnalyticsError:
        raise
    except Exception as exc:
        raise AnalyticsUnavailable("Pilot export could not be generated") from exc


__all__ = [
    "AnalyticsError",
    "AnalyticsConflict",
    "AnalyticsNotFound",
    "AnalyticsUnavailable",
    "ExperimentAssignment",
    "ExperimentAssignmentRequest",
    "PilotExport",
    "PilotExportRow",
    "TutorAssessment",
    "TutorAssessmentRequest",
    "assign_experiment",
    "capture_tutor_assessment",
    "export_pilot_data",
]
