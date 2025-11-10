# Product Matching Service

Минимальный сервис поиска похожих товаров с чистой слоистой архитектурой: FastAPI + sentence-transformers + SQLite.

## Архитектура

Проект построен по принципам чистой слоистой архитектуры с явным разделением ответственности:

```
src/matching_service/
├── api/                    # API слой (FastAPI контроллеры и схемы)
│   ├── controllers/        # REST endpoints
│   ├── schemas.py          # Pydantic модели запросов/ответов
│   └── error_handlers.py   # Обработка ошибок
├── services/               # Бизнес-логика (use-cases)
│   ├── storage.py          # VectorStorage - основной сервис
│   ├── embedder.py         # TextEmbedder - генерация эмбеддингов
│   └── search.py           # Алгоритм cosine similarity
├── storage/                # Слой данных
│   └── repositories/       # Реализации репозиториев
│       └── sqlite_repository.py  # SqliteVectorRepository
├── utils/                  # Утилиты
│   └── exceptions.py       # Доменные исключения
├── entrypoints/            # Точки входа
│   └── run_web_server.py   # Запуск FastAPI приложения
└── config.py               # Конфигурация (dataclass)
```

### Принципы

- **Явные зависимости**: Все параметры передаются через конструкторы, никаких глобальных settings внутри core слоев
- **Конкретные реализации**: Без лишних абстракций и интерфейсов - только то, что нужно
- **Доменные исключения**: `InvalidTextError`, `EmptyStorageError` вместо сырых `ValueError`
- **Валидация**: На уровне API (Pydantic) и в бизнес-логике
- **Простота**: Прямое создание компонентов в entrypoint, без DI-контейнеров

## Быстрый старт

### Вариант 1: Локальный запуск

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd matching_service

# 2. Установить uv (если еще не установлен)
pip install uv

# 3. Установить зависимости
uv sync

# 4. Запустить сервис
uv run matching-service
```

Сервис будет доступен на `http://127.0.0.1:8000`

### Вариант 2: Запуск через Docker

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd matching_service

# 2. Запустить через docker-compose
docker-compose up --build

# Или в фоновом режиме
docker-compose up -d --build
```

Сервис будет доступен на `http://localhost:8000`

**Проверка работы:**
```bash
curl http://localhost:8000/
```

## Установка

### Требования
- Python 3.11+ (для локального запуска)
- uv (для управления зависимостями, для локального запуска)
- Docker и Docker Compose (для запуска через Docker)

### Установка uv

**Через pip (рекомендуется):**
```bash
pip install uv
```

**Альтернативные способы:**

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

После установки через pip uv будет доступен сразу. При установке через скрипты перезапустите терминал.

### Установка зависимостей

```bash
# Установить все зависимости (создаст виртуальное окружение автоматически)
uv sync

# Активировать виртуальное окружение
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate       # Windows

# Или запускать команды без активации
uv run matching-service
```

**Примечание:** Если у вас уже активировано другое виртуальное окружение (например, через PyCharm или вручную), либо:
- Деактивируйте его: `deactivate` (Linux/macOS) или `deactivate` (Windows)
- Или используйте флаг `--active`: `uv run --active matching-service`

## Запуск

### Локальный запуск

```bash
# Базовый запуск (127.0.0.1:8000)
uv run matching-service

# Или если окружение активировано
matching-service

# Кастомный запуск
uv run matching-service --host 0.0.0.0 --port 8080 --log-level DEBUG

# С auto-reload для разработки
uv run matching-service --reload

# Справка по параметрам
uv run matching-service --help
```

Или напрямую через Python:
```bash
uv run python -m matching_service.entrypoints.run_web_server
```

### Управление зависимостями

```bash
# Добавить новую зависимость
uv add package-name

# Удалить зависимость
uv remove package-name

# Обновить зависимости
uv sync --upgrade

# Обновить lock файл
uv lock
```

### Запуск через Docker

```bash
# Сборка и запуск через docker-compose
docker-compose up --build

# Запуск в фоне
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### Запуск через переменные окружения

Создайте файл `.env` в корне проекта:

```bash
# API настройки
API_HOST=0.0.0.0
API_PORT=8000

# Пути к данным
DATA_PATH=data/KE_Автотовары.jsonl
VECTOR_DB_PATH=data/vectors.db

# Модель
MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
DEVICE=cpu

# Параметры поиска
DEFAULT_TOP_K=5
MAX_TOP_K=50
EMBEDDING_BATCH_SIZE=32
MAX_TEXT_LENGTH=256
DEFAULT_BATCH_SIZE=1000
```

Затем запустите:
```bash
# Загрузка переменных окружения и запуск
export $(cat .env | xargs) && matching-service
```

Или используйте `python-dotenv`:
```bash
pip install python-dotenv
python -c "from dotenv import load_dotenv; load_dotenv(); from matching_service.entrypoints.run_web_server import cli; cli()"
```

Документация: http://127.0.0.1:8000/docs

## Использование API

### Health check
```bash
curl http://127.0.0.1:8000/
```

### Upsert (добавить/обновить товар)
```bash
curl -X POST "http://127.0.0.1:8000/upsert" \
  -H "Content-Type: application/json" \
  -d '{"text": "Диагностический адаптер ELM327"}'
```

### Search (поиск похожих)
```bash
curl -G "http://127.0.0.1:8000/search" \
  --data-urlencode "text=адаптер ELM327" \
  --data-urlencode "top_k=5"
```

## Программное использование

Сервис можно использовать напрямую из Python без FastAPI:

```python
from matching_service.config import Config
from matching_service.services import TextEmbedder, VectorStorage
from matching_service.storage.repositories import SqliteVectorRepository

# Создание компонентов
config = Config()
repository = SqliteVectorRepository(db_path=str(config.vector_db_path))
embedder = TextEmbedder(
    model_name=config.model_name,
    device=config.device,
    embedding_batch_size=config.embedding_batch_size,
    max_text_length=config.max_text_length,
    min_clamp_value=config.min_clamp_value,
)
storage = VectorStorage(
    repository=repository,
    embedding_batch_size=config.embedding_batch_size,
    embedder=embedder,
)

# Использование
vector_id = storage.upsert("Масло моторное 5W-40")
results = storage.search("моторное масло", top_k=5)

for result in results:
    print(f"ID: {result.id}, Score: {result.score:.4f}, Text: {result.text}")
```

## Загрузка данных

```python
from matching_service.config import Config
from matching_service.services import TextEmbedder, VectorStorage
from matching_service.storage.repositories import SqliteVectorRepository

config = Config()
repository = SqliteVectorRepository(db_path=str(config.vector_db_path))
embedder = TextEmbedder(
    model_name=config.model_name,
    device=config.device,
    embedding_batch_size=config.embedding_batch_size,
    max_text_length=config.max_text_length,
    min_clamp_value=config.min_clamp_value,
)
storage = VectorStorage(
    repository=repository,
    embedding_batch_size=config.embedding_batch_size,
    embedder=embedder,
)

# Загрузить из JSONL
# Добавление данных через API upsert
print(f"Loaded {storage.count()} vectors")
```

## Конфигурация

Параметры задаются в `config.py` (dataclass):

```python
@dataclass
class Config:
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    data_path: Path = Path("data/KE_Автотовары.jsonl")
    vector_db_path: Path = Path("data/vectors.db")

    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str | None = None  # None = auto-detect
    
    default_top_k: int = 5
    max_top_k: int = 50
    embedding_batch_size: int = 32
    max_text_length: int = 256
    default_batch_size: int = 1000
```

Можно изменить значения напрямую в `config.py` или создать свой экземпляр `Config` с кастомными параметрами.

## Структура слоев

**API (Presentation)**
- Контроллеры FastAPI
- Pydantic схемы для валидации
- Маппинг DTO → API responses

**Services (Application/Use-cases)**
- `VectorStorage`: upsert, search
- `TextEmbedder`: генерация эмбеддингов
- Бизнес-правила и валидация

**Storage (Infrastructure)**
- `SqliteVectorRepository` — хранение векторов в SQLite
- Сериализация/десериализация векторов

**Utils**
- Доменные исключения
- Переиспользуемые утилиты

**Entrypoints**
- Создание и конфигурация приложения
- Запуск веб-сервера

## Зависимости слоев

```
API → Services → Storage Repositories
```

Простая прямая зависимость без лишних абстракций. Бизнес-логика напрямую использует конкретные реализации.
