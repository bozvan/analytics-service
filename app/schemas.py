from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class BasicAnalyticsResponse(BaseModel):
    survey_id: int
    answers_count: int


class UserStatisticsResponse(BaseModel):
    user_id: int
    total_surveys: int
    total_answers: int
    surveys: List[BasicAnalyticsResponse]


class AnswerCreatedEventRequest(BaseModel):
    user_id: int
    answer_id: str = Field(min_length=1)
    question_id: int
    survey_id: int


class SubmissionCreatedEventRequest(BaseModel):
    user_id: int
    submission_id: str = Field(min_length=1)
    survey_id: int
    question_ids: List[int] = Field(min_length=1)

    @field_validator("question_ids")
    @classmethod
    def validate_question_ids(cls, value: List[int]) -> List[int]:
        normalized = [int(question_id) for question_id in value]
        if any(question_id <= 0 for question_id in normalized):
            raise ValueError("question_ids must contain positive integers only")
        if len(set(normalized)) != len(normalized):
            raise ValueError("question_ids must be unique")
        return normalized


class AwardedAchievementResponse(BaseModel):
    id: int
    name: str
    description: str
    awarded_at: str


class AnswerCreatedEventResponse(BaseModel):
    status: str
    answer_id: str
    survey_id: int
    question_id: int
    answer_count: int
    awarded_achievements: List[AwardedAchievementResponse]


class ProcessedQuestionCountResponse(BaseModel):
    question_id: int
    submission_count: int


class SubmissionCreatedEventResponse(BaseModel):
    status: str
    submission_id: str
    survey_id: int
    question_counts: List[ProcessedQuestionCountResponse]
    awarded_achievements: List[AwardedAchievementResponse]


class DetailedQuestionAnalyticsResponse(BaseModel):
    question_id: int
    submission_count: int
    percentage: float


class DetailedSurveyAnalyticsResponse(BaseModel):
    survey_id: int
    total_submissions: int
    questions: List[DetailedQuestionAnalyticsResponse]


class UserAchievementResponse(BaseModel):
    id: int
    name: str
    description: str
    awarded_at: str


class UserAchievementsListResponse(BaseModel):
    user_id: int
    achievements: List[UserAchievementResponse]
