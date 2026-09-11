import { notFound } from "next/navigation";

import { AdaptivePracticeView } from "@/components/act/adaptive-remediation";
import type { Subject } from "@/lib/act/types";
import { requirePilotUser } from "@/lib/supabase/guard";

export default async function PracticePage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  await requirePilotUser();
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <AdaptivePracticeView subject={subject as Subject} skillId={skillId} />;
}
