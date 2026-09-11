import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

SubjectSlug = Literal["english", "math"]

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_EXPORT_PATHS: dict[SubjectSlug, Path] = {
    "english": _REPOSITORY_ROOT / "content/exports/master-output-english.json",
    "math": _REPOSITORY_ROOT / "content/exports/master-output-math.json",
}


class ImportPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: SubjectSlug | None = None


class ImportWarning(BaseModel):
    code: str
    count: int = Field(ge=1)


class ImportPreview(BaseModel):
    subject: SubjectSlug
    source_path: str
    source_sha256: str
    schema_version: str
    taxonomy_version: str
    generated_at: str | None
    row_counts: dict[str, int]
    warnings: list[ImportWarning]
    ready_for_assignment: bool


def _read_export(subject: SubjectSlug) -> tuple[dict[str, Any], str]:
    path = _EXPORT_PATHS[subject]
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Canonical content export is unavailable") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="Canonical content export is invalid") from exc

    if not isinstance(data, dict):
        raise HTTPException(status_code=503, detail="Canonical content export has an invalid shape")
    return data, hashlib.sha256(raw).hexdigest()


def _count_question_skill_mappings(questions: list[dict[str, Any]]) -> int:
    total = 0
    for question in questions:
        skill_ids = set(question.get("skillIds") or [])
        for classification in (question.get("wrongAnswerClassifications") or {}).values():
            if isinstance(classification, dict):
                skill_ids.update(classification.get("skillIds") or [])
        total += len(skill_ids)
    return total


def _count_choice_evidence(questions: list[dict[str, Any]]) -> int:
    return sum(len(question.get("wrongAnswerClassifications") or {}) for question in questions)


def preview_export(subject: SubjectSlug) -> ImportPreview:
    data, source_sha256 = _read_export(subject)
    metadata = data.get("metadata")
    skills = data.get("skills")
    tests = data.get("tests")
    questions = data.get("questions")
    if not isinstance(metadata, dict) or not all(
        isinstance(value, list) for value in (skills, tests, questions)
    ):
        raise HTTPException(status_code=503, detail="Canonical content export is missing required collections")

    questions_without_primary_skill = sum(
        1 for question in questions if not (question.get("skillIds") or [])
    )
    unreviewed_choice_evidence = sum(
        1
        for question in questions
        for classification in (question.get("wrongAnswerClassifications") or {}).values()
        if isinstance(classification, dict) and classification.get("reviewStatus") != "reviewed"
    )
    source_metadata = [
        test.get("metadata")
        for test in tests
        if isinstance(test, dict) and isinstance(test.get("metadata"), dict)
    ]
    rights_review_required = sum(
        1 for value in source_metadata if value.get("rightsStatus") != "approved"
    )
    passages = sum(
        len(test.get("passages") or [])
        for test in tests
        if isinstance(test, dict) and isinstance(test.get("passages") or [], list)
    )

    warnings = [
        ImportWarning(code="primary_skill_mapping_required", count=questions_without_primary_skill),
        ImportWarning(code="rights_status_requires_review", count=rights_review_required),
    ]
    if unreviewed_choice_evidence:
        warnings.append(ImportWarning(code="choice_evidence_requires_review", count=unreviewed_choice_evidence))

    return ImportPreview(
        subject=subject,
        source_path=str(_EXPORT_PATHS[subject].relative_to(_REPOSITORY_ROOT)),
        source_sha256=source_sha256,
        schema_version=str(metadata.get("schemaVersion", "unknown")),
        taxonomy_version=str(metadata.get("taxonomyVersion", "unknown")),
        generated_at=metadata.get("generatedAt") if isinstance(metadata.get("generatedAt"), str) else None,
        row_counts={
            "subjects": 1,
            "taxonomy_versions": 1,
            "skills": len(skills),
            "content_sources": len(tests),
            "tests": len(tests),
            "passages": passages,
            "questions": len(questions),
            "answer_choices": len(questions) * 4,
            "question_skills": _count_question_skill_mappings(questions),
            "choice_skill_evidence": _count_choice_evidence(questions),
        },
        warnings=[warning for warning in warnings if warning.count > 0],
        ready_for_assignment=not questions_without_primary_skill
        and not unreviewed_choice_evidence
        and rights_review_required == 0,
    )


def preview_requested_exports(subject: SubjectSlug | None) -> list[ImportPreview]:
    subjects = [subject] if subject else list(_EXPORT_PATHS)
    return [preview_export(current_subject) for current_subject in subjects]
