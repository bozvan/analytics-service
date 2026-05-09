# Analytics Service

FastAPI service for survey analytics, event ingestion, CSV export, and user achievements.

## Port

- HTTP: `8082`

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `SURVEY_SERVICE_URL` | `http://localhost:8081` | Base URL for survey-service |
| `DATABASE_URL` | `sqlite:///./data/analytics.db` | SQLite database URL |
| `INTERNAL_API_KEY` | `change-me` | Token for internal service calls |

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Healthcheck |
| `GET` | `/analytics/surveys/{survey_id}/basic` | Basic answer count |
| `GET` | `/analytics/surveys/{survey_id}/detailed` | Detailed survey stats |
| `GET` | `/analytics/surveys/{survey_id}/export?format=csv` | Export analytics as CSV |
| `GET` | `/analytics/users/{user_id}/statistics` | Aggregated author statistics |
| `GET` | `/users/{user_id}/achievements` | User achievements |
| `POST` | `/internal/events/answer-created` | Legacy per-question answer event |
| `POST` | `/internal/events/submission-created` | Submission-level answer event |

Internal endpoints require `X-Internal-Token: <INTERNAL_API_KEY>` or
`Authorization: Bearer <INTERNAL_API_KEY>`.

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8082
```

## Docker

```powershell
docker build -t analytics-service .
docker run --rm -p 8082:8082 `
  -e DATABASE_URL=sqlite:///./data/analytics.db `
  -e SURVEY_SERVICE_URL=http://host.docker.internal:8081 `
  -e INTERNAL_API_KEY=change-me-local-internal-key `
  analytics-service
```

## Example `POST /internal/events/submission-created`

```json
{
  "user_id": 42,
  "submission_id": "1001",
  "survey_id": 7,
  "question_ids": [1, 2, 3]
}
```

## Tests

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m unittest discover -s tests -p "test_analytics.py" -v
```
