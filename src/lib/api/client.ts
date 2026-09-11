import "server-only";

export type FastApiRole = "student" | "reviewer" | "admin";

export interface FastApiCurrentUser {
  id: string;
  role: FastApiRole;
}

function getApiBaseUrl() {
  const value = process.env.ACT_API_BASE_URL?.trim();
  if (!value) return null;

  try {
    return new URL(value).toString().replace(/\/$/, "");
  } catch {
    throw new Error("ACT_API_BASE_URL must be a valid absolute URL.");
  }
}

function isCurrentUser(value: unknown): value is FastApiCurrentUser {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    (candidate.role === "student" || candidate.role === "reviewer" || candidate.role === "admin")
  );
}

export async function verifyFastApiUser(accessToken: string | undefined) {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) return null;
  if (!accessToken) throw new Error("FastAPI verification requires a Supabase access token.");

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/v1/me`, {
      headers: { authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
  } catch {
    throw new Error("The domain API could not be reached.");
  }

  if (!response.ok) {
    throw new Error("The domain API rejected the authenticated user.");
  }

  const body: unknown = await response.json().catch(() => null);
  if (!isCurrentUser(body)) {
    throw new Error("The domain API returned an invalid user response.");
  }
  return body;
}
