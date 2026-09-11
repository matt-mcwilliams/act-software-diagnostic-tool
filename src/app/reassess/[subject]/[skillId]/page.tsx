import { notFound } from "next/navigation";

import { ReassessmentView } from "@/components/act/reassessment-view";
import type { Subject } from "@/lib/act/types";

export default async function ReassessmentPage({ params }: { params: Promise<{ subject: string; skillId: string }> }) {
  const { subject, skillId } = await params;
  if (subject !== "english" && subject !== "math") notFound();
  return <ReassessmentView subject={subject as Subject} skillId={skillId} />;
}
