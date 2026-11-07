# Data dictionary

## Source columns (staging.service_requests_raw, all text)

| Column | Meaning | Notes |
|---|---|---|
| department | City unit handling the request | 70 values; two legacy "ZZ" departments |
| service_request_type | Type of case | 255 values; "ZZ - OLD..." are retired types |
| status | Last known status | `Close` or `Open` |
| closure_reason | Reason recorded at closure | 18 values; `N/A` for 16,686 of 16,867 open requests |
| service_request_open_timestamp | When opened | UTC |
| service_request_close_date | When closed | Date only; NULL for open |
| last_modified_timestamp | Last update | UTC |
| address | Block-level address | ~66% NULL; not carried into the model |
| local_area | Neighbourhood (derived from lat/long) | 21% NULL |
| channel | How the request was made | 10 values |
| latitude, longitude, geom | Location | Mostly NULL |

The source has no request ID, so there is no natural key.

## Model (schema `analytics`)

**fact_service_request** (1,323,904 rows): `request_id` (surrogate PK), `request_type_id`, `local_area_id` (nullable),
`channel_id`, `closure_reason_id`, `status` (`Open`/`Closed`), `opened_at` (timestamptz), `opened_date` (America/Vancouver local date),
`closed_date`, `days_to_close` (closed_date - opened_date; NULL if open or anomalous), `date_anomaly` (closed_date earlier than opened_date),
`last_modified_at`, `latitude`, `longitude`.

**Lookups:** `dim_department`, `dim_request_type` (with analyst-defined `infrastructure_group`), `dim_local_area`,
`dim_channel`, `dim_closure_reason` (with analyst-defined `outcome_group`).

**Views:** `v_request_detail` (flat, with season/month/year), `v_complete_months`, `v_monthly_volume`, `v_closure_duration`.

**Constraints:** PK, four FKs, CHECK on status, CHECK that status = Closed exactly when closed_date is present, CHECK days_to_close >= 0.
**Indexes:** `(opened_date)` and `(request_type_id, opened_date)`.
