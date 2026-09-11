from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_TEST_TOKEN = "prototype-test-token"


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str


def _claims_to_user(claims: dict[str, Any]) -> CurrentUser:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Authentication subject is missing")
    role_claim = claims.get("role", "student")
    role = role_claim if isinstance(role_claim, str) else "student"
    return CurrentUser(id=subject, role=role)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="A bearer token is required")

    if settings.allow_test_user and credentials.credentials == _TEST_TOKEN:
        return CurrentUser(id="test-user", role="student")

    if not settings.auth_jwt_secret:
        raise HTTPException(status_code=503, detail="Authentication is not configured")

    decode_options = {"require": ["exp", "sub"]}
    decode_kwargs: dict[str, Any] = {
        "key": settings.auth_jwt_secret,
        "algorithms": ["HS256"],
        "audience": settings.auth_jwt_audience,
        "options": decode_options,
    }
    if settings.auth_jwt_issuer:
        decode_kwargs["issuer"] = settings.auth_jwt_issuer

    try:
        claims = jwt.decode(credentials.credentials, **decode_kwargs)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Bearer token is invalid or expired") from exc

    return _claims_to_user(claims)


def require_reviewer(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer access is required")
    return user
