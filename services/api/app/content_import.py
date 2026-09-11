from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

from .content import ImportPreview, ImportWarning, SubjectSlug, _read_export, preview_export

ImportStatus = Literal["imported", "already_imported"]


class ContentImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: SubjectSlug


class ContentImportResult(BaseModel):
    import_batch_id: str
    subject: SubjectSlug
    status: ImportStatus
    source_sha256: str
    row_counts: dict[str, int]
    warnings: list[ImportWarning]
    ready_for_assignment: bool


def _subject_name(subject: SubjectSlug) -> str:
    return "ACT English" if subject == "english" else "ACT Mathematics"


def _validate_references(data: dict[str, Any]) -> None:
    skills = data.get("skills")
    tests = data.get("tests")
    questions = data.get("questions")
    if not isinstance(skills, list) or not isinstance(tests, list) or not isinstance(questions, list):
        raise HTTPException(status_code=503, detail="Canonical content export is missing required collections")

    skill_ids = {skill.get("id") for skill in skills if isinstance(skill, dict)}
    test_keys = {test.get("testKey") for test in tests if isinstance(test, dict)}
    for question in questions:
        if not isinstance(question, dict):
            raise HTTPException(status_code=503, detail="Canonical content export contains an invalid question")
        question_key = f"{question.get('testKey')}:{question.get('questionNumber')}"
        if question.get("testKey") not in test_keys:
            raise HTTPException(status_code=503, detail="Question references an unknown test")
        if question.get("correctOption") not in {"A", "B", "C", "D"}:
            raise HTTPException(status_code=503, detail=f"Question {question_key} has an invalid answer choice")
        if any(
            not isinstance(question.get(f"option{label}"), str) or not question[f"option{label}"].strip()
            for label in ("A", "B", "C", "D")
        ):
            raise HTTPException(status_code=503, detail=f"Question {question_key} is missing an answer choice")

        referenced_skill_ids = set(question.get("skillIds") or [])
        for classification in (question.get("wrongAnswerClassifications") or {}).values():
            if isinstance(classification, dict):
                referenced_skill_ids.update(classification.get("skillIds") or [])
        if not referenced_skill_ids.issubset(skill_ids):
            raise HTTPException(status_code=503, detail=f"Question {question_key} references an unknown skill")


def _json(value: Any) -> Any:
    """Keep JSONB payload construction explicit and limited to source metadata."""
    return value if isinstance(value, (dict, list, str, int, float, bool)) or value is None else str(value)


def _get_or_insert_id(
    cursor: Any,
    insert_sql: str,
    insert_params: tuple[Any, ...],
    select_sql: str,
    select_params: tuple[Any, ...],
) -> str:
    cursor.execute(insert_sql, insert_params)
    row = cursor.fetchone()
    if row:
        return str(row[0])
    cursor.execute(select_sql, select_params)
    row = cursor.fetchone()
    if not row:
        raise RuntimeError("Content import could not resolve an inserted record")
    return str(row[0])


def _existing_batch(cursor: Any, source_sha256: str, subject: SubjectSlug) -> ContentImportResult | None:
    cursor.execute(
        """
        SELECT id, status, row_counts, warnings
        FROM import_batches
        WHERE source_sha256 = %s
        """,
        (source_sha256,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    row_counts = row[2] if isinstance(row[2], dict) else {}
    warning_values = row[3] if isinstance(row[3], list) else []
    return ContentImportResult(
        import_batch_id=str(row[0]),
        subject=subject,
        status="already_imported",
        source_sha256=source_sha256,
        row_counts=row_counts,
        warnings=[ImportWarning.model_validate(value) for value in warning_values],
        ready_for_assignment=False,
    )


def import_canonical_export(
    database_url: str,
    subject: SubjectSlug,
    created_by: str | None = None,
) -> ContentImportResult:
    data, source_sha256 = _read_export(subject)
    _validate_references(data)
    preview = preview_export(subject)

    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Database import dependencies are unavailable") from exc

    owner_id: UUID | None = None
    if created_by:
        try:
            owner_id = UUID(created_by)
        except ValueError:
            owner_id = None

    metadata = data["metadata"]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            existing = _existing_batch(cursor, source_sha256, subject)
            if existing:
                return existing

            subject_id = _get_or_insert_id(
                cursor,
                """
                INSERT INTO subjects (slug, name)
                VALUES (%s, %s)
                ON CONFLICT (slug) DO NOTHING
                RETURNING id
                """,
                (subject, _subject_name(subject)),
                "SELECT id FROM subjects WHERE slug = %s",
                (subject,),
            )
            taxonomy_version = str(metadata.get("taxonomyVersion", "unknown"))
            taxonomy_id = _get_or_insert_id(
                cursor,
                """
                INSERT INTO taxonomy_versions (subject_id, version, status, notes)
                VALUES (%s, %s, 'draft', %s)
                ON CONFLICT (subject_id, version) DO NOTHING
                RETURNING id
                """,
                (
                    subject_id,
                    taxonomy_version,
                    "Imported from canonical export; review and rights gates remain open.",
                ),
                "SELECT id FROM taxonomy_versions WHERE subject_id = %s AND version = %s",
                (subject_id, taxonomy_version),
            )

            cursor.execute(
                """
                INSERT INTO import_batches
                  (subject_id, source_path, source_sha256, schema_version, taxonomy_version,
                   status, row_counts, warnings, created_by)
                VALUES (%s, %s, %s, %s, %s, 'previewed', %s, %s, %s)
                ON CONFLICT (source_sha256) DO NOTHING
                RETURNING id
                """,
                (
                    subject_id,
                    preview.source_path,
                    source_sha256,
                    preview.schema_version,
                    taxonomy_version,
                    Jsonb(preview.row_counts),
                    Jsonb([warning.model_dump() for warning in preview.warnings]),
                    owner_id,
                ),
            )
            batch_row = cursor.fetchone()
            if not batch_row:
                existing = _existing_batch(cursor, source_sha256, subject)
                if existing:
                    return existing
                raise RuntimeError("Content import batch could not be created")
            batch_id = str(batch_row[0])

            skill_ids: dict[str, str] = {}
            for skill in data["skills"]:
                skill_id = _get_or_insert_id(
                    cursor,
                    """
                    INSERT INTO skills
                      (taxonomy_version_id, external_key, name, definition,
                       instructional_explanation, importance_weight, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'draft')
                    ON CONFLICT (taxonomy_version_id, external_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        taxonomy_id,
                        skill["id"],
                        skill["name"],
                        skill["definition"],
                        skill.get("instructionalExplanation"),
                        0.5,
                    ),
                    "SELECT id FROM skills WHERE taxonomy_version_id = %s AND external_key = %s",
                    (taxonomy_id, skill["id"]),
                )
                skill_ids[skill["id"]] = skill_id

            test_ids: dict[str, str] = {}
            passage_ids: dict[tuple[str, str], str] = {}
            for test in data["tests"]:
                test_key = test["testKey"]
                test_metadata = test.get("metadata") if isinstance(test.get("metadata"), dict) else {}
                source_name = f"{_subject_name(subject)} {test_key}"
                source_id = _get_or_insert_id(
                    cursor,
                    """
                    INSERT INTO content_sources (source_type, name, version, rights_status, metadata)
                    VALUES ('canonical_export', %s, %s, 'unreviewed', %s)
                    ON CONFLICT (source_type, name, version) DO NOTHING
                    RETURNING id
                    """,
                    (
                        source_name,
                        taxonomy_version,
                        Jsonb(
                            {
                                "sourcePath": preview.source_path,
                                "sourceSha256": source_sha256,
                                "testKey": test_key,
                                "sourceUrl": test_metadata.get("sourceUrl"),
                            }
                        ),
                    ),
                    "SELECT id FROM content_sources WHERE source_type = 'canonical_export' AND name = %s AND version = %s",
                    (source_name, taxonomy_version),
                )
                test_id = _get_or_insert_id(
                    cursor,
                    """
                    INSERT INTO tests (source_id, subject_id, external_key, title, profile, status)
                    VALUES (%s, %s, %s, %s, %s, 'draft')
                    ON CONFLICT (source_id, external_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        source_id,
                        subject_id,
                        test_key,
                        test_metadata.get("assignmentTitle") or test_key,
                        Jsonb(test_metadata),
                    ),
                    "SELECT id FROM tests WHERE source_id = %s AND external_key = %s",
                    (source_id, test_key),
                )
                test_ids[test_key] = test_id
                cursor.execute(
                    """
                    INSERT INTO sections (test_id, subject_id, section_order, status)
                    VALUES (%s, %s, 1, 'draft')
                    ON CONFLICT (test_id, section_order) DO NOTHING
                    """,
                    (test_id, subject_id),
                )
                for passage in test.get("passages") or []:
                    passage_key = passage["passageKey"]
                    passage_id = _get_or_insert_id(
                        cursor,
                        """
                        INSERT INTO passages
                          (source_id, external_key, version, title, body, metadata, status)
                        VALUES (%s, %s, 1, %s, %s, %s, 'draft')
                        ON CONFLICT (source_id, external_key, version) DO NOTHING
                        RETURNING id
                        """,
                        (
                            source_id,
                            passage_key,
                            passage.get("title"),
                            passage.get("body", ""),
                            Jsonb({"passageNumber": passage.get("passageNumber")}),
                        ),
                        "SELECT id FROM passages WHERE source_id = %s AND external_key = %s AND version = 1",
                        (source_id, passage_key),
                    )
                    passage_ids[(test_key, passage_key)] = passage_id

            for question in data["questions"]:
                test_key = question["testKey"]
                external_key = f"{test_key}:{question['questionNumber']}"
                passage_key = question.get("passageKey")
                passage_id = passage_ids.get((test_key, passage_key)) if passage_key else None
                question_id = _get_or_insert_id(
                    cursor,
                    """
                    INSERT INTO questions
                      (source_id, passage_id, external_key, version, stem, content,
                       format, status, review_status)
                    SELECT source_id, %s, %s, 1, %s, %s, 'multiple_choice', 'draft', 'pending'
                    FROM tests
                    WHERE id = %s
                    ON CONFLICT (source_id, external_key, version) DO NOTHING
                    RETURNING id
                    """,
                    (
                        passage_id,
                        external_key,
                        question["stem"],
                        Jsonb(
                            {
                                key: _json(question.get(key))
                                for key in (
                                    "stemHtml",
                                    "optionHtml",
                                    "imageUrls",
                                    "optionImageUrls",
                                    "characterStart",
                                    "characterEnd",
                                    "reportingCategory",
                                    "isScored",
                                )
                                if key in question
                            }
                        ),
                        test_ids[test_key],
                    ),
                    """
                    SELECT q.id
                    FROM questions q
                    JOIN tests t ON t.source_id = q.source_id
                    WHERE t.id = %s AND q.external_key = %s AND q.version = 1
                    """,
                    (test_ids[test_key], external_key),
                )
                choice_ids: dict[str, str] = {}
                for position, label in enumerate(("A", "B", "C", "D"), start=1):
                    choice_ids[label] = _get_or_insert_id(
                        cursor,
                        """
                        INSERT INTO answer_choices (question_id, label, position, content, is_correct)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (question_id, label) DO NOTHING
                        RETURNING id
                        """,
                        (
                            question_id,
                            label,
                            position,
                            question[f"option{label}"],
                            label == question["correctOption"],
                        ),
                        "SELECT id FROM answer_choices WHERE question_id = %s AND label = %s",
                        (question_id, label),
                    )

                for position, skill_key in enumerate(question.get("skillIds") or []):
                    cursor.execute(
                        """
                        INSERT INTO question_skills
                          (question_id, skill_id, role, evidence_weight, tag_source, tag_confidence)
                        VALUES (%s, %s, %s, %s, 'canonical_export', NULL)
                        ON CONFLICT (question_id, skill_id) DO NOTHING
                        """,
                        (
                            question_id,
                            skill_ids[skill_key],
                            "primary" if position == 0 else "secondary",
                            1.0 if position == 0 else 0.5,
                        ),
                    )
                for label, classification in (question.get("wrongAnswerClassifications") or {}).items():
                    if label not in choice_ids or not isinstance(classification, dict):
                        continue
                    for skill_key in classification.get("skillIds") or []:
                        cursor.execute(
                            """
                            INSERT INTO choice_skill_evidence
                              (answer_choice_id, skill_id, direction, evidence_weight, rationale)
                            VALUES (%s, %s, 'negative', 1, %s)
                            ON CONFLICT (answer_choice_id, skill_id) DO NOTHING
                            """,
                            (choice_ids[label], skill_ids[skill_key], classification.get("rationale")),
                        )

            cursor.execute(
                "UPDATE import_batches SET status = 'imported' WHERE id = %s",
                (batch_id,),
            )
            return ContentImportResult(
                import_batch_id=batch_id,
                subject=subject,
                status="imported",
                source_sha256=source_sha256,
                row_counts=preview.row_counts,
                warnings=preview.warnings,
                ready_for_assignment=preview.ready_for_assignment,
            )
