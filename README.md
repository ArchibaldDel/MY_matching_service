# Product Matching Service

Сервис поиска похожих товаров на основе векторных эмбеддингов. FastAPI + sentence-transformers + SQLite.

## Установка

Требования: Python 3.11+, uv (или pip)

```bash
# Установить uv
pip install uv

# Установить зависимости
uv sync
```

## Запуск

```bash
# Локально
python -m matching_service.entrypoints.run_web_server

# Или через установленный скрипт
uv run matching-service

# Docker
docker-compose up --build
```

Сервис доступен на `http://127.0.0.1:8000`

При первом запуске будет скачана ML модель (~500MB).

## Переменные окружения

```bash
API_HOST=127.0.0.1          # Хост API
API_PORT=8000               # Порт API
API_RELOAD=false            # Автоперезагрузка (dev)
LOG_LEVEL=INFO              # Уровень логирования
VECTOR_DB_PATH=data/vectors.db  # Путь к БД
TORCH_DEVICE=cpu            # cpu, cuda, или None
```

Пример:
```bash
API_HOST=0.0.0.0 API_PORT=9000 python -m matching_service.entrypoints.run_web_server
```

## API

### Health check

```bash
curl http://127.0.0.1:8000/
```

### Добавить/обновить товар

```bash
curl -X POST "http://127.0.0.1:8000/upsert" \
  -H "Content-Type: application/json" \
  -d '{"id": 12345, "text": "Диагностический адаптер ELM327"}'
```

Параметры:
- `id` (int, обязательный): уникальный идентификатор товара
- `text` (str, обязательный): текстовое описание товара

Ответ:
```json
{
  "id": 12345,
  "status": "ok",
  "message": "Upserted (ID: 12345, inserted)"
}
```

### Поиск похожих товаров

```bash
curl -G "http://127.0.0.1:8000/search" \
  --data-urlencode "text=адаптер ELM327" \
  --data-urlencode "top_k=5"
```

Параметры:
- `text` (str, обязательный): поисковый запрос
- `top_k` (int, опциональный): количество результатов (по умолчанию 5)

Ответ:
```json
{
  "results": [
    {
      "id": 12345,
      "score_rate": 0.95,
      "text": "Диагностический адаптер ELM327"
    }
  ]
}
```

## Конфигурация

Конфигурация задается через класс `Config()` в `src/matching_service/config/__init__.py`:

```python
from matching_service.config import Config

config = Config()
# config.api.api_host
# config.api.api_port
# config.db.vector_db_path
# config.ml.model_name
# config.ml.device
```

Или через переменные окружения (см. выше).

## Структура проекта

```
src/matching_service/
├── api/              # FastAPI контроллеры и схемы
├── config/           # Конфигурация
├── dependencies/     # Dependency Injection
├── entrypoints/      # Точка входа (run_web_server.py)
├── services/         # Бизнес-логика (usecases, embedder, cache)
└── storage/          # Репозитории (SQLite, CQRS)
```

## Документация

Интерактивная документация API: `http://127.0.0.1:8000/docs`
