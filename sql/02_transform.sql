-- Build lookup tables and the cleaned fact table from staging.
-- Timestamps in the source are UTC; they are converted to America/Vancouver so that
-- opened_date is comparable with the (local, date-only) close date.

CREATE TABLE analytics.dim_department (
    department_id serial PRIMARY KEY,
    department    text NOT NULL UNIQUE,
    is_legacy     boolean NOT NULL
);
INSERT INTO analytics.dim_department (department, is_legacy)
SELECT DISTINCT department, department LIKE 'ZZ%'
FROM staging.service_requests_raw
ORDER BY 1;

CREATE TABLE analytics.dim_local_area (
    local_area_id serial PRIMARY KEY,
    local_area    text NOT NULL UNIQUE
);
INSERT INTO analytics.dim_local_area (local_area)
SELECT DISTINCT local_area FROM staging.service_requests_raw
WHERE local_area IS NOT NULL AND local_area <> '' ORDER BY 1;

CREATE TABLE analytics.dim_channel (
    channel_id serial PRIMARY KEY,
    channel    text NOT NULL UNIQUE
);
INSERT INTO analytics.dim_channel (channel)
SELECT DISTINCT channel FROM staging.service_requests_raw ORDER BY 1;

-- closure_reason is what the 311 case record says happened at closure. Only
-- "Service provided" indicates delivered service; the groups below are an analyst
-- classification, not a city-defined field.
CREATE TABLE analytics.dim_closure_reason (
    closure_reason_id serial PRIMARY KEY,
    closure_reason    text NOT NULL UNIQUE,
    outcome_group     text NOT NULL
);
INSERT INTO analytics.dim_closure_reason (closure_reason, outcome_group)
SELECT r.closure_reason,
       CASE
         WHEN r.closure_reason = 'Service provided' THEN 'Service provided'
         WHEN r.closure_reason IN ('Dispatched to Crew','Assigned to inspector','Further action has been planned')
              THEN 'Action planned / handed off'
         WHEN r.closure_reason IN ('Referred to another service group','Closed automatically and sent to service group',
                                   'Alternate Service Required','Not a city provided service / jurisdiction')
              THEN 'Referred / redirected'
         WHEN r.closure_reason IN ('Reviewed and no action planned','Issue not found or inaccessible','Insufficient info',
                                   'Customer unreachable','Outside of Parameters (Sanitation)','Contaminated (Sanitation)')
              THEN 'No action / unable to act'
         ELSE 'Other / unknown'
       END
FROM (SELECT DISTINCT closure_reason FROM staging.service_requests_raw) r
ORDER BY 1;

-- Infrastructure grouping is an explicit analyst-defined mapping (types not listed are non-infrastructure).
CREATE TABLE analytics.dim_request_type (
    request_type_id      serial PRIMARY KEY,
    service_request_type text NOT NULL UNIQUE,
    department_id        int NOT NULL REFERENCES analytics.dim_department,
    infrastructure_group text,            -- NULL = not classified as infrastructure
    is_legacy            boolean NOT NULL -- "ZZ - OLD ..." types retired by the City
);
WITH infra(service_request_type, infrastructure_group) AS (VALUES
  ('Pothole Case',                              'Roads & Sidewalks'),
  ('Street Repair Case',                        'Roads & Sidewalks'),
  ('Sidewalk Repair Case',                      'Roads & Sidewalks'),
  ('Street Construction Concern Case',          'Roads & Sidewalks'),
  ('General Street Issues Case',                'Roads & Sidewalks'),
  ('Bridge and Structures Maintenance Case',    'Roads & Sidewalks'),
  ('Street Surface Water Flooding Case',        'Drainage & Flooding'),
  ('Catch Basin Concern Case',                  'Drainage & Flooding'),
  ('Sewer Backup Case',                         'Sewer'),
  ('Sewer Maintenance Hole Concern Case',       'Sewer'),
  ('Sewer Construction Concern Case',           'Sewer'),
  ('Sewer Operations Inquiry Case',             'Sewer'),
  ('Preventative Maintenance Program Case',     'Sewer'),
  ('Water Leak Case',                           'Water Supply'),
  ('Water Hydrant Concern Case',                'Water Supply'),
  ('Water Pressure Concern Case',               'Water Supply'),
  ('Water Quality Concern Case',                'Water Supply'),
  ('Street Light Out Case',                     'Lighting, Signals & Signs'),
  ('Street Light Pole Maintenance Case',        'Lighting, Signals & Signs'),
  ('Traffic Signal Repair Case',                'Lighting, Signals & Signs'),
  ('Sign Repair Case',                          'Lighting, Signals & Signs'),
  ('Pavement Marking Maintenance Case',         'Lighting, Signals & Signs')
)
INSERT INTO analytics.dim_request_type (service_request_type, department_id, infrastructure_group, is_legacy)
SELECT t.service_request_type, d.department_id, i.infrastructure_group,
       t.service_request_type LIKE 'ZZ%' OR t.department LIKE 'ZZ%'
FROM (SELECT DISTINCT service_request_type, department FROM staging.service_requests_raw) t
JOIN analytics.dim_department d ON d.department = t.department
LEFT JOIN infra i ON i.service_request_type = t.service_request_type
ORDER BY 1;

-- Fact table. Note: the source has no request ID, so there is no natural key;
-- request_id is a surrogate key.
CREATE TABLE analytics.fact_service_request (
    request_id        bigserial,
    request_type_id   int NOT NULL,
    local_area_id     int,
    channel_id        int NOT NULL,
    closure_reason_id int NOT NULL,
    status            text NOT NULL,
    opened_at         timestamptz NOT NULL,
    opened_date       date NOT NULL,        -- America/Vancouver local date
    closed_date       date,
    days_to_close     int,                  -- NULL if open or if closed_date < opened_date (data issue)
    date_anomaly      boolean NOT NULL,     -- closed_date earlier than local opened_date
    last_modified_at  timestamptz,
    latitude          double precision,
    longitude         double precision
);

INSERT INTO analytics.fact_service_request
    (request_type_id, local_area_id, channel_id, closure_reason_id, status, opened_at, opened_date,
     closed_date, days_to_close, date_anomaly, last_modified_at, latitude, longitude)
SELECT rt.request_type_id, a.local_area_id, ch.channel_id, cr.closure_reason_id,
       CASE s.status WHEN 'Close' THEN 'Closed' ELSE s.status END,
       s.opened_at,
       (s.opened_at AT TIME ZONE 'America/Vancouver')::date,
       s.closed_date,
       CASE WHEN s.closed_date >= (s.opened_at AT TIME ZONE 'America/Vancouver')::date
            THEN s.closed_date - (s.opened_at AT TIME ZONE 'America/Vancouver')::date END,
       COALESCE(s.closed_date < (s.opened_at AT TIME ZONE 'America/Vancouver')::date, false),
       s.last_modified_at, s.latitude, s.longitude
FROM (
    SELECT department, service_request_type, status, closure_reason, local_area, channel,
           service_request_open_timestamp::timestamptz AS opened_at,
           NULLIF(service_request_close_date, '')::date AS closed_date,
           NULLIF(last_modified_timestamp, '')::timestamptz AS last_modified_at,
           NULLIF(latitude, '')::double precision AS latitude,
           NULLIF(longitude, '')::double precision AS longitude
    FROM staging.service_requests_raw
) s
JOIN analytics.dim_request_type rt ON rt.service_request_type = s.service_request_type
LEFT JOIN analytics.dim_local_area a ON a.local_area = s.local_area
JOIN analytics.dim_channel ch ON ch.channel = s.channel
JOIN analytics.dim_closure_reason cr ON cr.closure_reason = s.closure_reason;
