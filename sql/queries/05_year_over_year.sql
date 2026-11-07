-- Q5a. Year-over-year change for infrastructure groups using the same Jan-Oct window each year
-- (2026 is incomplete after October, so later months are excluded for a like-for-like comparison).
WITH yearly AS (
    SELECT infrastructure_group, opened_year, count(*) AS requests
    FROM analytics.v_request_detail
    WHERE infrastructure_group IS NOT NULL AND opened_month_num <= 10
    GROUP BY 1, 2
)
SELECT infrastructure_group, opened_year, requests,
       lag(requests) OVER w AS prior_year,
       round(100.0 * (requests - lag(requests) OVER w) / lag(requests) OVER w, 1) AS yoy_pct
FROM yearly
WINDOW w AS (PARTITION BY infrastructure_group ORDER BY opened_year)
ORDER BY infrastructure_group, opened_year;
