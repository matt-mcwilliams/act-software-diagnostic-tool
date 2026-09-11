import { getQuestion } from "@/lib/act/server-content";
import type { ChoiceId } from "@/lib/act/types";

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

  const input = body as { questionId?: unknown; choiceId?: unknown };
  if (typeof input.questionId !== "string" || !isChoiceId(input.choiceId)) {
    return Response.json({ error: "questionId and a valid choiceId are required" }, { status: 400 });
  }

  const question = getQuestion(input.questionId);
  if (!question || question.purpose !== "practice") {
    return Response.json({ error: "Only approved practice items can be checked here" }, { status: 404 });
  }

  const failureMode = question.failureModeByChoice?.[input.choiceId];
  return Response.json({
    correct: input.choiceId === question.correctChoiceId,
    correctChoiceId: question.correctChoiceId,
    explanation: question.explanation,
    failureMode,
  });
}
