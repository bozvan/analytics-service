from __future__ import annotations

import csv
import io

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.clients.survey_client import fetch_answer_count, fetch_user_surveys
from app.db import get_connection
from app.schemas import (
    BasicAnalyticsResponse,
    DetailedSurveyAnalyticsResponse,
    UserStatisticsResponse,
)
from app.services.analytics_service import get_detailed_survey_stats

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/surveys/{survey_id}/basic",
    response_model=BasicAnalyticsResponse,
    summary="Basic survey analytics",
    responses={
        status.HTTP_200_OK: {"description": "Successful response"},
        status.HTTP_404_NOT_FOUND: {
            "description": "Survey not found",
            "content": {
                "application/json": {"example": {"detail": "Survey not found"}}
            },
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Survey service unavailable or returned an error",
            "content": {
                "application/json": {
                    "example": {"detail": "Survey service is unavailable"}
                }
            },
        },
    },
)
def get_basic_analytics(survey_id: int) -> BasicAnalyticsResponse:
    answers_count = fetch_answer_count(survey_id)
    return BasicAnalyticsResponse(survey_id=survey_id, answers_count=answers_count)


@router.get(
    "/users/{user_id}/statistics",
    response_model=UserStatisticsResponse,
    summary="User survey statistics",
)
def get_user_statistics(user_id: int) -> UserStatisticsResponse:
    surveys = fetch_user_surveys(user_id)

    if surveys is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or has no surveys",
        )

    total_answers = 0
    surveys_stats = []

    for survey in surveys:
        survey_id = survey["id"]
        answers_count = fetch_answer_count(survey_id)
        total_answers += answers_count
        surveys_stats.append(
            BasicAnalyticsResponse(
                survey_id=survey_id,
                answers_count=answers_count,
            )
        )

    return UserStatisticsResponse(
        user_id=user_id,
        total_surveys=len(surveys),
        total_answers=total_answers,
        surveys=surveys_stats,
    )


@router.get(
    "/surveys/{survey_id}/detailed",
    response_model=DetailedSurveyAnalyticsResponse,
    summary="Detailed survey analytics",
)
def get_detailed_analytics(survey_id: int) -> DetailedSurveyAnalyticsResponse:
    with get_connection() as connection:
        analytics = get_detailed_survey_stats(connection, survey_id)

    return DetailedSurveyAnalyticsResponse(**analytics)


@router.get(
    "/surveys/{survey_id}/export",
    summary="Export survey analytics",
)
def export_survey_analytics(
    survey_id: int,
    format: str = Query(default="csv"),
) -> Response:
    if format.lower() != "csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only csv export is supported",
        )

    with get_connection() as connection:
        analytics = get_detailed_survey_stats(connection, survey_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["question_id", "submission_count", "percentage"])

    for question in analytics["questions"]:
        writer.writerow(
            [
                question["question_id"],
                question["submission_count"],
                question["percentage"],
            ]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="survey_{survey_id}_analytics.csv"'
            )
        },
    )
