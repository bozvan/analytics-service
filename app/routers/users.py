from __future__ import annotations

from fastapi import APIRouter

from app.api import ApiResponse, success_response
from app.db import get_connection
from app.schemas import UserAchievementsListResponse, UserNotificationsResponse
from app.services.achievement_service import list_user_achievements

router = APIRouter(prefix="/api/v1", tags=["Users"])


@router.get(
    "/users/{user_id}/achievements",
    response_model=ApiResponse[UserAchievementsListResponse],
    summary="List user achievements",
)
def get_user_achievements(user_id: int) -> dict[str, object]:
    with get_connection() as connection:
        achievements = list_user_achievements(connection, user_id)

    return success_response(
        UserAchievementsListResponse(user_id=user_id, achievements=achievements)
    )


@router.get(
    "/users/{user_id}/notifications",
    response_model=ApiResponse[UserNotificationsResponse],
    summary="List user notifications",
)
def get_user_notifications(user_id: int) -> dict[str, object]:
    with get_connection() as connection:
        achievements = list_user_achievements(connection, user_id)

    notifications = [
        {
            "id": int(achievement["id"]),
            "message": f"Achievement unlocked: {achievement['name']}",
            "created_at": str(achievement["awarded_at"]),
        }
        for achievement in achievements
    ]
    return success_response(
        UserNotificationsResponse(user_id=user_id, notifications=notifications)
    )
