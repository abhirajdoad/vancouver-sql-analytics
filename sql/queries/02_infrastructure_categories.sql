-- Q1b. Infrastructure request categories and the types within them, ranked by volume.
-- Share is relative to all infrastructure-classified requests (see dim_request_type mapping).
WITH infra AS (
    SELECT infrastructure_group, service_request_type, count(*) AS requests
    FROM analytics.v_request_detail
    WHERE infrastructure_group IS NOT NULL
    GROUP BY 1, 2
)
SELECT infrastructure_group,
       service_request_type,
       requests,
       round(100.0 * requests / sum(requests) OVER (), 1)                          AS pct_of_infrastructure,
       sum(requests) OVER (PARTITION BY infrastructure_group)                      AS group_total,
       rank() OVER (PARTITION BY infrastructure_group ORDER BY requests DESC)      AS rank_in_group
FROM infra
ORDER BY group_total DESC, requests DESC;
