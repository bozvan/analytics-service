from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api import ApiResponse, success_response
from app.dependencies import verify_internal_token
from app.db import get_connection
from app.schemas import (
    AnswerCreatedEventRequest,
    AnswerCreatedEventResponse,
    FollowerCreatedEventRequest,
    SubmissionCreatedEventRequest,
    SubmissionCreatedEventResponse,
)
from app.services.achievement_service import increment_followers_and_award
from app.services.event_service import (
    process_answer_created_event,
    process_submission_created_event,
)

router = APIRouter(prefix="/api/v1", tags=["Internal events"])


@router.post(
    "/internal-events:answer-created",
    dependencies=[Depends(verify_internal_token)],
    response_model=ApiResponse[AnswerCreatedEventResponse],
    summary="Process answer.created events",
)
def handle_answer_created(
    payload: AnswerCreatedEventRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, object]:
    response_status, response_body = process_answer_created_event(
        payload=payload,
        idempotency_key=idempotency_key,
    )
    if response_status >= 400:
        raise HTTPException(
            status_code=response_status,
            detail=str(response_body.get("detail", "Request failed")),
        )
    return success_response(AnswerCreatedEventResponse(**response_body))


@router.post(
    "/internal-events:submission-created",
    dependencies=[Depends(verify_internal_token)],
    response_model=ApiResponse[SubmissionCreatedEventResponse],
    summary="Process submission.created events",
)
def handle_submission_created(
    payload: SubmissionCreatedEventRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, object]:
    response_status, response_body = process_submission_created_event(
        payload=payload,
        idempotency_key=idempotency_key,
    )
    if response_status >= 400:
        raise HTTPException(
            status_code=response_status,
            detail=str(response_body.get("detail", "Request failed")),
        )
    return success_response(SubmissionCreatedEventResponse(**response_body))


@router.post(
    "/internal-events:follower-created",
    dependencies=[Depends(verify_internal_token)],
    response_model=ApiResponse[dict[str, object]],
    summary="Process follower.created events",
)
def handle_follower_created(payload: FollowerCreatedEventRequest) -> dict[str, object]:
    with get_connection() as connection:
        awarded = increment_followers_and_award(connection, payload.user_id)
    return success_response(
        {
            "status": "processed",
            "user_id": payload.user_id,
            "awarded_achievements": awarded,
        }
    )
