-- Q2a. Monthly request volume with month-over-month change (complete months only).
WITH monthly AS (
    SELECT opened_month,
           sum(requests)                                                  AS all_requests,
           sum(requests) FILTER (WHERE category <> 'Non-infrastructure')  AS infra_requests
    FROM analytics.v_monthly_volume
    GROUP BY opened_month
)
SELECT opened_month,
       all_requests,
       infra_requests,
       round(100.0 * (all_requests - lag(all_requests) OVER w) / lag(all_requests) OVER w, 1)     AS all_mom_pct,
       round(100.0 * (infra_requests - lag(infra_requests) OVER w) / lag(infra_requests) OVER w, 1) AS infra_mom_pct
FROM monthly
WINDOW w AS (ORDER BY opened_month)
ORDER BY opened_month;
