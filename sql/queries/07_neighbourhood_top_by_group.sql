-- Q3b. Top 3 neighbourhoods for each infrastructure group (ROW_NUMBER over a CTE).
WITH counts AS (
    SELECT infrastructure_group, local_area, count(*) AS requests
    FROM analytics.v_request_detail
    WHERE infrastructure_group IS NOT NULL AND local_area IS NOT NULL
    GROUP BY 1, 2
),
ranked AS (
    SELECT *, row_number() OVER (PARTITION BY infrastructure_group ORDER BY requests DESC) AS rn,
           round(100.0 * requests / sum(requests) OVER (PARTITION BY infrastructure_group), 1) AS pct_of_group
    FROM counts
)
SELECT infrastructure_group, rn AS rank, local_area, requests, pct_of_group
FROM ranked
WHERE rn <= 3
ORDER BY infrastructure_group, rn;
