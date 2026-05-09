from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


def verify_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    authorization: str | None = Header(default=None),
) -> None:
    expected_token = get_settings().internal_api_key
    candidate = x_internal_token

    if candidate is None and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            candidate = token

    if candidate is None or not secrets.compare_digest(candidate, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
