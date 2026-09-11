import { scoreCycle } from "@/lib/act/scoring";
import type { ChoiceId, ResponseInput, Subject } from "@/lib/act/types";

const isSubject = (value: unknown): value is Subject =>
  value === "english" || value === "math";

const isChoiceId = (value: unknown): value is ChoiceId =>
  value === "A" || value === "B" || value === "C" || value === "D";

function parseResponses(value: unknown): ResponseInput[] | null {
  if (!Array.isArray(value)) return null;

  return value
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
}

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
    diagnosticResponses?: unknown;
    reassessmentResponses?: unknown;
  };
  const diagnosticResponses = parseResponses(input.diagnosticResponses);
  const reassessmentResponses = parseResponses(input.reassessmentResponses);

  if (!isSubject(input.subject) || !diagnosticResponses || !reassessmentResponses) {
    return Response.json(
      { error: "subject, diagnosticResponses, and reassessmentResponses are required" },
      { status: 400 },
    );
  }

  return Response.json(scoreCycle(input.subject, diagnosticResponses, reassessmentResponses), {
    headers: { "Cache-Control": "no-store" },
  });
}
