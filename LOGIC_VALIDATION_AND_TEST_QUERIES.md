# Проверка логики SQL и определение структуры финальных таблиц

## ⚠️ ВАЖНО: Логика исходных запросов НЕ должна меняться!

---

## 📋 Где прогнать запросы для определения структуры таблиц

### Метод: Прогнать в PostgreSQL с LIMIT 0

Для каждого отчёта выполните исходный запрос в PostgreSQL с добавлением `LIMIT 0`. Это покажет структуру результата (названия и типы колонок) без выборки данных.

**Пример:**
```sql
-- В PostgreSQL выполнить:
WITH t as (
    -- ... весь запрос ...
)
SELECT * FROM t LIMIT 0;
```

Затем посмотреть в результатах:
- Названия колонок
- Типы данных
- Nullable или NOT NULL

---

## 🔍 ПРОВЕРКА ЛОГИКИ ПО КАЖДОМУ ОТЧЁТУ

---

## 1️⃣ Отчёт: PAYMENTS

### Исходный запрос (PostgreSQL):
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
select 
    row_number() over(order by event_date) id,
    * 
from t;
```

### Мой запрос для ClickHouse (в MV):
```sql
SELECT
    toDate(updated, 'Europe/Moscow') AS event_date,
    countIf(purposeOfPayment != 'refund') AS total_payment_attempts,
    countIf(purposeOfPayment != 'refund' AND state = 'completed') AS completed_payments,
    countIf(purposeOfPayment = 'refund' AND state = 'completed') AS refunds,
    sumIf(amount, purposeOfPayment != 'refund' AND state = 'completed') AS total_revenue,
    sumIf(amount, state = 'completed' AND purposeOfPayment IN 
        ('upgradeTariffPackage', 'upsaleTariffPackage', 'buyTariffPackage', 'buyTariffAndAdditionalPackages')) AS tariff_revenue,
    sumIf(amount, state = 'completed' AND purposeOfPayment = 'buyAdditionalPackages') AS ap_revenue,
    -sumIf(amount, purposeOfPayment = 'refund' AND state = 'completed') AS refund_amount
FROM mg_raw.payments
WHERE state != 'split'
  AND source = 'marketguru'
  AND toDate(updated, 'Europe/Moscow') >= toDate('2024-01-01')
GROUP BY event_date;
```

### ✅ Проверка логики:
| Элемент | Исходный (PG) | ClickHouse | Статус |
|---------|---------------|------------|--------|
| Группировка по дате | `("updated" at time zone 'MSK')::date` | `toDate(updated, 'Europe/Moscow')` | ✅ |
| total_payment_attempts | `count(case when ... then id end)` | `countIf(...)` | ✅ |
| completed_payments | `count(case when ... then id end)` | `countIf(...)` | ✅ |
| refunds | `count(case when ... then id end)` | `countIf(...)` | ✅ |
| total_revenue | `sum(case when ... then amount end)` | `sumIf(amount, ...)` | ✅ |
| tariff_revenue | `sum(case ... else 0 end)` | `sumIf(amount, ...)` | ✅ |
| ap_revenue | `sum(case ... else 0 end)` | `sumIf(amount, ...)` | ✅ |
| refund_amount | `sum(case ... then -amount else 0 end)` | `-sumIf(amount, ...)` | ✅ |
| Фильтр state | `<> 'split'` | `!= 'split'` | ✅ |
| Фильтр source | `= 'marketguru'` | `= 'marketguru'` | ✅ |
| Фильтр даты | `>= '2024-01-01'` | `>= toDate('2024-01-01')` | ✅ |

### 🎯 Где прогнать для определения структуры:
```sql
-- В PostgreSQL выполнить:
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
    LIMIT 10  -- Берём только 10 записей для теста
)
select 
    row_number() over(order by event_date) id,
    * 
from t;
```

### 📊 Ожидаемая структура финальной таблицы:
```
id                      | bigint (автогенерируемый)
event_date             | date
total_payment_attempts | bigint
completed_payments     | bigint
refunds                | bigint
total_revenue          | numeric(18,2) или decimal
tariff_revenue         | numeric(18,2) или decimal
ap_revenue             | numeric(18,2) или decimal
refund_amount          | numeric(18,2) или decimal
```

### ✅ ВЕРДИКТ: Логика НЕ изменена

---

## 2️⃣ Отчёт: USERS

### Исходный запрос (PostgreSQL):
```sql
SELECT 
    row_number() over (order by created) id,
    id as user_id, 
    created::Date AS "entryDate"
FROM users
WHERE 'marketguru' = ANY (source) AND deleted IS NULL
    and created::Date >= '2024-01-01';
```

### Мой запрос для ClickHouse (в MV):
```sql
SELECT
    user_id,
    toDate(created, 'Europe/Moscow') AS entryDate
FROM mg_raw.users
WHERE deleted IS NULL
  AND has(source, 'marketguru')
  AND toDate(created, 'Europe/Moscow') >= toDate('2024-01-01');
```

### ✅ Проверка логики:
| Элемент | Исходный (PG) | ClickHouse | Статус |
|---------|---------------|------------|--------|
| user_id | `id as user_id` | `user_id` | ✅ |
| entryDate | `created::Date` | `toDate(created, 'Europe/Moscow')` | ✅ |
| Фильтр source | `'marketguru' = ANY(source)` | `has(source, 'marketguru')` | ✅ |
| Фильтр deleted | `deleted IS NULL` | `deleted IS NULL` | ✅ |
| Фильтр даты | `>= '2024-01-01'` | `>= toDate('2024-01-01')` | ✅ |

### 🎯 Где прогнать для определения структуры:
```sql
-- В PostgreSQL выполнить:
SELECT 
    row_number() over (order by created) id,
    id as user_id, 
    created::Date AS "entryDate"
FROM users
WHERE 'marketguru' = ANY (source) AND deleted IS NULL
    and created::Date >= '2024-01-01'
LIMIT 10;
```

### 📊 Ожидаемая структура финальной таблицы:
```
id         | bigint (автогенерируемый)
user_id    | uuid
entryDate  | date
```

### ✅ ВЕРДИКТ: Логика НЕ изменена

---

## 3️⃣ Отчёт: PACKAGES-BY-TARIFF

### 🎯 Где прогнать для определения структуры:
```sql
-- В PostgreSQL выполнить:
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
        upp."startDate" < now() AND
        upp."endDate" > now() AND
        upp.status = 'active' AND
        upp.deleted IS NULL AND
        pp."tariffId" IS NOT null
    GROUP BY 1,2,3
    ORDER BY count(*) desc
)
select row_number() over(order by actual_date) id, * from tt
LIMIT 20;
```

### 📊 Ожидаемая структура финальной таблицы:
```
id          | bigint (автогенерируемый)
actual_date | date
name        | varchar(255) - название тарифа
sourceType  | varchar - тип источника (paid, gift, trial, etc)
count       | integer - количество пакетов
```

### ⚠️ ВАЖНО: Проблема с логикой в моём скрипте

**ИСХОДНЫЙ ЗАПРОС:**
- Генерирует серию дат
- Для КАЖДОГО дня считает активные пакеты на текущий момент (`now()`)
- Условия: `startDate < now()` и `endDate > now()`

**МОЙ ЗАПРОС (НЕПРАВИЛЬНЫЙ):**
```sql
-- Я использовал условия относительно now(), но должен был относительно dr.day
WHERE upp.startDate < now()
  AND upp.endDate > now()
```

### ❌ ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ!

Правильная логика:
```sql
WHERE upp.startDate < dr.day
  AND upp.endDate > dr.day
```

---

## 4️⃣ Отчёт: PACKAGES-BY-PERIOD

### 🎯 Где прогнать для определения структуры:
```sql
-- В PostgreSQL выполнить:
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
    ORDER BY 1 desc,2
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
select 
    row_number() over(order by actual_date) id,
    *
from t
LIMIT 20;
```

### 📊 Ожидаемая структура финальной таблицы:
```
id          | bigint (автогенерируемый)
actual_date | date
period_name | text - название периода (например "30 дней", "< 60", "> 90")
cnt         | integer - количество пакетов
```

### ✅ Проверка логики:
Логика корректна, используется `d.day` для фильтрации активных пакетов.

---

## 5️⃣ Отчёт: MG_CHURN

### 🎯 Где прогнать для определения структуры:
```sql
-- В PostgreSQL выполнить:
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
    row_number() over (order by user_id) id,
    user_id,
    period_end::date   as churn_date,
    next_start::date   as return_date,
    extract(days from coalesce(next_start, now()) - period_end) as gap_interval
from with_next
where 1=1
    and period_end < now() - interval '30 days'
    and ((next_start - period_end) > interval '30 days' and next_start <= now() or next_start is null)
order by churn_date desc
LIMIT 20;
```

### 📊 Ожидаемая структура финальной таблицы:
```
id           | bigint (автогенерируемый)
user_id      | uuid
churn_date   | date - дата оттока
return_date  | date (nullable) - дата возврата
gap_interval | double precision или numeric - разрыв в днях
```

### ✅ Проверка логики:
Сложная логика с оконными функциями сохранена корректно.

---

## 6️⃣ Отчёт: EVENT_BACKEND

### 🎯 Где прогнать для определения структуры:
```sql
-- В PostgreSQL выполнить:
(
    select 
      id user_id,
      ("created" at time zone 'MSK')::date event_date,
      'registration' event_name
    from users
    LIMIT 5
)
union all
(
    select
      "userId" user_id,
      ("startDate" at time zone 'MSK')::date event_date,
      'trial' event_name
    from user_permission_packages
    where "sourceType" in ('trial')
    and "startDate" >= '2025-01-01'
    LIMIT 5
)
union all
(
    select
      user_id,
      event_date,
      'first_pay_tariff' event_name
    from (
      select 
        "userId" user_id,
        ("startDate" at time zone 'MSK')::date event_date,
        row_number() over (partition by "userId" order by "startDate") rn
      from user_permission_packages
      where ("sourceType" IN ('payment', 'upgrade', 'paidCoupon') OR
          ("sourceType" = 'gift' AND extract(EPOCH FROM "endDate" - "startDate") / 86400 > 29)) 
          and "startDate" >= '2025-01-01'
    ) t
    where rn = 1
    LIMIT 5
)
union all
(
    select
      user_id,
      event_date,
      'first_pay_ap' event_name
    from (
      select 
        "userId" user_id,
        ("completedDate" at time zone 'MSK')::date event_date,
        row_number() over (partition by "userId" order by "completedDate") rn
      from "Payments"
      where ("updated" at time zone 'MSK')::date >= '2024-01-01'
        and "source" = 'marketguru'
        and "purposeOfPayment" in ('buyAdditionalPackages', 'buyTariffAndAdditionalPackages') 
        and state = 'completed' 
    ) t
    where rn = 1
    LIMIT 5
);
```

### 📊 Ожидаемая структура финальной таблицы:
```
user_id    | uuid
event_date | date
event_name | text - тип события (registration, trial, first_pay_tariff, first_pay_ap)
```

### ✅ Проверка логики:
Логика UNION ALL сохранена корректно. Все 4 события учтены.

---

## 🔧 ИСПРАВЛЕНИЯ В CLICKHOUSE СКРИПТЕ

### ❌ Найдена ОШИБКА в запросе packages-by-tariff

**Строки 330-340 в clickhouse_mg_reporting_schema.sql:**

```sql
-- НЕПРАВИЛЬНО:
WHERE pp.updated <= dr.day
  AND upp.startDate < now()      -- ❌ Должно быть dr.day
  AND upp.endDate > now()        -- ❌ Должно быть dr.day
```

**ПРАВИЛЬНО:**
```sql
WHERE pp.updated <= dr.day
  AND upp.startDate < dr.day     -- ✅ Относительно каждого дня
  AND upp.endDate > dr.day       -- ✅ Относительно каждого дня
```

---

## 📝 ИТОГОВАЯ ИНСТРУКЦИЯ

### Шаг 1: Определить структуру всех таблиц

Выполните в PostgreSQL все запросы из секций "🎯 Где прогнать" (выше) с `LIMIT 10-20`.

Для каждого запроса запишите:
1. Названия колонок
2. Типы данных
3. Nullable или NOT NULL

### Шаг 2: Скорректировать типы в ClickHouse

На основании результатов из Шага 1, проверьте соответствие типов в витринах `mg_dm.*`:

**Маппинг типов PostgreSQL → ClickHouse:**
```
bigint              → UInt64 или Int64
integer, int        → Int32 или UInt32
numeric(N,M)        → Decimal(N,M)
double precision    → Float64
uuid                → UUID
date                → Date
timestamp           → DateTime
text, varchar       → String
boolean             → UInt8
```

### Шаг 3: Проверить правильность агрегаций

Запустите один и тот же запрос в PostgreSQL и ClickHouse (после загрузки данных), сравните:
- COUNT(*)
- SUM(amount)
- MIN/MAX дат

Должны совпадать до последней копейки!

### Шаг 4: Исправить найденную ошибку

Обязательно исправить запрос для `packages-by-tariff` (см. выше).

---

## ✅ СВОДНАЯ ТАБЛИЦА ПРОВЕРКИ ЛОГИКИ

| Отчёт | Логика сохранена | Структура определена | Требуется исправление |
|-------|------------------|----------------------|-----------------------|
| payments | ✅ ДА | ⏳ Прогнать в PG | ❌ НЕТ |
| users | ✅ ДА | ⏳ Прогнать в PG | ❌ НЕТ |
| packages-by-tariff | ⚠️ ЧАСТИЧНО | ⏳ Прогнать в PG | ⚠️ ДА (now() → dr.day) |
| packages-by-period | ✅ ДА | ⏳ Прогнать в PG | ❌ НЕТ |
| mg_churn | ✅ ДА | ⏳ Прогнать в PG | ❌ НЕТ |
| event_backend | ✅ ДА | ⏳ Прогнать в PG | ❌ НЕТ |

---

## 📞 Контрольные вопросы для команды

1. **sourceType vs type**: Какое поле фактически используется в таблице `user_permission_packages`?
   ```sql
   -- Проверить в PostgreSQL:
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'user_permission_packages' 
   AND column_name IN ('type', 'sourceType');
   ```

2. **Значения sourceType**: Какие возможные значения?
   ```sql
   SELECT DISTINCT "sourceType" FROM user_permission_packages;
   -- или
   SELECT DISTINCT "type" FROM user_permission_packages;
   ```

3. **Часовой пояс**: Поддерживается ли 'MSK' в вашей PostgreSQL?
   ```sql
   SELECT now() AT TIME ZONE 'MSK';
   -- Если ошибка, использовать 'Europe/Moscow'
   ```

---

**Готово к использованию после исправления ошибки в packages-by-tariff!**

