-- Q1a. Which departments receive the most 3-1-1 requests? (JOIN, aggregate, window share)
SELECT department,
       count(*)                                                  AS requests,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)        AS pct_of_total,
       rank() OVER (ORDER BY count(*) DESC)                      AS volume_rank
FROM analytics.v_request_detail
GROUP BY department
ORDER BY requests DESC
LIMIT 15;
