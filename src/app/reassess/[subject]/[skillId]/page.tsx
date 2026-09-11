import { notFound } from "next/navigation";

import { ReassessmentView } from "@/components/act/reassessment-view";
import type { Subject } from "@/lib/act/types";
import { requirePilotUser } from "@/lib/supabase/guard";

export default async function ReassessmentPage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  await requirePilotUser();
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <ReassessmentView subject={subject as Subject} skillId={skillId} />;
}
