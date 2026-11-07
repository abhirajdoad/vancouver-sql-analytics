-- Raw staging table (all text, loaded as-is) and cleaned model.
DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA staging;
CREATE SCHEMA analytics;

CREATE TABLE staging.service_requests_raw (
    department                     text,
    service_request_type           text,
    status                         text,
    closure_reason                 text,
    service_request_open_timestamp text,
    service_request_close_date     text,
    last_modified_timestamp        text,
    address                        text,
    local_area                     text,
    channel                        text,
    latitude                       text,
    longitude                      text,
    geom                           text
);
