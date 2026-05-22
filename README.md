# Analytics Service

`analytics-service` отвечает за аналитику опросов, достижения пользователей, уведомления и экспорт аналитики в JSON.

## Возможности

- базовая аналитика по числу ответов
- детальная аналитика по вопросам
- продвинутая аналитика со средним временем прохождения
- экспорт аналитики в JSON
- статистика автора по его опросам
- достижения пользователя
- уведомления о новых достижениях
- обработка внутренних событий ответов и подписок

## API

Сервис приведён к `API Design Guide`: https://docs.ensi.tech/guidelines/api

- базовый префикс: `/api/v1`
- формат JSON-ответов: `data`, `errors`, `meta`

Основные маршруты:

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/health` | healthcheck |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/basic` | базовая аналитика |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/detailed` | детальная аналитика |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/advanced` | продвинутая аналитика |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/export` | экспорт аналитики в JSON |
| `GET` | `/api/v1/users/{user_id}/statistics` | статистика автора по опросам |
| `GET` | `/api/v1/users/{user_id}/achievements` | достижения пользователя |
| `GET` | `/api/v1/users/{user_id}/notifications` | уведомления пользователя |
| `POST` | `/api/v1/internal-events:answer-created` | внутреннее событие ответа на вопрос |
| `POST` | `/api/v1/internal-events:submission-created` | внутреннее событие отправки ответа на опрос |
| `POST` | `/api/v1/internal-events:follower-created` | внутреннее событие новой подписки |

## Достижения

Дополнительно реализованы сложные достижения:

- `Hard worker` — 50 ответов
- `Explorer` — ответы в 5 категориях
- `Celebrity` — 50 подписчиков

## Интеграции

- получает события от `survey-service`
- читает данные из `survey-service` по:
  - `GET /api/v1/surveys/{survey_id}/answer-stats`
  - `POST /api/v1/users/{user_id}/surveys:search`
- получает события подписок от `user-service`

## Запуск

Через Docker:

```powershell
docker build -t analytics-service .
docker run --rm -p 8082:8082 `
  -e DATABASE_URL=sqlite:///./data/analytics.db `
  -e SURVEY_SERVICE_URL=http://host.docker.internal:8081 `
  -e INTERNAL_API_KEY=change-me-local-internal-key `
  analytics-service
```

Локально:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8082
```

Переменные окружения:

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `SURVEY_SERVICE_URL` | `http://localhost:8081` | адрес `survey-service` |
| `DATABASE_URL` | `sqlite:///./data/analytics.db` | SQLite база данных |
| `INTERNAL_API_KEY` | `change-me` | ключ внутренних API |

## Тесты

```powershell
python -m unittest discover -s tests -p "test_analytics.py" -v
```

## Git hooks

В репозиторий добавлен `pre-push` hook, который запускает тесты.

Установка внутри `analytics-service`:

```powershell
git config core.hooksPath .githooks
```

Либо из корня монорепозитория:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\..\scripts\install-git-hooks.ps1
```
