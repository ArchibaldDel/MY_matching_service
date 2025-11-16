-- ============================================================================
-- ClickHouse Schema для MarketGuru Reporting
-- Дата создания: 2025-11-14
-- ============================================================================
-- 
-- Структура:
-- 1. Создание баз данных (RAW, DM, MV)
-- 2. RAW-слой: копии таблиц из PostgreSQL
-- 3. DM-слой: витрины для отчётов
-- 4. MV-слой: материализованные представления
-- 5. Вспомогательные запросы для проверки
--
-- ============================================================================

-- ============================================================================
-- СЕКЦИЯ 1: СОЗДАНИЕ БАЗ ДАННЫХ
-- ============================================================================

-- База данных для сырых данных из PostgreSQL
CREATE DATABASE IF NOT EXISTS mg_raw;

-- База данных для витрин (Data Marts)
CREATE DATABASE IF NOT EXISTS mg_dm;

-- База данных для материализованных представлений
CREATE DATABASE IF NOT EXISTS mg_mv;

-- ============================================================================
-- СЕКЦИЯ 2: RAW-СЛОЙ (mg_raw.*)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2.1. Таблица mg_raw.users
-- Источник: public.users (PostgreSQL)
-- Используется в отчётах: users, event_backend
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_raw.users
(
    user_id UUID,
    created DateTime,
    source  Array(String),        -- В PG это массив или enum[]
    deleted Nullable(DateTime)
)
ENGINE = MergeTree()
ORDER BY (created, user_id)
COMMENT 'Пользователи MarketGuru из PostgreSQL';


-- ----------------------------------------------------------------------------
-- 2.2. Таблица mg_raw.payments
-- Источник: public."Payments" (PostgreSQL)
-- Используется в отчётах: payments, event_backend
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_raw.payments
(
    payment_id       UUID,
    updated          DateTime,
    completedDate    Nullable(DateTime),
    purposeOfPayment String,
    amount           Decimal(12, 2),
    state            String,
    source           String,
    user_id          UUID
)
ENGINE = MergeTree()
ORDER BY (updated, payment_id)
COMMENT 'Платежи MarketGuru из PostgreSQL';


-- ----------------------------------------------------------------------------
-- 2.3. Таблица mg_raw.permission_packages
-- Источник: public.permission_packages (PostgreSQL)
-- Используется в отчётах: packages-by-tariff, packages-by-period
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_raw.permission_packages
(
    id        UUID,
    period    Nullable(Int16),
    tariff_id Nullable(UUID),
    updated   DateTime
)
ENGINE = MergeTree()
ORDER BY (updated, id)
COMMENT 'Пакеты разрешений из PostgreSQL';


-- ----------------------------------------------------------------------------
-- 2.4. Таблица mg_raw.user_permission_packages
-- Источник: public.user_permission_packages (PostgreSQL)
-- Используется в отчётах: packages-by-tariff, packages-by-period, mg_churn, event_backend
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_raw.user_permission_packages
(
    id                  UUID,
    user_id             UUID,
    permissionPackageId UUID,
    status              String,
    startDate           DateTime,
    endDate             Nullable(DateTime),
    pausedStartDate     Nullable(DateTime),
    pausedEndDate       Nullable(DateTime),
    type                String,
    sourceType          String,          -- Для классификации платных/триальных пакетов
    deleted             Nullable(DateTime),
    created             DateTime,
    updated             DateTime
)
ENGINE = MergeTree()
ORDER BY (user_id, startDate)
COMMENT 'Пакеты пользователей из PostgreSQL';


-- ----------------------------------------------------------------------------
-- 2.5. Таблица mg_raw.tariffs
-- Источник: public.tariffs (PostgreSQL)
-- Используется в отчётах: packages-by-tariff, packages-by-period
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_raw.tariffs
(
    id     UUID,
    name   String,
    source String
)
ENGINE = MergeTree()
ORDER BY (id)
COMMENT 'Тарифы MarketGuru из PostgreSQL';


-- ----------------------------------------------------------------------------
-- 2.6. Таблица mg_raw.tariff_group_days
-- Источник: public.tariff_group_days (PostgreSQL)
-- Используется в отчётах: packages-by-period
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_raw.tariff_group_days
(
    day       Int32,
    name      String,
    source    String,
    isEnabled UInt8,
    isDefault UInt8
)
ENGINE = MergeTree()
ORDER BY (source, day)
COMMENT 'Группировка периодов по дням из PostgreSQL';


-- ============================================================================
-- СЕКЦИЯ 3: DM-СЛОЙ (mg_dm.*) - ВИТРИНЫ ДЛЯ ОТЧЁТОВ
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 3.1. Витрина mg_dm.users_entry
-- Отчёт: users (регистрации пользователей)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_dm.users_entry
(
    user_id   UUID,
    entryDate Date
)
ENGINE = MergeTree()
ORDER BY (entryDate, user_id)
COMMENT 'Витрина: регистрации пользователей MarketGuru';


-- ----------------------------------------------------------------------------
-- 3.2. Витрина mg_dm.payments_daily
-- Отчёт: payments (ежедневная платёжная активность)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_dm.payments_daily
(
    event_date             Date,
    total_payment_attempts UInt64,
    completed_payments     UInt64,
    refunds                UInt64,
    total_revenue          Decimal(18, 2),
    tariff_revenue         Decimal(18, 2),
    ap_revenue             Decimal(18, 2),
    refund_amount          Decimal(18, 2)
)
ENGINE = SummingMergeTree()
ORDER BY event_date
COMMENT 'Витрина: ежедневная платёжная активность';


-- ----------------------------------------------------------------------------
-- 3.3. Витрина mg_dm.packages_by_tariff
-- Отчёт: packages-by-tariff (активные пакеты по тарифам)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_dm.packages_by_tariff
(
    actual_date Date,
    tariff_name String,
    sourceType  String,
    cnt         UInt32
)
ENGINE = SummingMergeTree()
ORDER BY (actual_date, tariff_name, sourceType)
COMMENT 'Витрина: активные пакеты по тарифам и источникам';


-- ----------------------------------------------------------------------------
-- 3.4. Витрина mg_dm.packages_by_period
-- Отчёт: packages-by-period (активные пакеты по периодам)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_dm.packages_by_period
(
    actual_date Date,
    period_name String,
    cnt         UInt32
)
ENGINE = SummingMergeTree()
ORDER BY (actual_date, period_name)
COMMENT 'Витрина: активные пакеты по периодам (30/60/90+ дней)';


-- ----------------------------------------------------------------------------
-- 3.5. Витрина mg_dm.mg_churn
-- Отчёт: mg_churn (анализ оттока/возврата пользователей)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_dm.mg_churn
(
    user_id      UUID,
    churn_date   Date,
    return_date  Nullable(Date),
    gap_interval Int32
)
ENGINE = MergeTree()
ORDER BY (churn_date, user_id)
COMMENT 'Витрина: отток и возврат пользователей';


-- ----------------------------------------------------------------------------
-- 3.6. Витрина mg_dm.user_events
-- Отчёт: event_backend (поток событий пользователей)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_dm.user_events
(
    user_id    UUID,
    event_date Date,
    event_name String
)
ENGINE = MergeTree()
ORDER BY (user_id, event_date, event_name)
COMMENT 'Витрина: события пользователей (registration, trial, first_pay)';


-- ============================================================================
-- СЕКЦИЯ 4: МАТЕРИАЛИЗОВАННЫЕ ПРЕДСТАВЛЕНИЯ (mg_mv.*)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4.1. Материализованное представление для mg_dm.users_entry
-- Автоматически заполняет витрину при вставке в mg_raw.users
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mg_mv.users_entry_mv
TO mg_dm.users_entry
AS
SELECT
    user_id,
    toDate(created, 'Europe/Moscow') AS entryDate
FROM mg_raw.users
WHERE deleted IS NULL
  AND has(source, 'marketguru')
  AND toDate(created, 'Europe/Moscow') >= toDate('2024-01-01');


-- ----------------------------------------------------------------------------
-- 4.2. Материализованное представление для mg_dm.payments_daily
-- Автоматически агрегирует платежи при вставке в mg_raw.payments
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mg_mv.payments_daily_mv
TO mg_dm.payments_daily
AS
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


-- ============================================================================
-- СЕКЦИЯ 5: ВСПОМОГАТЕЛЬНЫЕ ЗАПРОСЫ ДЛЯ ПРОВЕРКИ
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 5.1. Запрос для отчёта "users" с нумерацией строк
-- ----------------------------------------------------------------------------
-- SELECT
--     row_number() OVER (ORDER BY entryDate, user_id) AS id,
--     user_id,
--     entryDate
-- FROM mg_dm.users_entry
-- ORDER BY entryDate;


-- ----------------------------------------------------------------------------
-- 5.2. Запрос для отчёта "payments" с нумерацией строк
-- ----------------------------------------------------------------------------
-- SELECT
--     row_number() OVER (ORDER BY event_date) AS id,
--     event_date,
--     total_payment_attempts,
--     completed_payments,
--     refunds,
--     total_revenue,
--     tariff_revenue,
--     ap_revenue,
--     refund_amount
-- FROM mg_dm.payments_daily
-- ORDER BY event_date;


-- ============================================================================
-- СЕКЦИЯ 6: СЛОЖНЫЕ ЗАПРОСЫ ДЛЯ ВИТРИН (БЕЗ АВТОМАТИЧЕСКОЙ МАТЕРИАЛИЗАЦИИ)
-- ============================================================================
-- Эти запросы требуют сложной логики с оконными функциями и временными таблицами.
-- Рекомендуется запускать их через ETL-процесс (Airflow/cron) с INSERT INTO.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6.1. Запрос для заполнения mg_dm.packages_by_tariff
-- Выполнять ежедневно для обновления данных за нужный период
-- ----------------------------------------------------------------------------
-- ПРИМЕР: Заполнение за диапазон дат (2025-10-10 до 2025-10-30)
-- 
-- INSERT INTO mg_dm.packages_by_tariff
-- WITH 
--     -- Генерация дней для анализа
--     date_range AS (
--         SELECT toDate(number) AS day
--         FROM numbers(dateDiff('day', toDate('2025-10-10'), toDate('2025-10-30')) + 1)
--         SETTINGS max_block_size = 1000
--     ),
--     -- Подсчёт активных пакетов на каждый день
--     daily_packages AS (
--         SELECT
--             dr.day AS actual_date,
--             t.name AS tariff_name,
--             multiIf(
--                 upp.sourceType IN ('payment', 'upgrade', 'paidCoupon'), 'paid',
--                 upp.sourceType = 'gift' AND dateDiff('day', upp.startDate, upp.endDate) > 29, 'paid',
--                 upp.sourceType = 'gift' AND dateDiff('day', upp.startDate, upp.endDate) <= 29, 'gift',
--                 upp.sourceType
--             ) AS sourceType,
--             count() AS cnt
--         FROM date_range dr
--         CROSS JOIN mg_raw.permission_packages pp
--         INNER JOIN mg_raw.user_permission_packages upp ON upp.permissionPackageId = pp.id
--         INNER JOIN mg_raw.tariffs t ON t.id = pp.tariff_id AND t.source = 'marketguru'
--         WHERE pp.updated <= dr.day
--           AND upp.startDate < dr.day
--           AND upp.endDate > dr.day
--           AND upp.status = 'active'
--           AND isNull(upp.deleted)
--           AND isNotNull(pp.tariff_id)
--         GROUP BY actual_date, tariff_name, sourceType
--     )
-- SELECT 
--     actual_date,
--     tariff_name,
--     sourceType,
--     cnt
-- FROM daily_packages
-- ORDER BY actual_date, tariff_name, sourceType;


-- ----------------------------------------------------------------------------
-- 6.2. Запрос для заполнения mg_dm.packages_by_period
-- Выполнять ежедневно для обновления данных за нужный период
-- ----------------------------------------------------------------------------
-- INSERT INTO mg_dm.packages_by_period
-- WITH 
--     date_range AS (
--         SELECT toDate(number) AS day
--         FROM numbers(dateDiff('day', toDate('2025-10-10'), toDate('2025-10-30')) + 1)
--     ),
--     periods AS (
--         SELECT
--             dr.day AS actual_date,
--             pp.period AS period,
--             count() AS quantity
--         FROM date_range dr
--         CROSS JOIN mg_raw.permission_packages pp
--         INNER JOIN mg_raw.user_permission_packages upp ON upp.permissionPackageId = pp.id
--         INNER JOIN mg_raw.tariffs t ON t.id = pp.tariff_id AND t.source = 'marketguru'
--         WHERE pp.updated <= dr.day
--           AND upp.startDate < dr.day
--           AND upp.endDate > dr.day
--           AND upp.status = 'active'
--           AND isNull(upp.deleted)
--           AND isNotNull(pp.tariff_id)
--         GROUP BY actual_date, period
--     ),
--     grouped AS (
--         SELECT
--             p.actual_date,
--             p.period,
--             p.quantity,
--             tgd.name,
--             coalesce(tgd.day, (
--                 SELECT min(day)
--                 FROM mg_raw.tariff_group_days
--                 WHERE day > p.period AND source = 'marketguru'
--             )) AS nearest_main
--         FROM periods p
--         LEFT JOIN mg_raw.tariff_group_days tgd ON p.period = tgd.day AND tgd.source = 'marketguru'
--     )
-- SELECT
--     actual_date,
--     multiIf(
--         period = nearest_main, name,
--         period < nearest_main, concat('< ', toString(nearest_main)),
--         concat('> ', (SELECT name FROM mg_raw.tariff_group_days WHERE source = 'marketguru' ORDER BY day DESC LIMIT 1))
--     ) AS period_name,
--     sum(quantity) AS cnt
-- FROM grouped
-- GROUP BY actual_date, period_name
-- ORDER BY actual_date, period_name;


-- ----------------------------------------------------------------------------
-- 6.3. Запрос для заполнения mg_dm.mg_churn
-- Анализ оттока и возврата пользователей (разрывы > 30 дней)
-- Выполнять еженедельно или ежемесячно
-- ----------------------------------------------------------------------------
-- TRUNCATE TABLE mg_dm.mg_churn;
-- INSERT INTO mg_dm.mg_churn
-- WITH
--     -- Сортировка и вычисление максимальной правой границы предыдущих интервалов
--     sorted AS (
--         SELECT
--             user_id,
--             startDate AS start_dt,
--             endDate AS end_dt,
--             maxOver(endDate, (PARTITION BY user_id ORDER BY startDate ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)) AS max_prev_end
--         FROM mg_raw.user_permission_packages
--         WHERE startDate >= toDate('2024-01-01')
--     ),
--     -- Определение начала новых "кусков" непрерывного доступа
--     flagged AS (
--         SELECT
--             user_id,
--             start_dt,
--             end_dt,
--             max_prev_end,
--             if(isNull(max_prev_end) OR start_dt > max_prev_end, 1, 0) AS is_new_chunk
--         FROM sorted
--     ),
--     -- Нумерация кусков
--     chunked AS (
--         SELECT
--             user_id,
--             start_dt,
--             end_dt,
--             sumOver(is_new_chunk, (PARTITION BY user_id ORDER BY start_dt ROWS UNBOUNDED PRECEDING)) AS chunk_id
--         FROM flagged
--     ),
--     -- Объединение интервалов в непрерывные периоды
--     merged AS (
--         SELECT
--             user_id,
--             min(start_dt) AS period_start,
--             max(end_dt) AS period_end
--         FROM chunked
--         GROUP BY user_id, chunk_id
--     ),
--     -- Поиск следующего периода для каждого пользователя
--     with_next AS (
--         SELECT
--             user_id,
--             period_end,
--             lagInFrame(period_start, 1) OVER (PARTITION BY user_id ORDER BY period_start DESC) AS next_start
--         FROM merged
--     )
-- -- Фильтрация: разрывы > 30 дней
-- SELECT
--     user_id,
--     toDate(period_end, 'Europe/Moscow') AS churn_date,
--     toDate(next_start, 'Europe/Moscow') AS return_date,
--     dateDiff('day', period_end, coalesce(next_start, now())) AS gap_interval
-- FROM with_next
-- WHERE period_end < now() - INTERVAL 30 DAY
--   AND (
--       (dateDiff('day', period_end, next_start) > 30 AND next_start <= now())
--       OR isNull(next_start)
--   )
-- ORDER BY churn_date DESC;


-- ----------------------------------------------------------------------------
-- 6.4. Запрос для заполнения mg_dm.user_events
-- События пользователей: registration, trial, first_pay_tariff, first_pay_ap
-- Выполнять ежедневно для добавления новых событий
-- ----------------------------------------------------------------------------
-- INSERT INTO mg_dm.user_events
-- -- 1. Регистрации
-- SELECT
--     user_id,
--     toDate(created, 'Europe/Moscow') AS event_date,
--     'registration' AS event_name
-- FROM mg_raw.users
-- WHERE has(source, 'marketguru')
--   AND toDate(created, 'Europe/Moscow') >= toDate('2024-01-01')
-- 
-- UNION ALL
-- 
-- -- 2. Триальные периоды
-- SELECT
--     user_id,
--     toDate(startDate, 'Europe/Moscow') AS event_date,
--     'trial' AS event_name
-- FROM mg_raw.user_permission_packages
-- WHERE sourceType = 'trial'
--   AND toDate(startDate, 'Europe/Moscow') >= toDate('2025-01-01')
-- 
-- UNION ALL
-- 
-- -- 3. Первый платный тариф
-- SELECT
--     user_id,
--     event_date,
--     'first_pay_tariff' AS event_name
-- FROM (
--     SELECT
--         user_id,
--         toDate(startDate, 'Europe/Moscow') AS event_date,
--         row_number() OVER (PARTITION BY user_id ORDER BY startDate) AS rn
--     FROM mg_raw.user_permission_packages
--     WHERE (
--         sourceType IN ('payment', 'upgrade', 'paidCoupon')
--         OR (sourceType = 'gift' AND dateDiff('day', startDate, endDate) > 29)
--     )
--     AND toDate(startDate, 'Europe/Moscow') >= toDate('2025-01-01')
-- )
-- WHERE rn = 1
-- 
-- UNION ALL
-- 
-- -- 4. Первая покупка дополнительных пакетов
-- SELECT
--     user_id,
--     event_date,
--     'first_pay_ap' AS event_name
-- FROM (
--     SELECT
--         user_id,
--         toDate(completedDate, 'Europe/Moscow') AS event_date,
--         row_number() OVER (PARTITION BY user_id ORDER BY completedDate) AS rn
--     FROM mg_raw.payments
--     WHERE toDate(updated, 'Europe/Moscow') >= toDate('2024-01-01')
--       AND source = 'marketguru'
--       AND purposeOfPayment IN ('buyAdditionalPackages', 'buyTariffAndAdditionalPackages')
--       AND state = 'completed'
-- )
-- WHERE rn = 1;


-- ============================================================================
-- СЕКЦИЯ 7: ПРОВЕРКА СТРУКТУРЫ
-- ============================================================================

-- Проверка созданных таблиц в RAW-слое
-- SHOW TABLES FROM mg_raw;

-- Проверка созданных таблиц в DM-слое
-- SHOW TABLES FROM mg_dm;

-- Проверка созданных материализованных представлений
-- SHOW TABLES FROM mg_mv;

-- Проверка структуры конкретной таблицы
-- DESCRIBE TABLE mg_raw.users;
-- DESCRIBE TABLE mg_dm.payments_daily;


-- ============================================================================
-- СЕКЦИЯ 8: ИНСТРУКЦИИ ПО ЗАПОЛНЕНИЮ RAW-ТАБЛИЦ
-- ============================================================================

/*
Для начальной загрузки данных из PostgreSQL используйте один из способов:

1. ClickHouse PostgreSQL Table Engine (рекомендуется для первичной загрузки):

   INSERT INTO mg_raw.users
   SELECT 
       id AS user_id,
       created,
       source,
       deleted
   FROM postgresql('postgres_host:5432', 'database', 'users', 'user', 'password')
   WHERE 'marketguru' = ANY(source) 
     AND created >= '2024-01-01';

2. Python-скрипт с использованием clickhouse-driver и psycopg2

3. DBeaver / DataGrip с экспортом в CSV → импорт в ClickHouse

4. Kafka Connector для потоковой репликации (для продакшена)


ВАЖНО: После загрузки данных в RAW-таблицы, материализованные представления
автоматически заполнят витрины. Для витрин без автоматической материализации
(packages_by_tariff, packages_by_period, mg_churn, user_events) используйте
запросы из СЕКЦИИ 6.
*/


-- ============================================================================
-- КОНЕЦ СКРИПТА
-- ============================================================================

