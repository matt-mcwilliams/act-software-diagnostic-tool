"""Small, de-identified pilot export for reviewer analysis."""

from datetime import datetime, timezone
import hashlib
import hmac
import re
from typing import Any

from pydantic import BaseModel, Field

from .content import SubjectSlug


class AnalyticsError(Exception):
    """Base class for safe analytics/export errors."""


class AnalyticsNotFound(AnalyticsError):
    """The requested experiment has no registered pilot cohort."""


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
    "AnalyticsNotFound",
    "AnalyticsUnavailable",
    "PilotExport",
    "PilotExportRow",
    "export_pilot_data",
]
