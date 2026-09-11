import { ProgressView } from "@/components/act/progress-view";
import { requirePilotUser } from "@/lib/supabase/guard";

export default async function ProgressPage() {
  await requirePilotUser();
  return <ProgressView />;
}
