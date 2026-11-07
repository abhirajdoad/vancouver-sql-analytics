-- Constraints and indexes are added after the bulk insert (faster load).
ALTER TABLE analytics.fact_service_request
    ADD PRIMARY KEY (request_id),
    ADD FOREIGN KEY (request_type_id)   REFERENCES analytics.dim_request_type,
    ADD FOREIGN KEY (local_area_id)     REFERENCES analytics.dim_local_area,
    ADD FOREIGN KEY (channel_id)        REFERENCES analytics.dim_channel,
    ADD FOREIGN KEY (closure_reason_id) REFERENCES analytics.dim_closure_reason,
    ADD CONSTRAINT chk_status CHECK (status IN ('Open', 'Closed')),
    ADD CONSTRAINT chk_closed_consistent CHECK ((status = 'Closed') = (closed_date IS NOT NULL)),
    ADD CONSTRAINT chk_days_nonneg CHECK (days_to_close IS NULL OR days_to_close >= 0);

-- Only indexes that measurably help are kept (see docs/query_optimization.md).
CREATE INDEX idx_fact_opened_date ON analytics.fact_service_request (opened_date);
CREATE INDEX idx_fact_type_opened ON analytics.fact_service_request (request_type_id, opened_date);

ANALYZE analytics.fact_service_request;
