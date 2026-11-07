-- Q4a. Days from open to close by infrastructure request type (closed requests, valid dates).
-- Close date has day resolution only, so same-day closure = 0 days.
SELECT infrastructure_group, service_request_type, closed_requests,
       mean_days, median_days, round(p90_days::numeric, 0) AS p90_days
FROM analytics.v_closure_duration
WHERE infrastructure_group IS NOT NULL AND closed_requests >= 200
ORDER BY median_days DESC, p90_days DESC;
