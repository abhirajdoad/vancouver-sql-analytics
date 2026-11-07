-- Index evaluation. Index drops are rolled back, so the database is unchanged afterwards.
-- Run: psql -d vancouver_311 -f sql/explain/explain_analyze.sql

\echo '=== A. Monthly pothole requests in 2025, WITHOUT supporting indexes'
BEGIN;
DROP INDEX analytics.idx_fact_type_opened, analytics.idx_fact_opened_date;
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF)
SELECT date_trunc('month', f.opened_date) AS m, count(*)
FROM analytics.fact_service_request f
JOIN analytics.dim_request_type t USING (request_type_id)
WHERE t.service_request_type = 'Pothole Case'
  AND f.opened_date >= '2025-01-01' AND f.opened_date < '2026-01-01'
GROUP BY 1 ORDER BY 1;
ROLLBACK;

\echo '=== B. Same query WITH idx_fact_type_opened (request_type_id, opened_date)'
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF)
SELECT date_trunc('month', f.opened_date) AS m, count(*)
FROM analytics.fact_service_request f
JOIN analytics.dim_request_type t USING (request_type_id)
WHERE t.service_request_type = 'Pothole Case'
  AND f.opened_date >= '2025-01-01' AND f.opened_date < '2026-01-01'
GROUP BY 1 ORDER BY 1;

