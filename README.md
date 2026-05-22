# Analytics Service

## 1. Название и назначение сервиса

**Analytics Service** — микросервис в составе платформы опросов, отвечающий за сбор, агрегацию и предоставление аналитических данных, а также за отслеживание достижений и уведомления пользователей.

**Основные функции:**
- базовая аналитика по числу ответов на опрос
- детальная аналитика по каждому вопросу опроса
- продвинутая аналитика со средним временем прохождения
- экспорт аналитики в JSON
- сводная статистика автора по всем его опросам
- отслеживание достижений пользователя
- уведомления о новых достижениях
- обработка внутренних событий (ответы, отправки опросов, подписки)

## 2. Архитектура и зависимости

**Технологии и фреймворки:**
- Python 3.11+
- FastAPI (веб-фреймворк)
- SQLAlchemy + Alembic (ORM и миграции)
- SQLite (основное хранилище аналитики и достижений)
- Uvicorn (ASGI-сервер)

**Взаимодействие с другими микросервисами:**
- `survey-service` — получение статистики ответов и поиска опросов:
  - `GET /api/v1/surveys/{survey_id}/answer-stats`
  - `POST /api/v1/users/{user_id}/surveys:search`
- `survey-service` — приём внутренних событий:
  - `POST /api/v1/internal-events:answer-created`
  - `POST /api/v1/internal-events:submission-created`
- `user-service` — приём внутренних событий:
  - `POST /api/v1/internal-events:follower-created`

**Внешние сервисы:**
- отсутствуют (в текущей версии Redis, S3, Kafka не используются)

## 3. Способы запуска сервиса

### Локальный запуск через Docker

```
docker build -t analytics-service .
docker run --rm -p 8082:8082 \
  -e DATABASE_URL=sqlite:///./data/analytics.db \
  -e SURVEY_SERVICE_URL=http://host.docker.internal:8081 \
  -e INTERNAL_API_KEY=change-me-local-internal-key \
  analytics-service
```

### Альтернативный запуск без Docker

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8082
```

### Переменные окружения (.env)

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `SURVEY_SERVICE_URL` | `http://localhost:8081` | адрес survey-service |
| `DATABASE_URL` | `sqlite:///./data/analytics.db` | строка подключения к SQLite |
| `INTERNAL_API_KEY` | `change-me` | ключ для аутентификации внутренних API-вызовов |

## 4. API документация

Сервис следует API Design Guide: https://docs.ensi.tech/guidelines/api

- Базовый префикс: `/api/v1`
- Формат JSON-ответов: `data`, `errors`, `meta`

**Документация OpenAPI/Swagger** (доступна после запуска):
- Swagger UI: `http://localhost:8082/docs`
- ReDoc: `http://localhost:8082/redoc`

**Основные эндпоинты:**

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/health` | healthcheck сервиса |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/basic` | базовая аналитика опроса |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/detailed` | детальная аналитика по вопросам |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/advanced` | продвинутая аналитика (время прохождения) |
| `GET` | `/api/v1/surveys/{survey_id}/analytics/export` | экспорт аналитики в JSON |
| `GET` | `/api/v1/users/{user_id}/statistics` | статистика автора по всем опросам |
| `GET` | `/api/v1/users/{user_id}/achievements` | достижения пользователя |
| `GET` | `/api/v1/users/{user_id}/notifications` | уведомления пользователя |
| `POST` | `/api/v1/internal-events:answer-created` | внутреннее событие создания ответа |
| `POST` | `/api/v1/internal-events:submission-created` | внутреннее событие отправки опроса |
| `POST` | `/api/v1/internal-events:follower-created` | внутреннее событие новой подписки |

## 5. Как тестировать

Запуск всех тестов:

```
python -m unittest discover -s tests -p "test_analytics.py" -v
```

Установка pre-push хука для автоматического запуска тестов:

```
git config core.hooksPath .githooks
```

## 6. Контакты и поддержка

По всем вопросам и проблемам обращаться:
- GitHub Issues: [в репозитории сервиса](https://github.com/bozvan/analytics-service/issues)
- Автор: Бозванов Иван
