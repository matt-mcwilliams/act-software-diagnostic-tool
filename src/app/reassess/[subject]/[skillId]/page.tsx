import { notFound } from "next/navigation";

import { AdaptiveReassessmentView } from "@/components/act/adaptive-remediation";
import type { Subject } from "@/lib/act/types";
import { requirePilotUser } from "@/lib/supabase/guard";

export default async function ReassessmentPage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  await requirePilotUser();
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <AdaptiveReassessmentView subject={subject as Subject} skillId={skillId} />;
}
