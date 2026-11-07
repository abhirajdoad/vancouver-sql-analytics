-- Q6a. Days with unusually high drainage/flooding demand: daily count vs. the trailing 60-day
-- mean and standard deviation (z-score). Needs at least 30 prior days, so January 2022 is not scored.
SELECT opened_date, requests, round(trailing_mean, 1) AS trailing_60d_mean, round(z_score, 1) AS z_score
FROM (
    SELECT opened_date, requests,
           count(*)              OVER w AS prior_days,
           avg(requests)         OVER w AS trailing_mean,
           (requests - avg(requests) OVER w) / NULLIF(stddev_samp(requests) OVER w, 0) AS z_score
    FROM (
        SELECT g.d::date AS opened_date, count(r.request_id) AS requests
        FROM generate_series('2022-01-01'::date, (SELECT max(opened_date) - 1 FROM analytics.fact_service_request), '1 day') g(d)
        LEFT JOIN analytics.v_request_detail r
               ON r.opened_date = g.d::date AND r.infrastructure_group = 'Drainage & Flooding'
        GROUP BY g.d
    ) daily
    WINDOW w AS (ORDER BY opened_date ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING)
) scored
WHERE prior_days >= 30 AND z_score >= 3 AND requests >= 20
ORDER BY requests DESC
LIMIT 10;
