from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api import ApiResponse, success_response
from app.clients.survey_client import fetch_answer_count, fetch_user_surveys
from app.db import get_connection
from app.schemas import (
    AdvancedSurveyAnalyticsResponse,
    BasicAnalyticsResponse,
    DetailedSurveyAnalyticsResponse,
    UserStatisticsResponse,
)
from app.services.analytics_service import (
    get_advanced_survey_stats,
    get_detailed_survey_stats,
)

router = APIRouter(prefix="/api/v1", tags=["Analytics"])


@router.get(
    "/surveys/{survey_id}/analytics/basic",
    response_model=ApiResponse[BasicAnalyticsResponse],
    summary="Get basic survey analytics",
)
def get_basic_analytics(survey_id: int) -> dict[str, object]:
    answers_count = fetch_answer_count(survey_id)
    return success_response(BasicAnalyticsResponse(survey_id=survey_id, answers_count=answers_count))


@router.get(
    "/users/{user_id}/statistics",
    response_model=ApiResponse[UserStatisticsResponse],
    summary="Get user survey statistics",
)
def get_user_statistics(user_id: int) -> dict[str, object]:
    surveys = fetch_user_surveys(user_id)

    if surveys is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or has no surveys",
        )

    total_answers = 0
    surveys_stats = []

    for survey in surveys:
        survey_id = int(survey["id"])
        answers_count = fetch_answer_count(survey_id)
        total_answers += answers_count
        surveys_stats.append(
            BasicAnalyticsResponse(
                survey_id=survey_id,
                answers_count=answers_count,
            )
        )

    return success_response(
        UserStatisticsResponse(
            user_id=user_id,
            total_surveys=len(surveys),
            total_answers=total_answers,
            surveys=surveys_stats,
        )
    )


@router.get(
    "/surveys/{survey_id}/analytics/detailed",
    response_model=ApiResponse[DetailedSurveyAnalyticsResponse],
    summary="Get detailed survey analytics",
)
def get_detailed_analytics(survey_id: int) -> dict[str, object]:
    with get_connection() as connection:
        analytics = get_detailed_survey_stats(connection, survey_id)

    return success_response(DetailedSurveyAnalyticsResponse(**analytics))


@router.get(
    "/surveys/{survey_id}/analytics/advanced",
    response_model=ApiResponse[AdvancedSurveyAnalyticsResponse],
    summary="Get advanced survey analytics",
)
def get_advanced_analytics(survey_id: int) -> dict[str, object]:
    with get_connection() as connection:
        analytics = get_advanced_survey_stats(connection, survey_id)

    return success_response(AdvancedSurveyAnalyticsResponse(**analytics))


@router.get(
    "/surveys/{survey_id}/analytics/export",
    response_model=ApiResponse[DetailedSurveyAnalyticsResponse],
    summary="Export survey analytics as JSON",
)
def export_survey_analytics(survey_id: int) -> dict[str, object]:
    with get_connection() as connection:
        analytics = get_detailed_survey_stats(connection, survey_id)

    return success_response(DetailedSurveyAnalyticsResponse(**analytics))
