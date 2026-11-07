-- Q6b. How do residents report infrastructure issues? Channel share per group (CASE pivot).
SELECT COALESCE(infrastructure_group, 'Non-infrastructure') AS category,
       count(*) AS requests,
       round(100.0 * count(*) FILTER (WHERE channel = 'WEB')        / count(*), 1) AS web_pct,
       round(100.0 * count(*) FILTER (WHERE channel = 'Mobile App') / count(*), 1) AS app_pct,
       round(100.0 * count(*) FILTER (WHERE channel = 'Phone')      / count(*), 1) AS phone_pct,
       round(100.0 * count(*) FILTER (WHERE channel NOT IN ('WEB','Mobile App','Phone')) / count(*), 1) AS other_pct
FROM analytics.v_request_detail
GROUP BY 1
ORDER BY requests DESC;
