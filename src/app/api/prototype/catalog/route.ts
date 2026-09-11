import { getSkills } from "@/lib/act/server-content";
import type { Subject } from "@/lib/act/types";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const subjectParam = searchParams.get("subject");
  const subject =
    subjectParam === "english" || subjectParam === "math"
      ? (subjectParam as Subject)
      : undefined;

  return Response.json(
    { skills: getSkills(subject) },
    { headers: { "Cache-Control": "no-store" } },
  );
}
