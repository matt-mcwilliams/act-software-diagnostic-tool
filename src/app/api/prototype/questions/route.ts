import { getPublicQuestions } from "@/lib/act/server-content";
import type { AssessmentPurpose, Subject } from "@/lib/act/types";

const isSubject = (value: string | null): value is Subject =>
  value === "english" || value === "math";

const isPurpose = (value: string | null): value is AssessmentPurpose =>
  value === "diagnostic" || value === "practice" || value === "reassessment";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const subject = searchParams.get("subject");
  const purpose = searchParams.get("purpose");

  if (!isSubject(subject) || !isPurpose(purpose)) {
    return Response.json(
      { error: "subject and purpose must be valid prototype values" },
      { status: 400 },
    );
  }

  return Response.json(
    { subject, purpose, questions: getPublicQuestions(subject, purpose) },
    { headers: { "Cache-Control": "no-store" } },
  );
}
