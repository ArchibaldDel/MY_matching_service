# 📊 Таблица соответствия полей: PostgreSQL → ClickHouse

## Назначение документа
Этот документ показывает **точное соответствие** между:
- Исходными запросами PostgreSQL
- RAW-таблицами ClickHouse (mg_raw.*)
- Финальными витринами ClickHouse (mg_dm.*)

---

## 1️⃣ Отчёт: PAYMENTS

### Исходные таблицы PostgreSQL:
- `public."Payments"`

### Используемые поля в запросе:
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `id` | uuid | COUNT условный |
| `updated` | timestamptz | Группировка по дате, фильтр >= 2024-01-01 |
| `purposeOfPayment` | varchar(255) | Классификация типа платежа |
| `state` | varchar(255) | Фильтр completed/split |
| `amount` | numeric(12,2) | Суммирование выручки |
| `source` | enum_resource | Фильтр = 'marketguru' |

### RAW-таблица ClickHouse:
```sql
CREATE TABLE mg_raw.payments (
    payment_id       UUID,           -- id из PG
    updated          DateTime,       -- updated из PG
    completedDate    Nullable(DateTime), -- не используется в этом отчёте
    purposeOfPayment String,         -- purposeOfPayment из PG
    amount           Decimal(12, 2), -- amount из PG
    state            String,         -- state из PG
    source           String,         -- source из PG
    user_id          UUID            -- userId из PG (для других отчётов)
);
```

### Финальная витрина ClickHouse:
```sql
CREATE TABLE mg_dm.payments_daily (
    event_date             Date,          -- из updated (группировка)
    total_payment_attempts UInt64,        -- COUNT(id) где purposeOfPayment <> 'refund'
    completed_payments     UInt64,        -- COUNT(id) где purposeOfPayment <> 'refund' AND state = 'completed'
    refunds                UInt64,        -- COUNT(id) где purposeOfPayment = 'refund' AND state = 'completed'
    total_revenue          Decimal(18,2), -- SUM(amount) где purposeOfPayment <> 'refund' AND state = 'completed'
    tariff_revenue         Decimal(18,2), -- SUM(amount) где state = 'completed' AND purposeOfPayment IN (...)
    ap_revenue             Decimal(18,2), -- SUM(amount) где state = 'completed' AND purposeOfPayment = 'buyAdditionalPackages'
    refund_amount          Decimal(18,2)  -- -SUM(amount) где purposeOfPayment = 'refund' AND state = 'completed'
);
```

### Где прогнать для проверки типов:
```sql
-- В PostgreSQL:
with t as (
    select
        ("updated" at time zone 'MSK')::date event_date,
        count(case when "purposeOfPayment" <> 'refund' then id end) total_payment_attempts,
        count(case when "purposeOfPayment" <> 'refund' and state = 'completed' then id end) completed_payments,
        count(case when "purposeOfPayment" = 'refund' and state = 'completed' then id end) refunds,
        sum(case when "purposeOfPayment" <> 'refund' and state = 'completed' then "amount" end) total_revenue,
        sum(case when state = 'completed' and "purposeOfPayment" in ('upgradeTariffPackage', 'upsaleTariffPackage', 'buyTariffPackage', 'buyTariffAndAdditionalPackages') then "amount" else 0 end) tariff_revenue,
        sum(case when state = 'completed' and "purposeOfPayment" in ('buyAdditionalPackages') then "amount" else 0 end) ap_revenue,
        sum(case when "purposeOfPayment" = 'refund' and state = 'completed' then -"amount" else 0 end) refund_amount
    from "Payments" p
    WHERE p.state <> 'split' AND ("updated" at time zone 'MSK')::date >= '2024-01-01' and p."source" = 'marketguru'
    group by 1
)
select * from t LIMIT 5;

-- Посмотреть на типы колонок в результате!
```

---

## 2️⃣ Отчёт: USERS

### Исходные таблицы PostgreSQL:
- `public.users`

### Используемые поля в запросе:
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `id` | uuid | Идентификатор пользователя (→ user_id) |
| `created` | timestamptz | Дата регистрации (→ entryDate) |
| `source` | array/enum[] | Фильтр 'marketguru' = ANY(source) |
| `deleted` | timestamptz | Фильтр IS NULL (не удалённые) |

### RAW-таблица ClickHouse:
```sql
CREATE TABLE mg_raw.users (
    user_id UUID,              -- id из PG
    created DateTime,          -- created из PG
    source  Array(String),     -- source из PG (массив)
    deleted Nullable(DateTime) -- deleted из PG
);
```

### Финальная витрина ClickHouse:
```sql
CREATE TABLE mg_dm.users_entry (
    user_id   UUID,  -- из id
    entryDate Date   -- из created::Date
);
```

### Где прогнать для проверки типов:
```sql
-- В PostgreSQL:
SELECT 
    id as user_id, 
    created::Date AS "entryDate"
FROM users
WHERE 'marketguru' = ANY (source) AND deleted IS NULL and created::Date >= '2024-01-01'
LIMIT 5;

-- Посмотреть на типы колонок в результате!
```

---

## 3️⃣ Отчёт: PACKAGES-BY-TARIFF

### Исходные таблицы PostgreSQL:
- `public.permission_packages`
- `public.user_permission_packages`
- `public.tariffs`

### Используемые поля в запросе:

#### permission_packages:
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `id` | uuid | JOIN с upp.permissionPackageId |
| `tariffId` | uuid | JOIN с tariffs.id, фильтр IS NOT NULL |
| `updated` | timestamptz | Фильтр <= d.day (пакет существовал на дату) |

#### user_permission_packages:
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `permissionPackageId` | uuid | JOIN с pp.id |
| `startDate` | timestamptz | Фильтр < d.day (активен на дату) |
| `endDate` | timestamptz | Фильтр > d.day (активен на дату) |
| `status` | varchar(255) | Фильтр = 'active' |
| `deleted` | timestamptz | Фильтр IS NULL |
| `sourceType` | varchar(255) | Классификация paid/gift/trial |

#### tariffs:
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `id` | uuid | JOIN с pp.tariffId |
| `name` | varchar(255) | Название тарифа (→ результат) |
| `source` | enum_resource | Фильтр = 'marketguru' |

### RAW-таблицы ClickHouse:
```sql
CREATE TABLE mg_raw.permission_packages (
    id        UUID,
    period    Nullable(Int16),  -- для packages-by-period
    tariff_id Nullable(UUID),
    updated   DateTime
);

CREATE TABLE mg_raw.user_permission_packages (
    id                  UUID,
    user_id             UUID,
    permissionPackageId UUID,
    status              String,
    startDate           DateTime,
    endDate             Nullable(DateTime),
    pausedStartDate     Nullable(DateTime),
    pausedEndDate       Nullable(DateTime),
    type                String,
    sourceType          String,
    deleted             Nullable(DateTime),
    created             DateTime,
    updated             DateTime
);

CREATE TABLE mg_raw.tariffs (
    id     UUID,
    name   String,
    source String
);
```

### Финальная витрина ClickHouse:
```sql
CREATE TABLE mg_dm.packages_by_tariff (
    actual_date Date,     -- день из generate_series
    tariff_name String,   -- t.name
    sourceType  String,   -- классификация: paid/gift/trial
    cnt         UInt32    -- COUNT(*) активных пакетов
);
```

### Где прогнать для проверки типов:
```sql
-- В PostgreSQL:
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
    FROM permission_packages pp
        JOIN user_permission_packages upp ON upp."permissionPackageId" = pp.id
        INNER JOIN tariffs t ON t."id" = pp."tariffId" and t.source = 'marketguru'
        join d on pp.updated <= d.day
    WHERE upp."startDate" < d.day AND upp."endDate" > d.day AND upp.status = 'active' AND upp.deleted IS NULL AND pp."tariffId" IS NOT null
    GROUP BY 1,2,3
)
select * from tt LIMIT 5;

-- Посмотреть на типы колонок в результате!
```

---

## 4️⃣ Отчёт: PACKAGES-BY-PERIOD

### Исходные таблицы PostgreSQL:
- `public.permission_packages`
- `public.user_permission_packages`
- `public.tariffs`
- `public.tariff_group_days`

### Дополнительные поля (tariff_group_days):
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `day` | int4 | Маппинг period → название группы |
| `name` | varchar(255) | Название группы периодов (30/60/90) |
| `source` | enum_resource | Фильтр = 'marketguru' |
| `isEnabled` | bool | Не используется в запросе, но есть в таблице |
| `isDefault` | bool | Не используется в запросе, но есть в таблице |

### RAW-таблицы ClickHouse:
```sql
-- (те же, что в packages-by-tariff + tariff_group_days)

CREATE TABLE mg_raw.tariff_group_days (
    day       Int32,
    name      String,
    source    String,
    isEnabled UInt8,
    isDefault UInt8
);
```

### Финальная витрина ClickHouse:
```sql
CREATE TABLE mg_dm.packages_by_period (
    actual_date Date,      -- день из generate_series
    period_name String,    -- название периода: "30", "< 60", "> 90"
    cnt         UInt32     -- SUM(quantity) пакетов
);
```

### Где прогнать для проверки типов:
```sql
-- В PostgreSQL (запрос большой, см. LOGIC_VALIDATION_AND_TEST_QUERIES.md)
-- Секция "4️⃣ Отчёт: PACKAGES-BY-PERIOD"
```

---

## 5️⃣ Отчёт: MG_CHURN

### Исходные таблицы PostgreSQL:
- `public.user_permission_packages`

### Используемые поля в запросе:
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `userId` | uuid | Группировка по пользователю |
| `startDate` | timestamptz | Начало периода, фильтр >= 2024-01-01 |
| `endDate` | timestamptz | Конец периода, вычисление разрывов |

### RAW-таблица ClickHouse:
```sql
-- Используется mg_raw.user_permission_packages (см. выше)
-- Нужны только 3 поля: user_id, startDate, endDate
```

### Финальная витрина ClickHouse:
```sql
CREATE TABLE mg_dm.mg_churn (
    user_id      UUID,            -- userId
    churn_date   Date,            -- period_end::date (дата оттока)
    return_date  Nullable(Date),  -- next_start::date (дата возврата или NULL)
    gap_interval Int32            -- количество дней разрыва
);
```

### Где прогнать для проверки типов:
```sql
-- В PostgreSQL (запрос большой с CTE, см. LOGIC_VALIDATION_AND_TEST_QUERIES.md)
-- Секция "5️⃣ Отчёт: MG_CHURN"
```

---

## 6️⃣ Отчёт: EVENT_BACKEND

### Исходные таблицы PostgreSQL:
- `public.users`
- `public.user_permission_packages`
- `public."Payments"`

### Используемые поля в запросе:

#### Событие 1: registration (из users)
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `id` | uuid | → user_id |
| `created` | timestamptz | → event_date |

#### Событие 2: trial (из user_permission_packages)
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `userId` | uuid | → user_id |
| `startDate` | timestamptz | → event_date |
| `sourceType` | varchar(255) | Фильтр IN ('trial') |

#### Событие 3: first_pay_tariff (из user_permission_packages)
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `userId` | uuid | → user_id |
| `startDate` | timestamptz | → event_date |
| `sourceType` | varchar(255) | Фильтр IN ('payment', 'upgrade', 'paidCoupon') |
| `endDate` | timestamptz | Вычисление длительности gift (> 29 дней = paid) |

#### Событие 4: first_pay_ap (из Payments)
| Поле в PostgreSQL | Тип в PG | Используется для |
|-------------------|----------|------------------|
| `userId` | uuid | → user_id |
| `completedDate` | timestamptz | → event_date |
| `purposeOfPayment` | varchar(255) | Фильтр IN ('buyAdditionalPackages', 'buyTariffAndAdditionalPackages') |
| `state` | varchar(255) | Фильтр = 'completed' |
| `source` | enum_resource | Фильтр = 'marketguru' |
| `updated` | timestamptz | Фильтр >= 2024-01-01 |

### RAW-таблицы ClickHouse:
```sql
-- Используются 3 таблицы:
-- mg_raw.users
-- mg_raw.user_permission_packages
-- mg_raw.payments
```

### Финальная витрина ClickHouse:
```sql
CREATE TABLE mg_dm.user_events (
    user_id    UUID,
    event_date Date,
    event_name String  -- 'registration', 'trial', 'first_pay_tariff', 'first_pay_ap'
);
```

### Где прогнать для проверки типов:
```sql
-- В PostgreSQL:
select id user_id, ("created" at time zone 'MSK')::date event_date, 'registration' event_name from users LIMIT 3
UNION ALL
select "userId" user_id, ("startDate" at time zone 'MSK')::date event_date, 'trial' event_name 
from user_permission_packages where "sourceType" in ('trial') LIMIT 3;

-- Посмотреть на типы колонок в результате!
```

---

## 📋 Сводная таблица: какие таблицы для каких отчётов

| Отчёт | Таблицы PostgreSQL | RAW-таблицы ClickHouse | Финальная витрина ClickHouse |
|-------|-------------------|------------------------|------------------------------|
| **payments** | Payments | mg_raw.payments | mg_dm.payments_daily |
| **users** | users | mg_raw.users | mg_dm.users_entry |
| **packages-by-tariff** | permission_packages, user_permission_packages, tariffs | mg_raw.permission_packages, mg_raw.user_permission_packages, mg_raw.tariffs | mg_dm.packages_by_tariff |
| **packages-by-period** | permission_packages, user_permission_packages, tariffs, tariff_group_days | mg_raw.permission_packages, mg_raw.user_permission_packages, mg_raw.tariffs, mg_raw.tariff_group_days | mg_dm.packages_by_period |
| **mg_churn** | user_permission_packages | mg_raw.user_permission_packages | mg_dm.mg_churn |
| **event_backend** | users, user_permission_packages, Payments | mg_raw.users, mg_raw.user_permission_packages, mg_raw.payments | mg_dm.user_events |

---

## 🎯 Как использовать эту таблицу

### Для заполнения RAW-таблиц:

1. Для каждой RAW-таблицы посмотрите в колонке "Используемые поля в запросе"
2. Выберите эти поля из PostgreSQL
3. Вставьте в соответствующую RAW-таблицу ClickHouse

**Пример для mg_raw.payments:**
```sql
-- В PostgreSQL экспортировать:
SELECT 
    id, updated, "completedDate", "purposeOfPayment", 
    amount, state, source::text, "userId"
FROM "Payments"
WHERE source = 'marketguru' AND updated >= '2024-01-01';

-- Импортировать в ClickHouse:
INSERT INTO mg_raw.payments FORMAT CSV ...
```

### Для проверки типов витрин:

1. Найдите секцию "Где прогнать для проверки типов" для нужного отчёта
2. Выполните запрос в PostgreSQL с LIMIT 5
3. Посмотрите на типы колонок в результате
4. Сверьте с типами в "Финальная витрина ClickHouse"
5. Если не совпадают - скорректируйте DDL таблицы в `clickhouse_mg_reporting_schema.sql`

---

## ⚠️ Важные замечания

### 1. Поле sourceType
В таблице `user_permission_packages` используется поле `sourceType`, но в DDL на скриншотах видно поле `type`.

**Что делать:**
```sql
-- Проверить в PostgreSQL:
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'user_permission_packages' 
AND column_name IN ('type', 'sourceType');
```

Если поле называется `type`, а не `sourceType`, то при заполнении RAW-таблицы нужно:
```sql
-- Вариант 1: Алиас при загрузке
SELECT ..., "type" AS sourceType FROM user_permission_packages

-- Вариант 2: Заполнить оба поля одинаковыми данными
SELECT ..., "type" AS type, "type" AS sourceType FROM user_permission_packages
```

### 2. Часовой пояс
В запросах используется `AT TIME ZONE 'MSK'`, в ClickHouse - `'Europe/Moscow'`.

### 3. Материализованные представления
Созданы только для 2 отчётов (users, payments). Остальные 4 требуют ETL-скриптов из-за сложности.

---

**Готово к использованию!**

