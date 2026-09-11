import { notFound } from "next/navigation";

import { AdaptiveLearnView } from "@/components/act/adaptive-remediation";
import type { Subject } from "@/lib/act/types";
import { requirePilotUser } from "@/lib/supabase/guard";

export default async function LearnPage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  await requirePilotUser();
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <AdaptiveLearnView subject={subject as Subject} skillId={skillId} />;
}
