import "server-only";

import { getOptionalSupabaseConfig } from "@/lib/supabase/env";

import { createClient } from "@/lib/supabase/server";

export type FastApiRole = "student" | "reviewer" | "admin";

export interface FastApiCurrentUser {
  id: string;
  role: FastApiRole;
}

export function getFastApiBaseUrl() {
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
  const baseUrl = getFastApiBaseUrl();
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

function errorResponse(status: number, message: string) {
  return Response.json(
    { error: { code: status === 401 ? "unauthorized" : "api_unavailable", message } },
    { status, headers: { "cache-control": "no-store" } },
  );
}

export async function proxyFastApi(path: string, init: RequestInit = {}) {
  const baseUrl = getFastApiBaseUrl();
  if (!baseUrl) return null;
  if (!getOptionalSupabaseConfig()) return errorResponse(401, "Authentication is required.");

  const supabase = await createClient();
  const { data: userData } = await supabase.auth.getUser();
  if (!userData.user) return errorResponse(401, "Authentication is required.");
  const { data: sessionData } = await supabase.auth.getSession();
  if (!sessionData.session?.access_token) return errorResponse(401, "Authentication is required.");

  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${sessionData.session.access_token}`);
  if (init.body && !headers.has("content-type")) headers.set("content-type", "application/json");

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    return errorResponse(503, "The domain API could not be reached.");
  }

  const responseHeaders = new Headers();
  const contentType = response.headers.get("content-type");
  const requestId = response.headers.get("x-request-id");
  const retryAfter = response.headers.get("retry-after");
  const rateLimit = response.headers.get("x-ratelimit-limit");
  if (contentType) responseHeaders.set("content-type", contentType);
  if (requestId) responseHeaders.set("x-request-id", requestId);
  if (retryAfter) responseHeaders.set("retry-after", retryAfter);
  if (rateLimit) responseHeaders.set("x-ratelimit-limit", rateLimit);
  responseHeaders.set("cache-control", "no-store");
  return new Response(await response.text(), {
    status: response.status,
    headers: responseHeaders,
  });
}
