-- Q4c / Q5c. Share of infrastructure requests closed within 7 days, by opening year.
-- Uses a fixed 7-day window so recent years are not biased by right-censoring (a request opened last
-- week cannot have a long duration yet). 2026 requests opened in the last 7 days are excluded.
SELECT infrastructure_group, opened_year,
       count(*) AS requests,
       round(100.0 * count(*) FILTER (WHERE days_to_close <= 7) / count(*), 1) AS closed_within_7d_pct,
       round(100.0 * count(*) FILTER (WHERE status = 'Open')    / count(*), 1) AS still_open_pct
FROM analytics.v_request_detail
WHERE infrastructure_group IS NOT NULL
  AND opened_date <= (SELECT max(opened_date) FROM analytics.fact_service_request) - 7
GROUP BY 1, 2
ORDER BY 1, 2;
