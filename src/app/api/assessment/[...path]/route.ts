import { proxyFastApi } from "@/lib/api/client";

type RouteContext = { params: Promise<{ path: string[] }> };

function buildTargetPath(segments: string[]) {
  if (segments.length === 1 && segments[0] === "diagnostics") return "/v1/diagnostics";
  if (segments.length === 1 && segments[0] === "sessions") return "/v1/assessment-sessions";
  if (segments.length === 1 && segments[0] === "cycles") return "/v1/remediation-cycles";
  if (segments.length === 1 && segments[0] === "practice-sets") return "/v1/practice-sets";
  if (segments.length === 2 && segments[0] === "sessions") {
    return `/v1/assessment-sessions/${encodeURIComponent(segments[1])}`;
  }
  if (segments.length === 3 && segments[0] === "sessions" && ["submit", "results"].includes(segments[2])) {
    return `/v1/assessment-sessions/${encodeURIComponent(segments[1])}/${segments[2]}`;
  }
  if (
    segments.length === 4 &&
    segments[0] === "sessions" &&
    segments[2] === "responses"
  ) {
    return `/v1/assessment-sessions/${encodeURIComponent(segments[1])}/responses/${encodeURIComponent(segments[3])}`;
  }
  if (segments.length === 2 && segments[0] === "cycles") {
    return `/v1/remediation-cycles/${encodeURIComponent(segments[1])}`;
  }
  if (segments.length === 3 && segments[0] === "cycles" && ["resource-events", "practice-sets", "reassessments"].includes(segments[2])) {
    return `/v1/remediation-cycles/${encodeURIComponent(segments[1])}/${segments[2]}`;
  }
  if (segments.length === 2 && segments[0] === "practice-sets") {
    return `/v1/practice-sets/${encodeURIComponent(segments[1])}`;
  }
  if (segments.length === 3 && segments[0] === "practice-sets" && segments[2] === "complete") {
    return `/v1/practice-sets/${encodeURIComponent(segments[1])}/complete`;
  }
  return null;
}

async function handle(request: Request, context: RouteContext) {
  const { path } = await context.params;
  const targetPath = buildTargetPath(path);
  if (!targetPath) return Response.json({ error: { code: "not_found", message: "Assessment route not found." } }, { status: 404 });

  const requestUrl = new URL(request.url);
  const query = path.length === 1 && path[0] === "diagnostics" ? requestUrl.search : "";
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.text();
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const idempotencyKey = request.headers.get("idempotency-key");
  if (contentType) headers.set("content-type", contentType);
  if (idempotencyKey) headers.set("idempotency-key", idempotencyKey);
  const response = await proxyFastApi(`${targetPath}${query}`, {
    method: request.method,
    headers,
    body,
  });
  return response ?? Response.json(
    { error: { code: "not_found", message: "Assessment route not found." } },
    { status: 404 },
  );
}

export async function GET(request: Request, context: RouteContext) {
  return handle(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return handle(request, context);
}

export async function PUT(request: Request, context: RouteContext) {
  return handle(request, context);
}
