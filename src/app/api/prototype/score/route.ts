import { scoreAssessment } from "@/lib/act/scoring";
import type { AssessmentPurpose, ChoiceId, ResponseInput, Subject } from "@/lib/act/types";

const isSubject = (value: unknown): value is Subject =>
  value === "english" || value === "math";

const isPurpose = (value: unknown): value is AssessmentPurpose =>
  value === "diagnostic" || value === "practice" || value === "reassessment";

const isChoiceId = (value: unknown): value is ChoiceId =>
  value === "A" || value === "B" || value === "C" || value === "D";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Request body must be valid JSON" }, { status: 400 });
  }

  if (!body || typeof body !== "object") {
    return Response.json({ error: "Request body must be an object" }, { status: 400 });
  }

  const input = body as {
    subject?: unknown;
    purpose?: unknown;
    responses?: unknown;
  };

  if (!isSubject(input.subject) || !isPurpose(input.purpose) || !Array.isArray(input.responses)) {
    return Response.json(
      { error: "subject, purpose, and responses are required" },
      { status: 400 },
    );
  }

  const responses: ResponseInput[] = input.responses
    .filter((response): response is { questionId: string; choiceId: unknown } => {
      return (
        Boolean(response) &&
        typeof response === "object" &&
        "questionId" in response &&
        typeof response.questionId === "string" &&
        "choiceId" in response
      );
    })
    .map((response) => ({
      questionId: response.questionId,
      choiceId: response.choiceId === null ? null : isChoiceId(response.choiceId) ? response.choiceId : null,
    }));

  return Response.json(scoreAssessment(input.subject, input.purpose, responses), {
    headers: { "Cache-Control": "no-store" },
  });
}
