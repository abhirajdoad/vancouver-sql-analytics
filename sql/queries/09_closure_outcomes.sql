-- Q4b / caveat. What does "Closed" actually mean? Outcome mix by infrastructure group.
-- Only "Service provided" indicates service was delivered; other outcomes include referrals,
-- hand-offs to crews/inspectors, and no-action closures.
SELECT infrastructure_group,
       count(*) AS closed_requests,
       round(100.0 * count(*) FILTER (WHERE outcome_group = 'Service provided')            / count(*), 1) AS service_provided_pct,
       round(100.0 * count(*) FILTER (WHERE outcome_group = 'Action planned / handed off') / count(*), 1) AS action_planned_pct,
       round(100.0 * count(*) FILTER (WHERE outcome_group = 'Referred / redirected')       / count(*), 1) AS referred_pct,
       round(100.0 * count(*) FILTER (WHERE outcome_group = 'No action / unable to act')   / count(*), 1) AS no_action_pct,
       round(100.0 * count(*) FILTER (WHERE outcome_group = 'Other / unknown')             / count(*), 1) AS other_unknown_pct
FROM analytics.v_request_detail
WHERE status = 'Closed' AND infrastructure_group IS NOT NULL
GROUP BY infrastructure_group
ORDER BY closed_requests DESC;
