"""Recompute key metrics from the raw CSV with pandas and compare them with the database.

The infrastructure classification is deliberately restated below so it is checked against the
database table rather than read back from it. Exits non-zero on any failure.
Usage: python src/validate.py
"""
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data/raw/3-1-1-service-requests.csv"

ROADS, LIGHT, SEWER, WATER, DRAIN = ("Roads & Sidewalks", "Lighting, Signals & Signs", "Sewer",
                                     "Water Supply", "Drainage & Flooding")
INFRA = {
    "Pothole Case": ROADS, "Street Repair Case": ROADS, "Sidewalk Repair Case": ROADS,
    "General Street Issues Case": ROADS, "Bridge and Structures Maintenance Case": ROADS,
    "Street Surface Water Flooding Case": DRAIN, "Catch Basin Concern Case": DRAIN,
    "Sewer Backup Case": SEWER, "Sewer Maintenance Hole Concern Case": SEWER, "Sewer Odour Case": SEWER,
    "Sewer Utility Damage Case": SEWER, "Preventative Maintenance Program Case": SEWER,
    "Water Leak Case": WATER, "Water Hydrant Concern Case": WATER, "Water Pressure Concern Case": WATER,
    "Water Quality Concern Case": WATER, "Damage to Water System Case": WATER,
    "Street Light Out Case": LIGHT, "Street Light Pole Maintenance Case": LIGHT, "Traffic Signal Repair Case": LIGHT,
    "Sign Repair Case": LIGHT, "Street or Traffic Light Utility Damage Case": LIGHT,
    "Pavement Markings Case": LIGHT, "Pavement Marking Maintenance Case": LIGHT,
}
failures = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        failures.append(name)


def main():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False, na_values=[""])
    opened = pd.to_datetime(df["service_request_open_timestamp"], utc=True).dt.tz_convert("America/Vancouver")
    df["opened_date"] = opened.dt.tz_localize(None).dt.normalize()
    df["closed_date"] = pd.to_datetime(df["service_request_close_date"])
    df["days"] = (df["closed_date"] - df["opened_date"]).dt.days
    df.loc[df["days"] < 0, "days"] = pd.NA
    df["grp"] = df["service_request_type"].map(INFRA)
    closed = df["status"].eq("Close")

    with psycopg.connect(dbname=os.environ.get("PGDATABASE", "vancouver_311")) as conn:
        def q(sql):
            return conn.execute(sql).fetchall()

        n_db = q("SELECT count(*) FROM analytics.fact_service_request")[0][0]
        n_stage = q("SELECT count(*) FROM staging.service_requests_raw")[0][0]
        check("row count: CSV == staging == fact", len(df) == n_stage == n_db, f"({len(df):,})")
        check("no fully duplicated source rows", not df.duplicated().any())
        check("open/closed counts match",
              dict(q("SELECT status, count(*) FROM analytics.fact_service_request GROUP BY 1"))
              == {"Closed": int(closed.sum()), "Open": int((~closed).sum())})
        anomalies = int((df["closed_date"] < df["opened_date"]).sum())
        check("local-date anomalies (close < open) match",
              anomalies == q("SELECT count(*) FROM analytics.fact_service_request WHERE date_anomaly")[0][0],
              f"({anomalies})")
        check("sum of per-row days_to_close matches",
              int(df["days"].dropna().astype("int64").sum())
              == q("SELECT sum(days_to_close) FROM analytics.fact_service_request")[0][0])

        pm = df.groupby(df["opened_date"].dt.to_period("M")).size().iloc[:-1]  # drop the partial last month
        dbm = dict(q("SELECT opened_month, sum(requests) FROM analytics.v_monthly_volume GROUP BY 1"))
        check("monthly volume matches", len(dbm) == len(pm) and all(dbm[p.to_timestamp().date()] == v for p, v in pm.items()),
              f"({len(pm)} months)")

        db_map = dict(q("SELECT service_request_type, infrastructure_group FROM analytics.dim_request_type "
                        "WHERE infrastructure_group IS NOT NULL"))
        check("infrastructure type mapping equals the list in this file", db_map == INFRA, f"({len(INFRA)} types)")
        check("infrastructure group totals match",
              df.groupby("grp").size().to_dict()
              == dict(q("SELECT infrastructure_group, count(*) FROM analytics.v_request_detail "
                        "WHERE infrastructure_group IS NOT NULL GROUP BY 1")))
        check("neighbourhood counts match",
              df["local_area"].value_counts().to_dict()
              == dict(q("SELECT local_area, count(*) FROM analytics.v_request_detail "
                        "WHERE local_area IS NOT NULL GROUP BY 1")))

        dbmed = dict(q("SELECT service_request_type, median_days FROM analytics.v_closure_duration "
                       "WHERE infrastructure_group IS NOT NULL"))
        pmed = df[df["grp"].notna() & df["days"].notna() & closed & ~df["service_request_type"].str.match(r"^ZZ? ?-")] \
            .groupby("service_request_type")["days"].apply(lambda s: s.astype(float).median())
        check("median closure days match (same set of types)",
              set(dbmed) == set(pmed.index) and all(abs(float(dbmed[t]) - pmed[t]) < 1e-9 for t in dbmed),
              f"({len(dbmed)} types)")

        sp = df[df["grp"].notna() & closed & df["closure_reason"].eq("Service provided")].shape[0]
        sp_db = q("SELECT count(*) FROM analytics.v_request_detail WHERE infrastructure_group IS NOT NULL "
                  "AND status = 'Closed' AND closure_reason = 'Service provided'")[0][0]
        unmapped = q("SELECT count(*) FROM analytics.dim_closure_reason WHERE outcome_group IS NULL")[0][0]
        check("'Service provided' count (infrastructure) matches; all reasons mapped", sp == sp_db and unmapped == 0, f"({sp:,})")

    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("\nAll checks passed")


if __name__ == "__main__":
    main()
