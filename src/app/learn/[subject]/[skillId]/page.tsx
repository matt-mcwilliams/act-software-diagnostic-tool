import { notFound } from "next/navigation";

import { LearnView } from "@/components/act/learn-view";
import type { Subject } from "@/lib/act/types";

export default async function LearnPage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <LearnView subject={subject as Subject} skillId={skillId} />;
}
