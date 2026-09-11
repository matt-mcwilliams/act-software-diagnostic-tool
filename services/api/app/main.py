import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from .auth import CurrentUser, get_current_user, require_reviewer
from .assessments import (
    AssessmentConflict,
    AssessmentNotFound,
    AssessmentResult,
    AssessmentSession,
    AssessmentUnavailable,
    AssessmentBlueprint,
    ResponseSaveRequest,
    ResponseSaveResult,
    SessionCreateRequest,
    create_or_resume_session,
    get_session_result,
    load_session,
    list_diagnostics,
    save_response,
    submit_session,
)
from .content import ImportPreview, ImportPreviewRequest, SubjectSlug, preview_requested_exports
from .content_import import ContentImportRequest, ContentImportResult, import_canonical_export
from .errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from .remediation import (
    PracticeSet,
    PracticeSetCreateRequest,
    RemediationConflict,
    RemediationCycle,
    RemediationCycleCreateRequest,
    RemediationError,
    RemediationNotFound,
    RemediationUnavailable,
    ReassessmentSessionCreateRequest,
    ResourceEvent,
    ResourceEventRequest,
    complete_practice_set,
    create_practice_set,
    create_reassessment_session,
    create_remediation_cycle,
    get_practice_set,
    get_reassessment_session,
    get_remediation_cycle,
    record_resource_event,
)
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


@app.post(
    "/v1/internal/imports",
    response_model=ContentImportResult,
    tags=["internal-content"],
)
async def import_content(
    payload: ContentImportRequest,
    user: CurrentUser = Depends(require_reviewer),
) -> ContentImportResult:
    """Import canonical content as draft/pending-review rows."""
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    return await run_in_threadpool(import_canonical_export, database_url, payload.subject, user.id)


@app.get(
    "/v1/diagnostics",
    response_model=list[AssessmentBlueprint],
    tags=["assessments"],
)
async def diagnostics(
    subject: SubjectSlug | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> list[AssessmentBlueprint]:
    del user
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    try:
        return await run_in_threadpool(list_diagnostics, database_url, subject)
    except AssessmentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/v1/assessment-sessions",
    response_model=AssessmentSession,
    tags=["assessments"],
)
async def start_assessment_session(
    payload: SessionCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> AssessmentSession:
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    try:
        return await run_in_threadpool(create_or_resume_session, database_url, user.id, payload)
    except AssessmentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    "/v1/assessment-sessions/{session_id}",
    response_model=AssessmentSession,
    tags=["assessments"],
)
async def get_assessment_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> AssessmentSession:
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    try:
        return await run_in_threadpool(load_session, database_url, user.id, session_id)
    except AssessmentNotFound as exc:
        raise HTTPException(status_code=404, detail="Assessment session was not found") from exc
    except AssessmentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.put(
    "/v1/assessment-sessions/{session_id}/responses/{session_item_id}",
    response_model=ResponseSaveResult,
    tags=["assessments"],
)
async def save_assessment_response(
    session_id: str,
    session_item_id: str,
    payload: ResponseSaveRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: CurrentUser = Depends(get_current_user),
) -> ResponseSaveResult:
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    try:
        return await run_in_threadpool(
            save_response,
            database_url,
            user.id,
            session_id,
            session_item_id,
            payload,
            idempotency_key or "",
        )
    except AssessmentConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AssessmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AssessmentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/v1/assessment-sessions/{session_id}/submit",
    response_model=AssessmentResult,
    tags=["assessments"],
)
async def submit_assessment_session(
    session_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: CurrentUser = Depends(get_current_user),
) -> AssessmentResult:
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    try:
        return await run_in_threadpool(
            submit_session,
            database_url,
            user.id,
            session_id,
            idempotency_key or "",
        )
    except AssessmentConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AssessmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AssessmentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    "/v1/assessment-sessions/{session_id}/results",
    response_model=AssessmentResult,
    tags=["assessments"],
)
async def assessment_session_results(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> AssessmentResult:
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    try:
        return await run_in_threadpool(get_session_result, database_url, user.id, session_id)
    except AssessmentNotFound as exc:
        raise HTTPException(status_code=404, detail="Assessment results were not found") from exc
    except AssessmentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _remediation_database_url() -> str:
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=503, detail="API database is not configured")
    return database_url


def _remediation_http_error(exc: RemediationError) -> HTTPException:
    if isinstance(exc, RemediationNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, RemediationConflict):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=503, detail=str(exc))


@app.post(
    "/v1/remediation-cycles",
    response_model=RemediationCycle,
    tags=["remediation"],
)
async def start_remediation_cycle(
    payload: RemediationCycleCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> RemediationCycle:
    try:
        return await run_in_threadpool(
            create_remediation_cycle,
            _remediation_database_url(),
            user.id,
            payload,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc


@app.get(
    "/v1/remediation-cycles/{cycle_id}",
    response_model=RemediationCycle,
    tags=["remediation"],
)
async def remediation_cycle(
    cycle_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> RemediationCycle:
    try:
        return await run_in_threadpool(
            get_remediation_cycle,
            _remediation_database_url(),
            user.id,
            cycle_id,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc


@app.post(
    "/v1/remediation-cycles/{cycle_id}/resource-events",
    response_model=ResourceEvent,
    tags=["remediation"],
)
async def remediation_resource_event(
    cycle_id: str,
    payload: ResourceEventRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ResourceEvent:
    try:
        return await run_in_threadpool(
            record_resource_event,
            _remediation_database_url(),
            user.id,
            cycle_id,
            payload,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc


@app.post(
    "/v1/remediation-cycles/{cycle_id}/practice-sets",
    response_model=PracticeSet,
    tags=["remediation"],
)
async def remediation_practice_set(
    cycle_id: str,
    payload: PracticeSetCreateRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> PracticeSet:
    try:
        return await run_in_threadpool(
            create_practice_set,
            _remediation_database_url(),
            user.id,
            cycle_id,
            payload,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc


@app.get(
    "/v1/practice-sets/{practice_set_id}",
    response_model=PracticeSet,
    tags=["remediation"],
)
async def practice_set(
    practice_set_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> PracticeSet:
    try:
        return await run_in_threadpool(
            get_practice_set,
            _remediation_database_url(),
            user.id,
            practice_set_id,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc


@app.post(
    "/v1/practice-sets/{practice_set_id}/complete",
    response_model=PracticeSet,
    tags=["remediation"],
)
async def finish_practice_set(
    practice_set_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> PracticeSet:
    try:
        return await run_in_threadpool(
            complete_practice_set,
            _remediation_database_url(),
            user.id,
            practice_set_id,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc


@app.post(
    "/v1/remediation-cycles/{cycle_id}/reassessments",
    response_model=AssessmentSession,
    tags=["remediation"],
)
async def remediation_reassessment(
    cycle_id: str,
    payload: ReassessmentSessionCreateRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> AssessmentSession:
    try:
        return await run_in_threadpool(
            create_reassessment_session,
            _remediation_database_url(),
            user.id,
            cycle_id,
            payload,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc


@app.get(
    "/v1/remediation-cycles/{cycle_id}/reassessments",
    response_model=AssessmentSession,
    tags=["remediation"],
)
async def current_reassessment(
    cycle_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> AssessmentSession:
    try:
        return await run_in_threadpool(
            get_reassessment_session,
            _remediation_database_url(),
            user.id,
            cycle_id,
        )
    except RemediationError as exc:
        raise _remediation_http_error(exc) from exc
