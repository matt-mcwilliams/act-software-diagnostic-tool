import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .auth import CurrentUser, get_current_user, require_reviewer
from .content import ImportPreview, ImportPreviewRequest, preview_requested_exports
from .errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from .settings import get_settings

logger = logging.getLogger("act_adaptive_api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("api_started environment=%s", settings.environment)
    yield
    logger.info("api_stopped")


app = FastAPI(
    title="ACT Adaptive API",
    version="0.1.0",
    description="Domain API boundary for the ACT adaptive learning pilot.",
    lifespan=lifespan,
)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/healthz", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["operations"])
async def readiness() -> JSONResponse:
    settings = get_settings()
    database_status = "configured" if settings.database_url else "not_configured"
    return JSONResponse(
        {"status": "ready", "database": database_status},
        headers={"cache-control": "no-store"},
    )


@app.get("/v1/me", tags=["identity"])
async def current_user(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    return {"id": user.id, "role": user.role}


@app.post(
    "/v1/internal/imports/preview",
    response_model=list[ImportPreview],
    tags=["internal-content"],
)
async def preview_content_import(
    payload: ImportPreviewRequest,
    _: CurrentUser = Depends(require_reviewer),
) -> list[ImportPreview]:
    """Validate canonical exports without writing content or returning item text."""
    return preview_requested_exports(payload.subject)
