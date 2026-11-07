-- Q6c. Open infrastructure requests older than 90 days, by type, with age of the oldest.
-- Subquery pins "today" to the extract's latest date so results are reproducible.
SELECT infrastructure_group, service_request_type,
       count(*)                                         AS open_over_90d,
       max(ref.d - opened_date)                         AS oldest_open_days,
       round(avg(ref.d - opened_date), 0)               AS avg_age_days
FROM analytics.v_request_detail
CROSS JOIN (SELECT max(opened_date) AS d FROM analytics.fact_service_request) ref
WHERE status = 'Open' AND infrastructure_group IS NOT NULL
  AND ref.d - opened_date > 90
GROUP BY 1, 2
ORDER BY open_over_90d DESC
LIMIT 10;
