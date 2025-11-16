# ✅ Финальный чеклист перед запуском

## 📊 Статус проверки

### ✅ Что проверено и готово:

1. **Все SQL-запросы проверены на соответствие исходной логике**
   - ✅ payments - логика сохранена
   - ✅ users - логика сохранена  
   - ✅ packages-by-period - логика сохранена
   - ✅ mg_churn - логика сохранена
   - ✅ event_backend - логика сохранена

2. **Исправлена 1 ошибка:**
   - ⚠️ packages-by-tariff - исправлено `now()` → `dr.day` ✅

3. **Созданы файлы:**
   - ✅ `clickhouse_mg_reporting_schema.sql` - основной скрипт (исправлен)
   - ✅ `validation_report.md` - детальный отчёт проверки
   - ✅ `LOGIC_VALIDATION_AND_TEST_QUERIES.md` - проверка логики и тестовые запросы
   - ✅ `README_CLICKHOUSE_SETUP.md` - быстрый старт
   - ✅ `FINAL_CHECKLIST.md` - этот файл

---

## 🎯 Что нужно сделать ПЕРЕД запуском в ClickHouse

### Шаг 1: Определить структуру финальных таблиц (ОБЯЗАТЕЛЬНО!)

Выполните в **PostgreSQL** следующие запросы:

#### 1.1. Payments
```sql
with t as (
    select
        ("updated" at time zone 'MSK')::date event_date,
        count(case when "purposeOfPayment" <> 'refund' then id end) total_payment_attempts,
        count(case when "purposeOfPayment" <> 'refund' and state = 'completed' then id end) completed_payments,
        count(case when "purposeOfPayment" = 'refund' and state = 'completed' then id end) refunds,
        sum(case when "purposeOfPayment" <> 'refund' and state = 'completed' 
            then "amount" end) total_revenue,
        sum(case when state = 'completed' 
            and "purposeOfPayment" in ('upgradeTariffPackage', 'upsaleTariffPackage', 'buyTariffPackage', 'buyTariffAndAdditionalPackages') 
            then "amount" else 0 end) tariff_revenue,
        sum(case when state = 'completed' and "purposeOfPayment" in ('buyAdditionalPackages') 
            then "amount" else 0 end) ap_revenue,
        sum(case when "purposeOfPayment" = 'refund' and state = 'completed' 
            then -"amount" else 0 end) refund_amount
    from  "Payments" p
    WHERE p.state <> 'split' 
        AND ("updated" at time zone 'MSK')::date >= '2024-01-01'
        and p."source"  = 'marketguru'
    group by 1
)
select * from t LIMIT 5;
```

**Запишите типы колонок:**
- event_date: ?
- total_payment_attempts: ?
- completed_payments: ?
- refunds: ?
- total_revenue: ?
- tariff_revenue: ?
- ap_revenue: ?
- refund_amount: ?

#### 1.2. Users
```sql
SELECT 
    id as user_id, 
    created::Date AS "entryDate"
FROM users
WHERE 'marketguru' = ANY (source) AND deleted IS NULL
    and created::Date >= '2024-01-01'
LIMIT 5;
```

**Запишите типы колонок:**
- user_id: ?
- entryDate: ?

#### 1.3. Packages-by-tariff
```sql
with d as (
    select day from generate_series('2025-10-10'::timestamp, '2025-10-15'::timestamp, '1 day') AS g(day)
),
tt as (
    select
        date(d.day) actual_date,
        t.name,
        case when "sourceType" IN ('payment', 'upgrade', 'paidCoupon') OR
            ("sourceType" = 'gift' AND extract(EPOCH FROM upp."endDate" - "startDate") / 86400 > 29) then 'paid'
        when upp."sourceType" = 'gift' AND extract(EPOCH FROM upp."endDate" - "startDate") / 86400 <= 29 then 'gift'
        else upp."sourceType" end sourceType,
        count(*)::int AS count
    FROM
        permission_packages pp
            JOIN user_permission_packages upp ON upp."permissionPackageId" = pp.id
            INNER JOIN tariffs t ON t."id" = pp."tariffId" and t.source = 'marketguru'
            join d on pp.updated <= d.day
    WHERE
        upp."startDate" < d.day AND
        upp."endDate" > d.day AND
        upp.status = 'active' AND
        upp.deleted IS NULL AND
        pp."tariffId" IS NOT null
    GROUP BY 1,2,3
)
select * from tt LIMIT 5;
```

**Запишите типы колонок:**
- actual_date: ?
- name: ?
- sourceType: ?
- count: ?

#### 1.4. Packages-by-period
```sql
with d as (
    select day from generate_series('2025-10-10'::timestamp, '2025-10-15'::timestamp, '1 day') AS g(day)
),
periods AS (
    select
        date(d.day) actual_date,
        pp.period::int AS period,
        count(*)::int AS quantity
    FROM
        permission_packages pp
            JOIN user_permission_packages upp ON upp."permissionPackageId" = pp.id
            INNER JOIN tariffs t ON t."id" = pp."tariffId" AND t.source = 'marketguru'
            join d on pp.updated <= d.day
    WHERE
        upp."startDate" < d.day AND
        upp."endDate" > d.day AND
        upp.status = 'active' AND
        upp.deleted IS NULL AND
        pp."tariffId" IS NOT NULL
    GROUP BY 1,2
),
grouped AS (
    SELECT
        tgd.name,
        p.period,
        p.quantity,
        COALESCE(tgd.day, (
            SELECT MIN(day)
            FROM tariff_group_days
            WHERE day > p.period)
        ) AS nearest_main,
        p.actual_date
    FROM
        periods p
            LEFT JOIN tariff_group_days tgd ON p.period = tgd.day AND tgd.source = 'marketguru'
),
t as (
    select
        actual_date,
        case
            WHEN period = nearest_main THEN name::text
            WHEN period < nearest_main THEN '< ' || nearest_main
            ELSE (
                SELECT '> ' || name
                FROM tariff_group_days
                WHERE source = 'marketguru'
                ORDER BY day DESC
                LIMIT 1)
            END AS period_name,
        sum(quantity)::int AS cnt
    FROM grouped
    GROUP BY 1,2
)
select * from t LIMIT 5;
```

**Запишите типы колонок:**
- actual_date: ?
- period_name: ?
- cnt: ?

#### 1.5. MG Churn
```sql
with sorted as (
    select
        "userId"  user_id,
        "startDate"  start_dt,
        "endDate" end_dt,
        max("endDate") over (
            partition by "userId"
            order by "startDate"
            rows between unbounded preceding and 1 preceding
        ) as max_prev_end
    from user_permission_packages
    where "startDate" >= '2024-01-01'
),
flagged as (
    select
        user_id,
        start_dt,
        end_dt,
        max_prev_end,
        case
            when max_prev_end is null then 1
            when start_dt > max_prev_end then 1
            else 0
        end as is_new_chunk
    from sorted
),
chunked as (
    select
        user_id,
        start_dt,
        end_dt,
        sum(is_new_chunk) over (partition by user_id order by start_dt rows unbounded preceding) as chunk_id
    from flagged
),
merged as (
    select
        user_id,
        min(start_dt) as period_start,
        max(end_dt)   as period_end
    from chunked
    group by user_id, chunk_id
),
with_next as (
    select
        m.*,
        lead(period_start) over (partition by user_id order by period_start) as next_start
    from merged m
)
select
    user_id,
    period_end::date   as churn_date,
    next_start::date   as return_date,
    extract(days from coalesce(next_start, now()) - period_end) as gap_interval
from with_next
where period_end < now() - interval '30 days'
  and ((next_start - period_end) > interval '30 days' and next_start <= now() or next_start is null)
LIMIT 5;
```

**Запишите типы колонок:**
- user_id: ?
- churn_date: ?
- return_date: ?
- gap_interval: ?

#### 1.6. Event Backend
```sql
select 
  id user_id,
  ("created" at time zone 'MSK')::date event_date,
  'registration' event_name
from users
WHERE 'marketguru' = ANY (source)
LIMIT 3

UNION ALL

select
  "userId" user_id,
  ("startDate" at time zone 'MSK')::date event_date,
  'trial' event_name
from user_permission_packages
where "sourceType" in ('trial')
and "startDate" >= '2025-01-01'
LIMIT 3;
```

**Запишите типы колонок:**
- user_id: ?
- event_date: ?
- event_name: ?

---

### Шаг 2: Проверить критичные моменты в PostgreSQL

#### 2.1. Проверить поле sourceType
```sql
-- Какое поле существует?
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'user_permission_packages' 
AND column_name IN ('type', 'sourceType');

-- Какие значения?
SELECT DISTINCT "sourceType" FROM user_permission_packages LIMIT 20;
-- ИЛИ
SELECT DISTINCT "type" FROM user_permission_packages LIMIT 20;
```

**Запишите результат:** _____________

#### 2.2. Проверить часовой пояс MSK
```sql
SELECT now() AT TIME ZONE 'MSK';
```

**Работает?** ☐ ДА ☐ НЕТ (если нет, использовать 'Europe/Moscow')

#### 2.3. Проверить объёмы данных
```sql
SELECT 
    (SELECT COUNT(*) FROM users WHERE 'marketguru' = ANY(source)) AS users_count,
    (SELECT COUNT(*) FROM "Payments" WHERE source = 'marketguru' AND updated >= '2024-01-01') AS payments_count,
    (SELECT COUNT(*) FROM user_permission_packages WHERE "startDate" >= '2024-01-01') AS upp_count;
```

**Запишите результат:**
- users: _____________
- payments: _____________
- user_permission_packages: _____________

---

### Шаг 3: Скорректировать типы данных в ClickHouse (если нужно)

На основании Шага 1, проверьте соответствие типов в файле `clickhouse_mg_reporting_schema.sql`:

**Если типы не совпадают**, исправьте определения таблиц в секции "СЕКЦИЯ 3: DM-СЛОЙ".

Например:
- Если в PG `bigint` → в CH может быть `Int64` или `UInt64`
- Если в PG `numeric` → в CH `Decimal(18,2)`
- Если в PG `double precision` → в CH `Float64`

---

### Шаг 4: Запустить скрипт в ClickHouse

```bash
clickhouse-client --host <your_host> --user <user> < clickhouse_mg_reporting_schema.sql
```

или

```sql
-- Подключиться к ClickHouse и выполнить весь скрипт
```

---

### Шаг 5: Загрузить тестовые данные (см. README_CLICKHOUSE_SETUP.md)

---

### Шаг 6: Проверить результаты

Сравните COUNT и SUM между PostgreSQL и ClickHouse:

```sql
-- В PostgreSQL (исходный запрос payments)
with t as (
    select
        ("updated" at time zone 'MSK')::date event_date,
        count(case when "purposeOfPayment" <> 'refund' then id end) total_payment_attempts,
        sum(case when "purposeOfPayment" <> 'refund' and state = 'completed' 
            then "amount" end) total_revenue
    from  "Payments" p
    WHERE p.state <> 'split' 
        AND ("updated" at time zone 'MSK')::date >= '2024-01-01'
        and p."source"  = 'marketguru'
    group by 1
)
select sum(total_payment_attempts), sum(total_revenue) from t;
```

```sql
-- В ClickHouse
SELECT 
    sum(total_payment_attempts),
    sum(total_revenue)
FROM mg_dm.payments_daily;
```

**Должны ПОЛНОСТЬЮ совпадать!**

---

## ⚠️ КРИТИЧНЫЕ МОМЕНТЫ

### 1. sourceType vs type
- ❗ В RAW-таблице mg_raw.user_permission_packages есть ОБА поля
- ❗ Уточните у команды, какое использовать
- ❗ Возможно, нужно будет скорректировать запросы

### 2. Исправлена ошибка в packages-by-tariff
- ✅ Заменено `now()` на `dr.day` в условиях WHERE
- ✅ Теперь запрос корректно считает активные пакеты на каждый день

### 3. Материализованные представления
- ✅ Созданы только для 2 простых отчётов: users, payments
- ⚠️ Остальные 4 отчёта требуют ETL-процесса (слишком сложные для MV)

---

## 📋 Финальная таблица соответствия

| Отчёт | Логика PostgreSQL | Логика ClickHouse | Статус |
|-------|-------------------|-------------------|--------|
| payments | ✅ Исходная | ✅ Сохранена | ✅ ГОТОВО |
| users | ✅ Исходная | ✅ Сохранена | ✅ ГОТОВО |
| packages-by-tariff | ✅ Исходная | ✅ Исправлена | ✅ ГОТОВО |
| packages-by-period | ✅ Исходная | ✅ Сохранена | ✅ ГОТОВО |
| mg_churn | ✅ Исходная | ✅ Сохранена | ✅ ГОТОВО |
| event_backend | ✅ Исходная | ✅ Сохранена | ✅ ГОТОВО |

---

## 🎯 Готово к запуску!

После выполнения Шагов 1-3, скрипт готов к развёртыванию в ClickHouse.

**Файлы для использования:**
1. `clickhouse_mg_reporting_schema.sql` - основной скрипт (ИСПРАВЛЕН ✅)
2. `README_CLICKHOUSE_SETUP.md` - инструкция по запуску
3. `LOGIC_VALIDATION_AND_TEST_QUERIES.md` - детальная проверка каждого запроса

**Успехов! 🚀**

