from __future__ import annotations

from fastapi import APIRouter

from app.db import get_connection
from app.schemas import UserAchievementsListResponse
from app.services.achievement_service import list_user_achievements

router = APIRouter(tags=["Users"])


@router.get(
    "/users/{user_id}/achievements",
    response_model=UserAchievementsListResponse,
    summary="List user achievements",
)
def get_user_achievements(user_id: int) -> UserAchievementsListResponse:
    with get_connection() as connection:
        achievements = list_user_achievements(connection, user_id)

    return UserAchievementsListResponse(user_id=user_id, achievements=achievements)
