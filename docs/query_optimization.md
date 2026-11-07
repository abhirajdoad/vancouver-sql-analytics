# Query optimization (EXPLAIN ANALYZE)

Script: `sql/explain/explain_analyze.sql`; full plans in `docs/explain_output.txt`. Warm-cache runs, PostgreSQL 16, 1.3M-row fact table.

Query: monthly Pothole requests for 2025 (join to `dim_request_type`, filter on type and date range).

| Plan | Execution time |
|---|---|
| No indexes on the fact table: parallel sequential scan of all rows | ~40 ms |
| `idx_fact_type_opened (request_type_id, opened_date)`: bitmap index scan, 3,844 rows | ~3 ms |

The composite index puts the equality column first and the range column second, so one index scan satisfies both predicates.

An index on `local_area_id` was tried and dropped: a neighbourhood like Kitsilano holds about 5% of rows, and the planner's
indexed plan (~240-300 ms) was no faster than a parallel sequential scan (~270 ms). Indexes that do not change the plan are cost without benefit.
The first run of the unindexed query was slower (113-135 ms) because of a cold cache; the figures above are repeated warm runs.
