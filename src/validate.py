"""Independent validation: recompute key metrics from the raw CSV with pandas and compare to the database.

Exits non-zero on any mismatch. Usage: python src/validate.py
"""
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data/raw/3-1-1-service-requests.csv"
failures = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        failures.append(name)


def q(conn, sql):
    return conn.execute(sql).fetchall()


def main():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False, na_values=[""])
    opened = pd.to_datetime(df["service_request_open_timestamp"], utc=True).dt.tz_convert("America/Vancouver")
    df["opened_date"] = opened.dt.tz_localize(None).dt.normalize()
    df["closed_date"] = pd.to_datetime(df["service_request_close_date"])
    df["days"] = (df["closed_date"] - df["opened_date"]).dt.days
    df.loc[df["days"] < 0, "days"] = pd.NA

    with psycopg.connect(dbname=os.environ.get("PGDATABASE", "vancouver_311")) as conn:
        # 1. Row counts
        n_db = q(conn, "SELECT count(*) FROM analytics.fact_service_request")[0][0]
        n_stage = q(conn, "SELECT count(*) FROM staging.service_requests_raw")[0][0]
        check("row count: CSV == staging == fact", len(df) == n_stage == n_db, f"({len(df):,})")

        # 2. Data quality
        check("no fully duplicated rows in source", not df.duplicated().any())
        check("no NULLs in required fact columns", q(conn, """
            SELECT count(*) FROM analytics.fact_service_request
            WHERE request_type_id IS NULL OR channel_id IS NULL OR opened_at IS NULL OR status IS NULL""")[0][0] == 0)
        check("no negative durations stored", q(conn,
            "SELECT count(*) FROM analytics.fact_service_request WHERE days_to_close < 0")[0][0] == 0)
        anomalies = int((df["closed_date"] < df["opened_date"]).sum())
        check("date anomalies (close < open) match", anomalies == q(conn,
            "SELECT count(*) FROM analytics.fact_service_request WHERE date_anomaly")[0][0], f"({anomalies})")
        check("open/closed status counts match",
              dict(q(conn, "SELECT status, count(*) FROM analytics.fact_service_request GROUP BY 1"))
              == {"Closed": int((df.status == "Close").sum()), "Open": int((df.status == "Open").sum())})

        # 3. Monthly volume (all requests, complete months) vs pandas
        pm = df.groupby(df["opened_date"].dt.to_period("M")).size()
        pm = pm.iloc[:-1]  # drop latest partial month
        dbm = dict(q(conn, "SELECT opened_month, sum(requests) FROM analytics.v_monthly_volume GROUP BY 1"))
        ok = len(dbm) == len(pm) and all(dbm[p.to_timestamp().date()] == v for p, v in pm.items())
        check("monthly volume matches pandas", ok, f"({len(pm)} months)")

        # 4. Infrastructure group totals: rebuild mapping from the SQL table, count in pandas
        mapping = dict(q(conn, "SELECT service_request_type, infrastructure_group FROM analytics.dim_request_type "
                               "WHERE infrastructure_group IS NOT NULL"))
        df["grp"] = df["service_request_type"].map(mapping)
        pg = df.groupby("grp").size().to_dict()
        dbg = dict(q(conn, "SELECT infrastructure_group, count(*) FROM analytics.v_request_detail "
                           "WHERE infrastructure_group IS NOT NULL GROUP BY 1"))
        check("infrastructure group totals match pandas", pg == dbg, str(dbg))

        # 5. Neighbourhood counts
        pa = df["local_area"].value_counts().to_dict()
        dba = dict(q(conn, "SELECT local_area, count(*) FROM analytics.v_request_detail "
                           "WHERE local_area IS NOT NULL GROUP BY 1"))
        check("neighbourhood counts match pandas", pa == dba)

        # 6. Median closure days by type (percentile_cont vs pandas median), infra types
        dbmed = dict(q(conn, "SELECT service_request_type, median_days FROM analytics.v_closure_duration "
                             "WHERE infrastructure_group IS NOT NULL"))
        pmed = df[df["grp"].notna() & df["days"].notna() & df["status"].eq("Close")].groupby(
            "service_request_type")["days"].apply(lambda s: s.astype(float).median())
        ok = all(abs(float(dbmed[t]) - pmed[t]) < 1e-9 for t in dbmed) and set(dbmed) <= set(pmed.index)
        check("median closure days match pandas", ok, f"({len(dbmed)} types)")

        # 7. Constraints exist
        n_con = q(conn, "SELECT count(*) FROM pg_constraint WHERE conrelid = 'analytics.fact_service_request'::regclass")[0][0]
        check("fact table constraints present (PK, 4 FK, 3 CHECK)", n_con >= 8, f"({n_con})")

    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("\nAll checks passed")


if __name__ == "__main__":
    main()
