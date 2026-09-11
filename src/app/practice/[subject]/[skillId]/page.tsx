import { notFound } from "next/navigation";

import { PracticeView } from "@/components/act/practice-view";
import type { Subject } from "@/lib/act/types";

export default async function PracticePage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <PracticeView subject={subject as Subject} skillId={skillId} />;
}
