# Быстрый старт: MarketGuru Reporting в ClickHouse

## 📋 Что сделано

1. ✅ **Проверена корректность всех SQL-запросов** (см. `validation_report.md`)
2. ✅ **Создан полный SQL-скрипт для ClickHouse** (`clickhouse_mg_reporting_schema.sql`)
3. ✅ **Спроектированы 3 слоя данных:**
   - `mg_raw.*` - сырые данные из PostgreSQL
   - `mg_dm.*` - витрины для отчётов
   - `mg_mv.*` - материализованные представления

---

## 🚀 План действий до вторника

### Шаг 1: Подготовка среды (30 мин)

```bash
# Подключиться к ClickHouse
clickhouse-client --host wbia-prod-alfa-ch-1.mgt --user ALFACHUSER

# Проверить подключение
SELECT version();
```

### Шаг 2: Создание структуры (10 мин)

```bash
# Выполнить основной скрипт
clickhouse-client --host wbia-prod-alfa-ch-1.mgt --user ALFACHUSER < clickhouse_mg_reporting_schema.sql

# Проверить созданные таблицы
clickhouse-client --query "SHOW TABLES FROM mg_raw"
clickhouse-client --query "SHOW TABLES FROM mg_dm"
```

### Шаг 3: Загрузка тестовых данных (1-2 часа)

#### Вариант А: Через PostgreSQL Table Engine (быстро, для теста)

```sql
-- Подключиться к ClickHouse и выполнить:

-- 1. Загрузить пользователей
INSERT INTO mg_raw.users
SELECT 
    id AS user_id,
    created,
    source::Array,  -- конвертировать в массив
    deleted
FROM postgresql('postgres_host:5432', 'users_db', 'users', 'user', 'password')
WHERE 'marketguru' = ANY(source) 
  AND created >= '2024-01-01'
  AND created <= '2024-02-01';  -- Для теста берём 1 месяц

-- 2. Загрузить платежи
INSERT INTO mg_raw.payments
SELECT 
    id AS payment_id,
    updated,
    "completedDate" AS completedDate,
    "purposeOfPayment" AS purposeOfPayment,
    amount,
    state,
    source::String,
    "userId" AS user_id
FROM postgresql('postgres_host:5432', 'users_db', 'Payments', 'user', 'password')
WHERE source::String = 'marketguru'
  AND updated >= '2024-01-01'
  AND updated <= '2024-02-01';

-- 3-6. Аналогично для остальных таблиц...
```

#### Вариант Б: Через CSV (надёжно, для прода)

```bash
# В PostgreSQL экспортировать данные
psql -h postgres_host -U user -d users_db -c "COPY (
    SELECT id, created, source, deleted 
    FROM users 
    WHERE 'marketguru' = ANY(source) AND created >= '2024-01-01'
) TO STDOUT WITH CSV HEADER" > users.csv

# В ClickHouse импортировать
clickhouse-client --query "INSERT INTO mg_raw.users FORMAT CSV" < users.csv
```

#### Вариант В: Python-скрипт (универсально)

```python
# fetch_and_load.py
import psycopg2
from clickhouse_driver import Client

# PostgreSQL connection
pg_conn = psycopg2.connect("host=pg_host dbname=users_db user=user password=pwd")
pg_cur = pg_conn.cursor()

# ClickHouse connection
ch_client = Client('ch_host', user='ALFACHUSER', password='pwd')

# Пример для users
pg_cur.execute("""
    SELECT id, created, source, deleted 
    FROM users 
    WHERE 'marketguru' = ANY(source) AND created >= '2024-01-01'
    LIMIT 10000
""")

rows = pg_cur.fetchall()
ch_client.execute('INSERT INTO mg_raw.users VALUES', rows)

print(f"Loaded {len(rows)} users")
```

### Шаг 4: Проверка витрин (15 мин)

```sql
-- Проверить автоматическое заполнение витрин через MV
SELECT COUNT(*) FROM mg_dm.users_entry;
SELECT COUNT(*) FROM mg_dm.payments_daily;

-- Проверить первые строки
SELECT * FROM mg_dm.users_entry LIMIT 10;
SELECT * FROM mg_dm.payments_daily ORDER BY event_date LIMIT 10;

-- Сравнить с PostgreSQL (должны совпадать)
-- В PostgreSQL выполнить оригинальный запрос и сравнить COUNT и суммы
```

### Шаг 5: Подготовка демонстрации (30 мин)

Подготовить 2 запроса для показа лиду:

#### 1. Отчёт "users" с нумерацией

```sql
SELECT
    row_number() OVER (ORDER BY entryDate, user_id) AS id,
    user_id,
    entryDate,
    formatDateTime(entryDate, '%Y-%m') AS month
FROM mg_dm.users_entry
ORDER BY entryDate DESC
LIMIT 100;
```

#### 2. Отчёт "payments" за последние 30 дней

```sql
SELECT
    row_number() OVER (ORDER BY event_date) AS id,
    event_date,
    total_payment_attempts,
    completed_payments,
    refunds,
    total_revenue,
    tariff_revenue,
    ap_revenue,
    refund_amount,
    -- Дополнительные метрики
    round(completed_payments / total_payment_attempts * 100, 2) AS conversion_rate,
    round(total_revenue / completed_payments, 2) AS avg_check
FROM mg_dm.payments_daily
WHERE event_date >= today() - INTERVAL 30 DAY
ORDER BY event_date DESC;
```

---

## 📊 Что показать лиду во вторник

### ✅ Готово к демо:

1. **Структура данных:**
   ```
   mg_raw.*              -> 6 таблиц (сырые данные)
   mg_dm.*               -> 6 витрин (отчёты)
   mg_mv.*               -> 2 MV (автоматическое обновление)
   ```

2. **Работающие отчёты:**
   - ✅ `users` (регистрации) - ГОТОВ, автообновление
   - ✅ `payments` (платежи) - ГОТОВ, автообновление

3. **В разработке:**
   - ⚠️ `event_backend` - требует ETL-скрипт
   - ⚠️ `packages-by-tariff` - требует ETL-скрипт
   - ⚠️ `packages-by-period` - требует ETL-скрипт
   - ⚠️ `mg_churn` - требует ETL-скрипт

### 📈 Примеры метрик для демо:

```sql
-- Статистика по пользователям
SELECT 
    formatDateTime(entryDate, '%Y-%m') AS month,
    count() AS new_users
FROM mg_dm.users_entry
GROUP BY month
ORDER BY month DESC
LIMIT 12;

-- Статистика по платежам
SELECT 
    sum(total_revenue) AS total_revenue_all_time,
    sum(completed_payments) AS total_payments,
    round(avg(total_revenue), 2) AS avg_daily_revenue
FROM mg_dm.payments_daily;

-- Конверсия по дням недели
SELECT 
    toDayOfWeek(event_date) AS day_of_week,
    avg(completed_payments / total_payment_attempts * 100) AS avg_conversion
FROM mg_dm.payments_daily
GROUP BY day_of_week
ORDER BY day_of_week;
```

---

## 🎯 План дальнейшего развития

### Фаза 1: Автоматизация (после вторника, 3-5 дней)

1. **ETL-пайплайн для ежедневной загрузки:**
   - Airflow DAG для синхронизации RAW-таблиц
   - Запуск в 02:00 MSK каждую ночь
   - Инкрементальная загрузка (только новые записи)

2. **ETL для сложных витрин:**
   - Скрипты из СЕКЦИИ 6 (`clickhouse_mg_reporting_schema.sql`)
   - Запуск после синхронизации RAW
   - Логирование времени выполнения

### Фаза 2: Интеграция с Подели (1-2 недели)

1. **API-слой или S3:**
   - Экспорт витрин в формате Подели
   - Расписание синхронизации

2. **Дашборды:**
   - Подключение Подели к ClickHouse (если поддерживается)
   - Или экспорт в промежуточное хранилище

### Фаза 3: Мониторинг и оптимизация (постоянно)

1. **Мониторинг:**
   - Проверка актуальности данных
   - Алерты на задержку > 2 часов
   - Сравнение COUNT между PG и CH

2. **Оптимизация:**
   - Настройка индексов
   - Партиционирование больших таблиц
   - Тюнинг запросов

---

## ⚠️ Важные моменты для обсуждения

### 1. Поле `sourceType` в `user_permission_packages`

**Проблема:** В DDL видно поле `type`, а в запросах используется `sourceType`.

**Вопросы для команды:**
- Это одно и то же поле (алиас)?
- Или `sourceType` вычисляется на лету?
- Какие значения принимает: `trial`, `payment`, `upgrade`, `paidCoupon`, `gift`, ...?

**Как проверить в PostgreSQL:**
```sql
SELECT DISTINCT "type" FROM user_permission_packages LIMIT 20;
-- или
SELECT DISTINCT "sourceType" FROM user_permission_packages LIMIT 20;
```

### 2. Часовой пояс MSK

**В PostgreSQL:** `AT TIME ZONE 'MSK'`  
**В ClickHouse:** `'Europe/Moscow'`

Проверить совместимость, возможно понадобится коррекция.

### 3. Объёмы данных

**Для планирования инфраструктуры:**
- Сколько пользователей в `users` с `source = 'marketguru'`?
- Сколько записей в `Payments` за 2024 год?
- Сколько записей в `user_permission_packages`?

**Как проверить:**
```sql
-- В PostgreSQL
SELECT 
    (SELECT COUNT(*) FROM users WHERE 'marketguru' = ANY(source)) AS users_count,
    (SELECT COUNT(*) FROM "Payments" WHERE source = 'marketguru') AS payments_count,
    (SELECT COUNT(*) FROM user_permission_packages) AS upp_count;
```

---

## 📚 Полезные ссылки

- **Основной SQL-скрипт:** `clickhouse_mg_reporting_schema.sql`
- **Отчёт о проверке:** `validation_report.md`
- **ClickHouse документация:** https://clickhouse.com/docs/
- **PostgreSQL -> ClickHouse миграция:** https://clickhouse.com/docs/en/engines/table-engines/integrations/postgresql

---

## 🆘 Если что-то пошло не так

### Ошибка: "Database doesn't exist"
```sql
CREATE DATABASE IF NOT EXISTS mg_raw;
CREATE DATABASE IF NOT EXISTS mg_dm;
```

### Ошибка: "Table already exists"
```sql
DROP TABLE IF EXISTS mg_raw.users;
-- Затем пересоздать
```

### Ошибка при INSERT из PostgreSQL
Проверить:
1. Сетевую доступность PostgreSQL из ClickHouse
2. Правильность креденшалов
3. Формат данных (особенно массивы и JSON)

### Данные в RAW есть, но витрины пустые
```sql
-- Проверить MV
SELECT * FROM system.tables WHERE database = 'mg_mv';

-- Пересоздать MV
DROP VIEW IF EXISTS mg_mv.users_entry_mv;
-- Затем создать заново из скрипта

-- Заполнить витрину вручную (one-time)
INSERT INTO mg_dm.users_entry
SELECT user_id, toDate(created) AS entryDate
FROM mg_raw.users
WHERE deleted IS NULL AND has(source, 'marketguru');
```

---

## ✅ Чеклист перед демо во вторник

- [ ] ClickHouse доступен, есть права на создание БД
- [ ] Созданы 3 базы данных (mg_raw, mg_dm, mg_mv)
- [ ] Созданы 6 RAW-таблиц
- [ ] Загружены тестовые данные (хотя бы 1000 записей в каждую таблицу)
- [ ] Созданы 6 витрин в mg_dm
- [ ] Работают 2 материализованные представления
- [ ] Проверены результаты (совпадают с PostgreSQL)
- [ ] Подготовлены 2-3 примера запросов для демо
- [ ] Подготовлен список вопросов для лида (см. раздел "Важные моменты")

---

**Успехов с демонстрацией! 🚀**

**PS:** Если потребуется помощь с Python-скриптами для ETL или дополнительные запросы для оптимизации - обращайся!

