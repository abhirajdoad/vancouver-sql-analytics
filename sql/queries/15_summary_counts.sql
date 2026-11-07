-- Headline counts quoted in the README and methodology.
SELECT metric, value FROM (
    SELECT 1 AS ord, 'all requests' AS metric, count(*)::numeric AS value FROM analytics.v_request_detail
    UNION ALL SELECT 2, 'infrastructure requests', count(*) FROM analytics.v_request_detail WHERE infrastructure_group IS NOT NULL
    UNION ALL SELECT 3, 'infrastructure share of all (%)', round(100.0 * count(*) FILTER (WHERE infrastructure_group IS NOT NULL) / count(*), 1) FROM analytics.v_request_detail
    UNION ALL SELECT 4, 'infrastructure requests without local_area', count(*) FROM analytics.v_request_detail WHERE infrastructure_group IS NOT NULL AND local_area IS NULL
    UNION ALL SELECT 5, 'infrastructure requests still open', count(*) FROM analytics.v_request_detail WHERE infrastructure_group IS NOT NULL AND status = 'Open'
    UNION ALL SELECT 6, 'infrastructure open > 90 days', count(*) FROM analytics.v_request_detail
        WHERE infrastructure_group IS NOT NULL AND status = 'Open'
          AND (SELECT max(opened_date) FROM analytics.fact_service_request) - opened_date > 90
    UNION ALL SELECT 7, 'infrastructure closed as "Service provided" (% of closed)',
        round(100.0 * count(*) FILTER (WHERE outcome_group = 'Service provided') / count(*), 1)
        FROM analytics.v_request_detail WHERE infrastructure_group IS NOT NULL AND status = 'Closed'
    UNION ALL SELECT 8, 'infrastructure median days to close', percentile_cont(0.5) WITHIN GROUP (ORDER BY days_to_close)
        FROM analytics.v_request_detail WHERE infrastructure_group IS NOT NULL AND status = 'Closed'
    UNION ALL SELECT 9, 'requests with close date before local open date', count(*) FROM analytics.fact_service_request WHERE date_anomaly
    UNION ALL SELECT 10 + opened_year - 2022, 'requests opened in ' || opened_year, count(*) FROM analytics.v_request_detail GROUP BY opened_year
) s ORDER BY ord;
