import { notFound } from "next/navigation";

import { PracticeView } from "@/components/act/practice-view";
import type { Subject } from "@/lib/act/types";
import { requirePilotUser } from "@/lib/supabase/guard";

export default async function PracticePage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  await requirePilotUser();
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <PracticeView subject={subject as Subject} skillId={skillId} />;
}
