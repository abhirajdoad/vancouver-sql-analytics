-- Q2b. Seasonal pattern: average requests per month in each season, indexed against the
-- mean of the category's four season averages (100 = typical season). Complete months only; seasons have
-- 14 or 15 observed months because the data ends in November.
WITH monthly AS (
    SELECT v.opened_month, v.category, v.requests,
           CASE WHEN extract(month FROM v.opened_month) IN (12, 1, 2) THEN 'Winter'
                WHEN extract(month FROM v.opened_month) IN (3, 4, 5)  THEN 'Spring'
                WHEN extract(month FROM v.opened_month) IN (6, 7, 8)  THEN 'Summer'
                ELSE 'Autumn' END AS season
    FROM analytics.v_monthly_volume v
),
by_season AS (
    SELECT category, season, round(avg(requests), 0) AS avg_monthly_requests, count(*) AS months_observed
    FROM monthly
    GROUP BY category, season
)
SELECT category, season, avg_monthly_requests, months_observed,
       round(100 * avg_monthly_requests / avg(avg_monthly_requests) OVER (PARTITION BY category), 0) AS seasonal_index
FROM by_season
ORDER BY category, array_position(ARRAY['Winter','Spring','Summer','Autumn'], season);
