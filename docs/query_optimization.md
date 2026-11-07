# Query optimization (EXPLAIN ANALYZE)

Script: `sql/explain/explain_analyze.sql`. Latest plans are in `docs/explain_output.txt`. PostgreSQL 16 on a laptop, 1.3M-row fact table, repeated runs with a warm cache. Timings depend on the machine, so treat them as rough.

Query: monthly Pothole requests for 2025 (join to `dim_request_type`, filter on type and date range).

| Plan | Execution time |
|---|---|
| Both fact-table indexes dropped (inside a rolled-back transaction): parallel sequential scan of the whole table | about 40-45 ms |
| With `idx_fact_type_opened (request_type_id, opened_date)`: bitmap index scan returning 3,844 rows | about 3 ms |

The index puts the equality column first and the date range second, so one index scan covers both filters. Plans can change between runs and versions; on some runs the planner picks an index-only scan for this query instead of the bitmap scan shown in the saved output. A cold-cache first run of the unindexed query took 113-135 ms.

Only this query was tested; the other indexes in `03_constraints_indexes.sql` were not benchmarked separately.
