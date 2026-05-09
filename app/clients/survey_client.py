from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app.config import get_settings


def _survey_service_url() -> str:
    return get_settings().survey_service_url


def fetch_answer_count(survey_id: int) -> int:
    url = f"{_survey_service_url()}/surveys/{survey_id}/answers/count"
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Survey service returned an error",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Survey service is unavailable",
        ) from exc

    payload = response.json()
    return int(payload["answers_count"])


def fetch_user_surveys(user_id: int) -> Optional[List[Dict[str, Any]]]:
    url = f"{_survey_service_url()}/users/{user_id}/surveys"

    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            return None
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Survey service returned an error",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Survey service is unavailable",
        ) from exc

    return response.json()


def fetch_all_surveys_stats() -> Dict[str, Any]:
    url = f"{_survey_service_url()}/surveys/statistics"

    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Survey service is unavailable",
        ) from exc

    return response.json()


def check_survey_service_health() -> bool:
    url = f"{_survey_service_url()}/health"

    try:
        response = httpx.get(url, timeout=2.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False
