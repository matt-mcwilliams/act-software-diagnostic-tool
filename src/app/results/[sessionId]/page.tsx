import { notFound } from "next/navigation";

import { ResultsView } from "@/components/act/results-view";
import type { Subject } from "@/lib/act/types";

export default async function ResultsPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  if (sessionId !== "english" && sessionId !== "math") notFound();
  return <ResultsView subject={sessionId as Subject} />;
}
