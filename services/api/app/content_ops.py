"""Reviewer-facing content and inventory readiness reports."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .content import SubjectSlug

class ContentOpsError(Exception):
    """Base class for safe content-operations errors."""


class ContentOpsUnavailable(ContentOpsError):
    """The readiness database or dependency is unavailable."""


class InventoryReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: SubjectSlug
    purpose: str = Field(pattern="^(diagnostic|practice|reassessment)$")
    blueprint_id: str
    blueprint_status: str
    item_count: int = Field(ge=1)
    approved_question_count: int = Field(ge=0)
    approved_primary_mapping_count: int = Field(ge=0)
    approved_resource_count: int = Field(ge=0)
    ready_for_assignment: bool


def _connect(database_url: str | None) -> Any:
    if not database_url:
        raise ContentOpsUnavailable("Content operations database is not configured")
    try:
        import psycopg
    except ImportError as exc:
        raise ContentOpsUnavailable("Database dependencies are unavailable") from exc
    try:
        return psycopg.connect(database_url)
    except Exception as exc:
        raise ContentOpsUnavailable("Content operations database is unavailable") from exc


def _item_count(rules: Any) -> int:
    if not isinstance(rules, dict):
        return 0
    try:
        return int(rules.get("itemCount", 0))
    except (TypeError, ValueError):
        return 0


def list_inventory_readiness(
    database_url: str | None,
    subject: SubjectSlug | None = None,
) -> list[InventoryReadiness]:
    """Return counts needed to decide whether an inventory is assignable."""

    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                params: list[Any] = []
                subject_filter = ""
                if subject:
                    subject_filter = "WHERE subject.slug = %s"
                    params.append(subject)
                cursor.execute(
                    f"""
                    SELECT subject.slug, blueprint.purpose::text, blueprint.id,
                           blueprint.status::text, blueprint.rules,
                           COUNT(DISTINCT question.id) FILTER (
                             WHERE question.status = 'approved'
                               AND question.review_status = 'approved'
                               AND source.rights_status = 'approved'
                               AND test.status = 'approved'
                           ),
                           COUNT(DISTINCT primary_mapping.question_id) FILTER (
                             WHERE question.status = 'approved'
                               AND question.review_status = 'approved'
                               AND source.rights_status = 'approved'
                               AND test.status = 'approved'
                           ),
                           COUNT(DISTINCT resource.id) FILTER (
                             WHERE resource.status = 'approved'
                           )
                    FROM assessment_blueprints blueprint
                    JOIN subjects subject ON subject.id = blueprint.subject_id
                    LEFT JOIN tests test ON test.subject_id = subject.id
                    LEFT JOIN content_sources source ON source.id = test.source_id
                    LEFT JOIN questions question ON question.source_id = source.id
                    LEFT JOIN question_skills primary_mapping
                      ON primary_mapping.question_id = question.id
                     AND primary_mapping.role = 'primary'
                    LEFT JOIN skills mapping_skill ON mapping_skill.id = primary_mapping.skill_id
                    LEFT JOIN learning_resources resource
                      ON resource.skill_id = mapping_skill.id
                    {subject_filter}
                    GROUP BY subject.slug, blueprint.purpose, blueprint.id,
                             blueprint.status, blueprint.rules
                    ORDER BY subject.slug, blueprint.purpose, blueprint.version,
                             blueprint.id
                    """,
                    params,
                )
                readiness: list[InventoryReadiness] = []
                for row in cursor.fetchall():
                    item_count = _item_count(row[4])
                    if item_count < 1:
                        raise ContentOpsUnavailable("An assessment blueprint has an invalid item count")
                    approved_question_count = int(row[5] or 0)
                    approved_mapping_count = int(row[6] or 0)
                    readiness.append(
                        InventoryReadiness(
                            subject=row[0],
                            purpose=row[1],
                            blueprint_id=str(row[2]),
                            blueprint_status=row[3],
                            item_count=item_count,
                            approved_question_count=approved_question_count,
                            approved_primary_mapping_count=approved_mapping_count,
                            approved_resource_count=int(row[7] or 0),
                            ready_for_assignment=(
                                row[3] == "approved"
                                and approved_question_count >= item_count
                                and approved_mapping_count >= item_count
                            ),
                        )
                    )
                return readiness
    except ContentOpsError:
        raise
    except Exception as exc:
        raise ContentOpsUnavailable("Inventory readiness could not be loaded") from exc


__all__ = ["ContentOpsError", "ContentOpsUnavailable", "InventoryReadiness", "list_inventory_readiness"]
