-- Analytical views used by the queries and the dashboard.

-- One flat, denormalised row per request, with calendar helpers.
CREATE OR REPLACE VIEW analytics.v_request_detail AS
SELECT f.request_id,
       f.opened_date,
       date_trunc('month', f.opened_date)::date           AS opened_month,
       extract(year  FROM f.opened_date)::int             AS opened_year,
       extract(month FROM f.opened_date)::int             AS opened_month_num,
       CASE WHEN extract(month FROM f.opened_date) IN (12, 1, 2) THEN 'Winter'
            WHEN extract(month FROM f.opened_date) IN (3, 4, 5)  THEN 'Spring'
            WHEN extract(month FROM f.opened_date) IN (6, 7, 8)  THEN 'Summer'
            ELSE 'Autumn' END                              AS season,
       f.status, f.closed_date, f.days_to_close, f.date_anomaly,
       d.department, t.service_request_type, t.infrastructure_group, t.is_legacy,
       a.local_area, ch.channel, cr.closure_reason, cr.outcome_group
FROM analytics.fact_service_request f
JOIN analytics.dim_request_type   t  USING (request_type_id)
JOIN analytics.dim_department     d  USING (department_id)
JOIN analytics.dim_channel        ch USING (channel_id)
JOIN analytics.dim_closure_reason cr USING (closure_reason_id)
LEFT JOIN analytics.dim_local_area a USING (local_area_id);

-- Months that are fully covered by the extract (the latest, partial month is excluded).
CREATE OR REPLACE VIEW analytics.v_complete_months AS
SELECT DISTINCT opened_month
FROM analytics.v_request_detail
WHERE opened_month < (SELECT date_trunc('month', max(opened_date))::date FROM analytics.fact_service_request);

CREATE OR REPLACE VIEW analytics.v_monthly_volume AS
SELECT r.opened_month,
       COALESCE(r.infrastructure_group, 'Non-infrastructure') AS category,
       count(*) AS requests
FROM analytics.v_request_detail r
JOIN analytics.v_complete_months m USING (opened_month)
GROUP BY 1, 2;

-- Closure-time statistics by request type (closed requests with a valid close date only).
CREATE OR REPLACE VIEW analytics.v_closure_duration AS
SELECT infrastructure_group, service_request_type,
       count(*)                                                       AS closed_requests,
       round(avg(days_to_close), 1)                                   AS mean_days,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY days_to_close)     AS median_days,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY days_to_close)     AS p90_days
FROM analytics.v_request_detail
WHERE status = 'Closed' AND days_to_close IS NOT NULL AND NOT is_legacy
GROUP BY 1, 2;
