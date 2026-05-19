# Analytics Service

## 1. Название и назначение сервиса

`analytics-service` — микросервис аналитики в системе PIUS. Он хранит локальную статистику по ответам на опросы, принимает внутренние события от `survey-service`, отдает базовую и детальную аналитику, экспортирует данные в CSV и ведет достижения пользователей.

Основные функции:

- прием событий `answer-created` и `submission-created`;
- расчет количества ответов и статистики по вопросам;
- экспорт аналитики по опросу в CSV;
- расчет статистики автора по его опросам;
- хранение и выдача достижений пользователя.

## 2. Архитектура и зависимости

Технологии:

- Python 3.11;
- FastAPI и Uvicorn;
- Pydantic;
- SQLite;
- Alembic;
- HTTPX;
- unittest и FastAPI TestClient.

Взаимодействие с микросервисами:

- получает от `survey-service` события `POST /internal/events/submission-created` и `POST /internal/events/answer-created`;
- вызывает `survey-service` для чтения количества ответов и списка опросов пользователя;
- внутренние вызовы защищены `INTERNAL_API_KEY`.

Внешние сервисы не используются. Redis, Kafka, S3 и внешняя PostgreSQL в текущей версии не требуются.

## 3. Способы запуска сервиса

### Через Docker

```powershell
docker build -t analytics-service .
docker run --rm -p 8082:8082 `
  -e DATABASE_URL=sqlite:///./data/analytics.db `
  -e SURVEY_SERVICE_URL=http://host.docker.internal:8081 `
  -e INTERNAL_API_KEY=change-me-local-internal-key `
  analytics-service
```

### Без Docker

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8082
```

### Переменные окружения

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `SURVEY_SERVICE_URL` | `http://localhost:8081` | URL сервиса опросов |
| `DATABASE_URL` | `sqlite:///./data/analytics.db` | SQLite база данных |
| `INTERNAL_API_KEY` | `change-me` | ключ внутренних API-вызовов |

Для запуска всей системы используется общий репозиторий `bozvan/PIUS` и команда `docker compose up --build -d`.

## 4. API документация

После запуска Swagger доступен по адресу:

- `http://localhost:8082/docs`
- `http://localhost:8082/openapi.json`

Основные эндпоинты:

| Метод | Путь | Описание |
| --- | --- | --- |
| `GET` | `/health` | проверка работоспособности |
| `GET` | `/analytics/surveys/{survey_id}/basic` | базовая аналитика по опросу |
| `GET` | `/analytics/surveys/{survey_id}/detailed` | детальная статистика по вопросам |
| `GET` | `/analytics/surveys/{survey_id}/export?format=csv` | экспорт статистики в CSV |
| `GET` | `/analytics/users/{user_id}/statistics` | статистика автора по его опросам |
| `GET` | `/users/{user_id}/achievements` | достижения пользователя |
| `POST` | `/internal/events/answer-created` | legacy-событие по одному вопросу |
| `POST` | `/internal/events/submission-created` | событие по отправленному ответу на опрос |

Внутренние эндпоинты требуют заголовок `X-Internal-Token: <INTERNAL_API_KEY>` или `Authorization: Bearer <INTERNAL_API_KEY>`.

## 5. Как тестировать

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m unittest discover -s tests -p "test_analytics.py" -v
```

## 6. Контакты и поддержка

Автор сервиса: Бозванов И.

Поддержка:

- GitHub Issues: https://github.com/bozvan/analytics-service/issues
- GitHub: https://github.com/bozvan
