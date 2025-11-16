-- ============================================================================
-- ЗАПРОСЫ ДЛЯ ПРОВЕРКИ СТРУКТУРЫ В POSTGRESQL
-- Выполнять по одному, раскомментируя нужный
-- ============================================================================

-- 1. PAYMENTS
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
from t
LIMIT 10;


-- ============================================================================
-- 2. USERS
-- ============================================================================
-- SELECT 
-- 	row_number() over (order by created) id,
-- 	id as user_id, 
-- 	created::Date AS "entryDate"
-- FROM users
-- WHERE 'marketguru' = ANY (source) AND deleted IS NULL
--     and created::Date >= '2024-01-01'
-- LIMIT 10;


-- ============================================================================
-- 3. PACKAGES-BY-TARIFF
-- ============================================================================
-- with d as (
--     select day from generate_series('2025-10-10'::timestamp, '2025-10-30'::timestamp, '1 day') AS g(day)
-- ),
-- tt as (
-- select
--     date(d.day) actual_date,
--     t.name,
--     case when "sourceType" IN ('payment', 'upgrade', 'paidCoupon') OR
--         ("sourceType" = 'gift' AND extract(EPOCH FROM upp."endDate" - "startDate") / 86400 > 29) then 'paid'
--     when upp."sourceType" = 'gift' AND extract(EPOCH FROM upp."endDate" - "startDate") / 86400 <= 29 then 'gift'
--     else upp."sourceType" end sourceType,
--     count(*)::int AS count
-- FROM
--     permission_packages pp
--         JOIN user_permission_packages upp ON upp."permissionPackageId" = pp.id
--         INNER JOIN tariffs t ON t."id" = pp."tariffId" and t.source = 'marketguru'
--         join d on pp.updated <= d.day
-- WHERE
--     upp."startDate" < now() AND
--     upp."endDate" > now() AND
--     upp.status = 'active' AND
--     upp.deleted IS NULL AND
--     pp."tariffId" IS NOT null
-- GROUP BY 1,2,3
-- ORDER BY count(*) desc
-- )
-- select row_number() over(order by actual_date) id, * from tt
-- LIMIT 10;


-- ============================================================================
-- 4. PACKAGES-BY-PERIOD
-- ============================================================================
-- with d as (
--     select day from generate_series('2025-10-10'::timestamp, '2025-10-30'::timestamp, '1 day') AS g(day)
-- ),
--     periods AS (
--         select
--             date(d.day) actual_date,
--             pp.period::int AS period,
--             count(*)::int AS quantity
--     FROM
--         permission_packages pp
--             JOIN user_permission_packages upp ON upp."permissionPackageId" = pp.id
--             INNER JOIN tariffs t ON t."id" = pp."tariffId" AND t.source = 'marketguru'
--             join d on pp.updated <= d.day
--     WHERE
--         upp."startDate" < d.day AND
--         upp."endDate" > d.day AND
--         upp.status = 'active' AND
--         upp.deleted IS NULL AND
--         pp."tariffId" IS NOT NULL
--     GROUP BY 1,2
--     ORDER BY 1 desc,2
-- ),
--     grouped AS (
--         SELECT
--         tgd.name,
--         p.period,
--         p.quantity,
--         COALESCE(tgd.day, (
--             SELECT MIN(day)
--             FROM tariff_group_days
--             WHERE day > p.period)
--         ) AS nearest_main,
--         p.actual_date
--     FROM
--         periods p
--             LEFT JOIN tariff_group_days tgd ON p.period = tgd.day AND tgd.source = 'marketguru'
-- ),
-- t as (
-- 	select
-- 	    actual_date,
-- 	    case
-- 	        WHEN period = nearest_main THEN name::text
-- 	        WHEN period < nearest_main THEN '< ' || nearest_main
-- 	        ELSE (
-- 	            SELECT '> ' || name
-- 	            FROM tariff_group_days
-- 	            WHERE source = 'marketguru'
-- 	            ORDER BY day DESC
-- 	            LIMIT 1)
-- 	        END AS period_name,
-- 	    sum(quantity)::int AS cnt
-- 	FROM grouped
-- 	GROUP BY 1,2
-- )
-- select 
--     row_number() over(order by actual_date) id,
-- 	*
-- from t
-- LIMIT 10;


-- ============================================================================
-- 5. MG_CHURN
-- ============================================================================
-- with sorted as (
--     select
--         "userId"  user_id,
--         "startDate"  start_dt,
--         "endDate" end_dt,
--         max("endDate") over (
--             partition by "userId"
--             order by "startDate"
--             rows between unbounded preceding and 1 preceding
--         ) as max_prev_end
--     from user_permission_packages
--     where "startDate" >= '2024-01-01'
-- ),
-- flagged as (
--     select
--         user_id,
--         start_dt,
--         end_dt,
--         max_prev_end,
--         case
--             when max_prev_end is null then 1
--             when start_dt > max_prev_end then 1
--             else 0
--         end as is_new_chunk
--     from sorted
-- ),
-- chunked as (
--     select
--         user_id,
--         start_dt,
--         end_dt,
--         sum(is_new_chunk) over (partition by user_id order by start_dt rows unbounded preceding) as chunk_id
--     from flagged
-- ),
-- merged as (
--     select
--         user_id,
--         min(start_dt) as period_start,
--         max(end_dt)   as period_end
--     from chunked
--     group by user_id, chunk_id
-- ),
-- with_next as (
--     select
--         m.*,
--         lead(period_start) over (partition by user_id order by period_start) as next_start
--     from merged m
-- )
-- select
-- 	row_number() over (order by user_id) id,
--     user_id,
--     period_end::date   as churn_date,
--     next_start::date   as return_date,
--     extract(days from coalesce(next_start, now()) - period_end) as gap_interval
-- from with_next
-- where 1=1
-- 	and period_end < now() - interval '30 days'
--   and ((next_start - period_end) > interval '30 days' and next_start <= now() or next_start is null)
-- order by churn_date desc
-- LIMIT 10;


-- ============================================================================
-- 6. EVENT_BACKEND
-- ============================================================================
-- select 
--   id user_id,
--   ("created" at time zone 'MSK')::date event_date,
--   'registration' event_name
-- from users
-- where 'marketguru' = ANY (source)
-- LIMIT 3
-- union all
-- select
--   "userId" user_id,
--   ("startDate" at time zone 'MSK')::date event_date,
--   'trial' event_name
-- from user_permission_packages
-- where "sourceType" in ('trial')
-- and "startDate" >= '2025-01-01'
-- LIMIT 3
-- union all
-- select
--   user_id,
--   event_date,
--   'first_pay_tariff' event_name
-- from (
--   select 
--     "userId" user_id,
--     ("startDate" at time zone 'MSK')::date event_date,
--     row_number() over (partition by "userId" order by "startDate") rn
--   from user_permission_packages
--   where ("sourceType" IN ('payment', 'upgrade', 'paidCoupon') OR
--       ("sourceType" = 'gift' AND extract(EPOCH FROM "endDate" - "startDate") / 86400 > 29)) 
--       and "startDate" >= '2025-01-01'
-- ) t
-- where rn = 1
-- LIMIT 3
-- union all
-- select
--   user_id,
--   event_date,
--   'first_pay_ap' event_name
-- from (
--   select 
--     "userId" user_id,
--     ("completedDate" at time zone 'MSK')::date event_date,
--     row_number() over (partition by "userId" order by "completedDate") rn
--   from "Payments"
--   where ("updated" at time zone 'MSK')::date >= '2024-01-01'
--     and "source" = 'marketguru'
--     and "purposeOfPayment" in ('buyAdditionalPackages', 'buyTariffAndAdditionalPackages') 
--     and state = 'completed' 
-- ) t
-- where rn = 1
-- LIMIT 3;

