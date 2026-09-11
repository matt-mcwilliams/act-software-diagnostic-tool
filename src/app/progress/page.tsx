import { AdaptiveProgressView } from "@/components/act/adaptive-remediation";
import { requirePilotUser } from "@/lib/supabase/guard";

export default async function ProgressPage() {
  await requirePilotUser();
  return <AdaptiveProgressView />;
}
