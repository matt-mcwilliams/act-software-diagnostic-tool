import { notFound } from "next/navigation";

import { DiagnosticPlayer } from "@/components/act/diagnostic-player";
import { PageFrame } from "@/components/act/page-frame";
import type { Subject } from "@/lib/act/types";

export default async function DiagnosticPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  if (sessionId !== "english" && sessionId !== "math") notFound();
  return <PageFrame><DiagnosticPlayer subject={sessionId as Subject} /></PageFrame>;
}
