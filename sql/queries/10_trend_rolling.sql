-- Q5b. Trend: 3-month rolling average and 12-month-ago comparison for infrastructure volume.
WITH monthly AS (
    SELECT opened_month, sum(requests) AS infra_requests
    FROM analytics.v_monthly_volume
    WHERE category <> 'Non-infrastructure'
    GROUP BY opened_month
)
SELECT opened_month, infra_requests,
       round(avg(infra_requests) OVER (ORDER BY opened_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS rolling_3m_avg,
       lag(infra_requests, 12) OVER (ORDER BY opened_month)                                                 AS same_month_prior_year,
       round(100.0 * (infra_requests - lag(infra_requests, 12) OVER (ORDER BY opened_month))
             / lag(infra_requests, 12) OVER (ORDER BY opened_month), 1)                                      AS yoy_pct
FROM monthly
ORDER BY opened_month;
