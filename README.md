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

# Docker (рекомендуется для production)
docker-compose up --build

# Проверка статуса
docker-compose ps
docker logs matching-service

# Просмотр логов в реальном времени
docker logs -f matching-service

# На Mac с Apple Silicon (M1/M2/M3)
docker buildx build --platform linux/amd64 -t matching-service .
docker-compose up
```

Сервис доступен на `http://127.0.0.1:8000`

При первом запуске будет скачана ML модель (~500MB). Healthcheck проверяет доступность каждые 30 секунд.

## Конфигурация

Все параметры имеют разумные значения по умолчанию в коде. Переопределяйте только необходимые через переменные окружения.

### Локальная разработка

Файл `.env` используется **только для секретов** (токены, пароли):

```bash
# .env (только секреты)
HUGGINGFACE_TOKEN=your_token_here
```

Для изменения обычных настроек используйте переменные окружения:

```bash
API_HOST=0.0.0.0 ML_DEVICE=cuda python -m matching_service.entrypoints.run_web_server
```

### Production / Kubernetes

В продакшене используйте:
- **ConfigMap** для конфигурации (API_*, ML_*, LOG_*)
- **Secrets** для секретных данных
- Переменные окружения в docker-compose.yml

### API Configuration (`API_*`)

```bash
API_HOST=127.0.0.1              # API host (default: 127.0.0.1)
API_PORT=8000                   # API port (default: 8000)
API_RELOAD=false                # Auto-reload для разработки (default: false)
API_DEFAULT_TOP_K=5             # Кол-во результатов по умолчанию (default: 5)
API_MAX_TOP_K=50                # Максимальное кол-во результатов (default: 50)
API_SCORE_DECIMAL_PLACES=4      # Знаков после запятой в score (default: 4)
```

### Database Configuration (`DB_*`)

```bash
DB_VECTOR_DB_PATH=data/vectors.db  # Путь к SQLite БД (default: data/vectors.db)
```

### ML Model Configuration (`ML_*`)

```bash
ML_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ML_DEVICE=                      # cpu, cuda, auto, или пусто для авто (default: None)
ML_VECTOR_DIM=384               # Размерность вектора (default: 384)
ML_EMBEDDING_BATCH_SIZE=32      # Batch size для эмбеддингов (default: 32)
ML_MAX_TEXT_LENGTH=512          # Макс. кол-во токенов (default: 512)
ML_MIN_CLAMP_VALUE=1e-9         # Min clamp для normalization (default: 1e-9)
```

### Logging Configuration (`LOG_*`)

```bash
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
LOG_FORMAT="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
```

### Примеры

**Локальная разработка (с GPU):**
```bash
ML_DEVICE=cuda LOG_LEVEL=DEBUG python -m matching_service.entrypoints.run_web_server
```

**Docker Compose:**
```bash
# Переопределение через переменные окружения
ML_DEVICE=cuda LOG_LEVEL=INFO docker-compose up
```

**Kubernetes:**
```yaml
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: matching-service-config
data:
  API_HOST: "0.0.0.0"
  ML_DEVICE: "cuda"
  LOG_LEVEL: "INFO"

# Deployment
env:
  - name: API_HOST
    valueFrom:
      configMapKeyRef:
        name: matching-service-config
        key: API_HOST
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
- `text` (str, обязательный): текстовое описание товара (макс. 100000 символов)

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
- `text` (str, обязательный): поисковый запрос (макс. 100000 символов)
- `top_k` (int, опциональный): количество результатов (по умолчанию 5)

Ответ (200 OK):
```json
[
  {
    "id": 12345,
    "score_rate": 0.95,
    "text": "Диагностический адаптер ELM327"
  }
]
```

**Примечание:** Если хранилище пустое (нет загруженных товаров), возвращается пустой массив `[]` с HTTP 200 OK.

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
