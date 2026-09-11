import { getFastApiBaseUrl } from "@/lib/api/client";

export const dynamic = "force-dynamic";

export function GET() {
  return Response.json(
    { mode: getFastApiBaseUrl() ? "fastapi" : "local" },
    { headers: { "cache-control": "no-store" } },
  );
}
