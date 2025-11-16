-- ============================================================================
-- СОЗДАНИЕ И ЗАПОЛНЕНИЕ RAW-ТАБЛИЦ В CLICKHOUSE
-- Выполнять в ClickHouse
-- ============================================================================
-- ВАЖНО: Замените параметры подключения к PostgreSQL:
--   postgres_host:5432  → ваш хост и порт
--   users_db            → название базы данных
--   username            → пользователь PostgreSQL
--   password            → пароль
-- ============================================================================


-- ============================================================================
-- СЕКЦИЯ 1: СОЗДАНИЕ БАЗЫ ДАННЫХ
-- ============================================================================

CREATE DATABASE IF NOT EXISTS mg_raw;


-- ============================================================================
-- СЕКЦИЯ 2: СОЗДАНИЕ RAW-ТАБЛИЦ (6 штук)
-- ============================================================================

-- 2.1. RAW-таблица: users
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mg_raw.users
(
    user_id UUID,
    created DateTime,
    source  Array(String),
    deleted Nullable(DateTime)
)
ENGINE = MergeTree()
ORDER BY (created, user_id)
COMMENT 'Пользователи MarketGuru из PostgreSQL';


-- 2.2. RAW-таблица: payments
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


-- 2.3. RAW-таблица: permission_packages
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


-- 2.4. RAW-таблица: user_permission_packages
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
    sourceType          String,
    deleted             Nullable(DateTime),
    created             DateTime,
    updated             DateTime
)
ENGINE = MergeTree()
ORDER BY (user_id, startDate)
COMMENT 'Пакеты пользователей из PostgreSQL';


-- 2.5. RAW-таблица: tariffs
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


-- 2.6. RAW-таблица: tariff_group_days
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
-- ПРОВЕРКА: Таблицы созданы
-- ============================================================================
SHOW TABLES FROM mg_raw;


-- ============================================================================
-- СЕКЦИЯ 3: ЗАПОЛНЕНИЕ RAW-ТАБЛИЦ ДАННЫМИ ИЗ POSTGRESQL
-- ============================================================================
-- ВАЖНО: Раскомментируйте INSERT-ы только после:
--   1. Проверки, что все таблицы созданы (SHOW TABLES FROM mg_raw)
--   2. Проверки параметров подключения к PostgreSQL
--   3. Тестового запроса к PostgreSQL
-- ============================================================================

-- 3.1. Заполнение mg_raw.users
-- ----------------------------------------------------------------------------
-- INSERT INTO mg_raw.users
-- SELECT 
--     id AS user_id,
--     created,
--     source,
--     deleted
-- FROM postgresql('postgres_host:5432', 'users_db', 'users', 'username', 'password')
-- WHERE 'marketguru' = ANY(source) 
--   AND created >= '2024-01-01';

-- -- Проверка:
-- -- SELECT 'users' AS table_name, COUNT(*) AS row_count FROM mg_raw.users;


-- -- 3.2. Заполнение mg_raw.payments
-- -- ----------------------------------------------------------------------------
-- INSERT INTO mg_raw.payments
-- SELECT 
--     id AS payment_id,
--     updated,
--     "completedDate" AS completedDate,
--     "purposeOfPayment" AS purposeOfPayment,
--     amount,
--     state,
--     source::text AS source,
--     "userId" AS user_id
-- FROM postgresql('postgres_host:5432', 'users_db', 'Payments', 'username', 'password')
-- WHERE source::text = 'marketguru'
--   AND updated >= '2024-01-01';

-- -- Проверка:
-- SELECT 'payments' AS table_name, COUNT(*) AS row_count FROM mg_raw.payments;


-- -- 3.3. Заполнение mg_raw.permission_packages
-- -- ----------------------------------------------------------------------------
-- INSERT INTO mg_raw.permission_packages
-- SELECT 
--     id,
--     period,
--     "tariffId" AS tariff_id,
--     updated
-- FROM postgresql('postgres_host:5432', 'users_db', 'permission_packages', 'username', 'password')
-- WHERE updated >= '2024-01-01';

-- -- Проверка:
-- SELECT 'permission_packages' AS table_name, COUNT(*) AS row_count FROM mg_raw.permission_packages;


-- -- 3.4. Заполнение mg_raw.user_permission_packages
-- -- ----------------------------------------------------------------------------
-- INSERT INTO mg_raw.user_permission_packages
-- SELECT 
--     id,
--     "userId" AS user_id,
--     "permissionPackageId" AS permissionPackageId,
--     status,
--     "startDate" AS startDate,
--     "endDate" AS endDate,
--     "pausedStartDate" AS pausedStartDate,
--     "pausedEndDate" AS pausedEndDate,
--     type,
--     COALESCE("sourceType", type) AS sourceType,
--     deleted,
--     created,
--     updated
-- FROM postgresql('postgres_host:5432', 'users_db', 'user_permission_packages', 'username', 'password')
-- WHERE "startDate" >= '2024-01-01';

-- -- Проверка:
-- SELECT 'user_permission_packages' AS table_name, COUNT(*) AS row_count FROM mg_raw.user_permission_packages;


-- -- 3.5. Заполнение mg_raw.tariffs
-- -- ----------------------------------------------------------------------------
-- INSERT INTO mg_raw.tariffs
-- SELECT 
--     id,
--     name,
--     source::text AS source
-- FROM postgresql('postgres_host:5432', 'users_db', 'tariffs', 'username', 'password')
-- WHERE source::text = 'marketguru';

-- -- Проверка:
-- SELECT 'tariffs' AS table_name, COUNT(*) AS row_count FROM mg_raw.tariffs;


-- -- 3.6. Заполнение mg_raw.tariff_group_days
-- -- ----------------------------------------------------------------------------
-- INSERT INTO mg_raw.tariff_group_days
-- SELECT 
--     day,
--     name,
--     source::text AS source,
--     "isEnabled"::int AS isEnabled,
--     "isDefault"::int AS isDefault
-- FROM postgresql('postgres_host:5432', 'users_db', 'tariff_group_days', 'username', 'password')
-- WHERE source::text = 'marketguru';

-- -- Проверка:
-- SELECT 'tariff_group_days' AS table_name, COUNT(*) AS row_count FROM mg_raw.tariff_group_days;


-- -- ============================================================================
-- -- ФИНАЛЬНАЯ ПРОВЕРКА: Количество строк во всех RAW-таблицах
-- -- ============================================================================
-- SELECT 
--     'users' AS table_name, 
--     COUNT(*) AS row_count 
-- FROM mg_raw.users

-- UNION ALL

-- SELECT 
--     'payments' AS table_name, 
--     COUNT(*) AS row_count 
-- FROM mg_raw.payments

-- UNION ALL

-- SELECT 
--     'permission_packages' AS table_name, 
--     COUNT(*) AS row_count 
-- FROM mg_raw.permission_packages

-- UNION ALL

-- SELECT 
--     'user_permission_packages' AS table_name, 
--     COUNT(*) AS row_count 
-- FROM mg_raw.user_permission_packages

-- UNION ALL

-- SELECT 
--     'tariffs' AS table_name, 
--     COUNT(*) AS row_count 
-- FROM mg_raw.tariffs

-- UNION ALL

-- SELECT 
--     'tariff_group_days' AS table_name, 
--     COUNT(*) AS row_count 
-- FROM mg_raw.tariff_group_days;


-- -- ============================================================================
-- -- ГОТОВО!
-- -- ============================================================================
-- -- Следующий шаг: создать витрины (mg_dm.*) и материализованные представления
-- -- ============================================================================

