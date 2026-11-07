-- Q3a. Neighbourhood demand. Requests without a local_area (~21% overall, ~1% of infrastructure
-- requests) are shown as their own row and left unranked, not dropped silently.
-- Counts are raw volumes, not per-capita.
WITH by_area AS (
    SELECT local_area,
           count(*)                                              AS all_requests,
           count(*) FILTER (WHERE infrastructure_group IS NOT NULL) AS infra_requests
    FROM analytics.v_request_detail
    GROUP BY local_area
)
SELECT COALESCE(local_area, '(no location recorded)')                  AS local_area,
       all_requests,
       infra_requests,
       round(100.0 * infra_requests / all_requests, 1)                 AS infra_share_pct,
       CASE WHEN local_area IS NOT NULL
            THEN rank() OVER (PARTITION BY local_area IS NULL ORDER BY infra_requests DESC) END AS infra_rank
FROM by_area
ORDER BY infra_requests DESC;
