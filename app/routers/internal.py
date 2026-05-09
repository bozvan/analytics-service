from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.dependencies import verify_internal_token
from app.schemas import AnswerCreatedEventRequest, SubmissionCreatedEventRequest
from app.services.event_service import (
    process_answer_created_event,
    process_submission_created_event,
)

router = APIRouter(prefix="/internal/events", tags=["Internal events"])


@router.post(
    "/answer-created",
    dependencies=[Depends(verify_internal_token)],
    summary="Process answer.created events",
)
def handle_answer_created(
    payload: AnswerCreatedEventRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JSONResponse:
    response_status, response_body = process_answer_created_event(
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return JSONResponse(status_code=response_status, content=response_body)


@router.post(
    "/submission-created",
    dependencies=[Depends(verify_internal_token)],
    summary="Process submission.created events",
)
def handle_submission_created(
    payload: SubmissionCreatedEventRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JSONResponse:
    response_status, response_body = process_submission_created_event(
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return JSONResponse(status_code=response_status, content=response_body)
