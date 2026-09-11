import { redirect } from "next/navigation";

import { verifyFastApiUser } from "@/lib/api/client";

import { getOptionalSupabaseConfig } from "./env";
import { createClient } from "./server";

/**
 * Auth is optional only for the local prototype. Once public Supabase config
 * exists, every student page uses the server-side session before rendering.
 */
export async function requirePilotUser() {
  if (!getOptionalSupabaseConfig()) return null;

  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/sign-in");

  if (process.env.ACT_API_BASE_URL) {
    const { data: sessionData } = await supabase.auth.getSession();
    await verifyFastApiUser(sessionData.session?.access_token);
  }

  return data.user;
}
