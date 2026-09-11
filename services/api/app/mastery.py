from math import sqrt
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

MASTERY_MODEL_VERSION = "beta-binomial-v1"
PRIORITY_FORMULA_VERSION = "priority-v1"
PRIOR_ALPHA = 2.0
PRIOR_BETA = 2.0
TARGET_MASTERY = 0.75


class MasterySnapshot(BaseModel):
    skill_id: str
    skill_key: str
    skill_name: str
    mean: float
    lower_bound: float
    upper_bound: float
    effective_evidence: float
    correct_count: int = Field(ge=0)
    incorrect_count: int = Field(ge=0)
    omitted_count: int = Field(ge=0)
    classification: str
    reason: str
    model_version: str


class Recommendation(BaseModel):
    skill_id: str
    skill_key: str
    skill_name: str
    rank: int = Field(ge=1)
    priority_score: float = Field(ge=0)
    weakness_score: float = Field(ge=0)
    importance_score: float = Field(ge=0)
    confidence_score: float = Field(ge=0)
    readiness: bool
    explanation: str
    formula_version: str


def _classify(mean: float, upper_bound: float, lower_bound: float, confidence: float, evidence: float) -> str:
    if evidence < 2:
        return "insufficient_evidence"
    if mean >= 0.78 and lower_bound >= 0.62 and confidence >= 0.7:
        return "strong_evidence_of_mastery"
    if mean >= 0.68 and confidence >= 0.55:
        return "likely_mastered"
    if mean <= 0.34 and upper_bound <= 0.5 and confidence >= 0.7:
        return "strong_evidence_of_weakness"
    if mean <= 0.52 and confidence >= 0.55:
        return "likely_weak"
    return "developing"


def calculate_snapshot(
    skill_id: str,
    skill_key: str,
    skill_name: str,
    positive_weight: float,
    negative_weight: float,
    correct_count: int,
    incorrect_count: int,
    omitted_count: int,
    model_version: str = MASTERY_MODEL_VERSION,
) -> MasterySnapshot:
    effective_evidence = positive_weight + negative_weight
    alpha = PRIOR_ALPHA + positive_weight
    beta = PRIOR_BETA + negative_weight
    mean = alpha / (alpha + beta)
    confidence = effective_evidence / (effective_evidence + 2)
    interval_radius = min(0.32, 0.42 / sqrt(effective_evidence + 1))
    lower_bound = max(0.0, mean - interval_radius)
    upper_bound = min(1.0, mean + interval_radius)
    classification = _classify(mean, upper_bound, lower_bound, confidence, effective_evidence)
    reason = (
        "There are not yet enough scored responses to make a dependable call."
        if classification == "insufficient_evidence"
        else f"Based on {correct_count} correct and {incorrect_count} incorrect scored response"
        f"{'s' if correct_count + incorrect_count != 1 else ''}."
    )
    return MasterySnapshot(
        skill_id=skill_id,
        skill_key=skill_key,
        skill_name=skill_name,
        mean=mean,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        effective_evidence=effective_evidence,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        omitted_count=omitted_count,
        classification=classification,
        reason=reason,
        model_version=model_version,
    )


def _upsert_evidence(
    cursor: Any,
    evidence_by_response: dict[str, dict[str, dict[str, Any]]],
    model_version: str,
    source_purpose: str,
) -> None:
    from psycopg.types.json import Jsonb

    for response_id, evidence_by_skill in evidence_by_response.items():
        for skill_id, evidence in evidence_by_skill.items():
            cursor.execute(
                """
                INSERT INTO mastery_evidence
                  (student_id, skill_id, response_id, direction, weight,
                   source_purpose, model_version, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (response_id, skill_id, model_version) DO NOTHING
                """,
                (
                    evidence["student_id"],
                    UUID(skill_id),
                    UUID(response_id),
                    evidence["direction"],
                    evidence["weight"],
                    source_purpose,
                    model_version,
                    Jsonb(evidence["details"]),
                ),
            )


def calculate_and_persist_mastery(
    cursor: Any,
    student_id: UUID,
    subject: str,
    session_id: UUID,
    model_version: str = MASTERY_MODEL_VERSION,
    source_purpose: str = "diagnostic",
) -> tuple[list[MasterySnapshot], list[Recommendation]]:
    from psycopg.types.json import Jsonb

    cursor.execute(
        """
        SELECT skill.id, skill.external_key, skill.name, skill.importance_weight
        FROM skills skill
        JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
        JOIN subjects subject ON subject.id = taxonomy.subject_id
        WHERE subject.slug = %s AND skill.status = 'approved'
        ORDER BY skill.external_key
        """,
        (subject,),
    )
    skill_rows = cursor.fetchall()
    if not skill_rows:
        return [], []

    skill_ids = [row[0] for row in skill_rows]
    skill_by_id = {str(row[0]): row for row in skill_rows}
    cursor.execute(
        """
        SELECT question_id, skill_id, evidence_weight
        FROM question_skills
        WHERE skill_id = ANY(%s)
        """,
        (skill_ids,),
    )
    question_skills: dict[str, list[tuple[str, float]]] = {}
    for question_id, skill_id, evidence_weight in cursor.fetchall():
        question_skills.setdefault(str(question_id), []).append((str(skill_id), float(evidence_weight)))

    cursor.execute(
        """
        SELECT item.question_id, response.id, response.answer_choice_id,
               response.is_omitted, (selected.id = correct_choice.id)
        FROM assessment_session_items item
        JOIN responses response ON response.session_item_id = item.id
        LEFT JOIN answer_choices selected ON selected.id = response.answer_choice_id
        JOIN answer_choices correct_choice
          ON correct_choice.question_id = item.question_id
         AND correct_choice.is_correct = true
        WHERE item.session_id = %s
        """,
        (session_id,),
    )
    response_rows = cursor.fetchall()
    selected_choice_ids = [row[2] for row in response_rows if row[2] is not None]
    choice_evidence: dict[str, list[tuple[str, str, float, str | None]]] = {}
    if selected_choice_ids:
        cursor.execute(
            """
            SELECT answer_choice_id, skill_id, direction::text, evidence_weight, rationale
            FROM choice_skill_evidence
            WHERE answer_choice_id = ANY(%s)
            """,
            (selected_choice_ids,),
        )
        for choice_id, skill_id, direction, weight, rationale in cursor.fetchall():
            choice_evidence.setdefault(str(choice_id), []).append(
                (str(skill_id), direction, float(weight), rationale)
            )

    evidence_by_response: dict[str, dict[str, dict[str, Any]]] = {}
    for question_id, response_id, choice_id, is_omitted, is_correct in response_rows:
        response_evidence: dict[str, dict[str, Any]] = {}
        if is_omitted:
            for skill_id, _ in question_skills.get(str(question_id), []):
                if skill_id in skill_by_id:
                    response_evidence[skill_id] = {
                        "student_id": student_id,
                        "direction": "omitted",
                        "weight": 0,
                        "details": {"source": "question_skill"},
                    }
        else:
            direction = "positive" if is_correct else "negative"
            for skill_id, weight in question_skills.get(str(question_id), []):
                if skill_id in skill_by_id:
                    response_evidence[skill_id] = {
                        "student_id": student_id,
                        "direction": direction,
                        "weight": weight,
                        "details": {"source": "question_skill"},
                    }
            if not is_correct and choice_id is not None:
                for skill_id, choice_direction, weight, rationale in choice_evidence.get(str(choice_id), []):
                    if skill_id not in skill_by_id or choice_direction == "omitted":
                        continue
                    existing = response_evidence.get(skill_id)
                    response_evidence[skill_id] = {
                        "student_id": student_id,
                        "direction": choice_direction,
                        "weight": max(existing["weight"] if existing else 0, weight * 1.15),
                        "details": {
                            "source": "choice_skill_evidence",
                            **({"rationale": rationale} if rationale else {}),
                        },
                    }
        if response_evidence:
            evidence_by_response[str(response_id)] = response_evidence

    _upsert_evidence(cursor, evidence_by_response, model_version, source_purpose)
    cursor.execute(
        """
        SELECT evidence.skill_id, evidence.direction::text, evidence.weight
        FROM mastery_evidence evidence
        JOIN skills skill ON skill.id = evidence.skill_id
        JOIN taxonomy_versions taxonomy ON taxonomy.id = skill.taxonomy_version_id
        JOIN subjects subject ON subject.id = taxonomy.subject_id
        WHERE evidence.student_id = %s
          AND subject.slug = %s
          AND evidence.model_version = %s
        """,
        (student_id, subject, model_version),
    )
    totals: dict[str, dict[str, Any]] = {}
    for skill_id, direction, weight in cursor.fetchall():
        total = totals.setdefault(
            str(skill_id),
            {"positive": 0.0, "negative": 0.0, "correct": 0, "incorrect": 0, "omitted": 0},
        )
        if direction == "positive":
            total["positive"] += float(weight)
            total["correct"] += 1
        elif direction == "negative":
            total["negative"] += float(weight)
            total["incorrect"] += 1
        else:
            total["omitted"] += 1

    snapshots: list[MasterySnapshot] = []
    snapshot_ids: dict[str, str] = {}
    for row in skill_rows:
        skill_id = str(row[0])
        total = totals.get(skill_id, {"positive": 0.0, "negative": 0.0, "correct": 0, "incorrect": 0, "omitted": 0})
        snapshot = calculate_snapshot(
            skill_id,
            str(row[1]),
            str(row[2]),
            total["positive"],
            total["negative"],
            total["correct"],
            total["incorrect"],
            total["omitted"],
            model_version,
        )
        snapshots.append(snapshot)
        cursor.execute(
            """
            INSERT INTO mastery_snapshots
              (student_id, skill_id, mean, lower_bound, upper_bound, effective_evidence,
               correct_count, incorrect_count, omitted_count, classification, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                student_id,
                row[0],
                snapshot.mean,
                snapshot.lower_bound,
                snapshot.upper_bound,
                snapshot.effective_evidence,
                snapshot.correct_count,
                snapshot.incorrect_count,
                snapshot.omitted_count,
                snapshot.classification,
                model_version,
            ),
        )
        snapshot_ids[skill_id] = str(cursor.fetchone()[0])

    cursor.execute(
        """
        SELECT skill.id,
               EXISTS (
                 SELECT 1 FROM learning_resources resource
                 WHERE resource.skill_id = skill.id AND resource.status = 'approved'
               )
               AND EXISTS (
                 SELECT 1
                 FROM question_skills question_skill
                 JOIN questions question ON question.id = question_skill.question_id
                 JOIN content_sources source ON source.id = question.source_id
                 WHERE question_skill.skill_id = skill.id
                   AND question.status = 'approved'
                   AND question.review_status = 'approved'
                   AND source.rights_status = 'approved'
               ) AS ready
        FROM skills skill
        WHERE skill.id = ANY(%s)
        """,
        (skill_ids,),
    )
    readiness = {str(skill_id): bool(ready) for skill_id, ready in cursor.fetchall()}
    cursor.execute(
        """
        INSERT INTO recommendation_runs (student_id, trigger_session_id, formula_version, inputs)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (
            student_id,
            session_id,
            PRIORITY_FORMULA_VERSION,
            Jsonb({"masteryModelVersion": model_version, "snapshotCount": len(snapshots)}),
        ),
    )
    recommendation_run_id = cursor.fetchone()[0]
    recommendations: list[Recommendation] = []
    ranked: list[tuple[float, str, Recommendation]] = []
    for snapshot in snapshots:
        importance = float(skill_by_id[snapshot.skill_id][3])
        confidence = min(1.0, snapshot.effective_evidence / (snapshot.effective_evidence + 2))
        weakness = max(0.0, (TARGET_MASTERY - snapshot.mean) / TARGET_MASTERY)
        ready = readiness.get(snapshot.skill_id, False)
        priority = weakness * importance * confidence * (1 if ready else 0)
        explanation = (
            f"{snapshot.skill_name} is prioritized from the observed response pattern and its learning path."
            if ready
            else f"{snapshot.skill_name} is visible for review, but the current inventory does not have a complete approved learning path."
        )
        recommendation = Recommendation(
            skill_id=snapshot.skill_id,
            skill_key=snapshot.skill_key,
            skill_name=snapshot.skill_name,
            rank=0,
            priority_score=priority,
            weakness_score=weakness,
            importance_score=importance,
            confidence_score=confidence,
            readiness=ready,
            explanation=explanation,
            formula_version=PRIORITY_FORMULA_VERSION,
        )
        ranked.append((priority, snapshot.skill_key, recommendation))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    for rank, (_, _, recommendation) in enumerate(ranked, start=1):
        recommendation = recommendation.model_copy(update={"rank": rank})
        recommendations.append(recommendation)
        cursor.execute(
            """
            INSERT INTO recommendations
              (run_id, skill_id, rank, priority_score, weakness_score, importance_score,
               confidence_score, readiness, explanation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                recommendation_run_id,
                UUID(recommendation.skill_id),
                recommendation.rank,
                recommendation.priority_score,
                recommendation.weakness_score,
                recommendation.importance_score,
                recommendation.confidence_score,
                recommendation.readiness,
                recommendation.explanation,
            ),
        )
    return snapshots, recommendations
