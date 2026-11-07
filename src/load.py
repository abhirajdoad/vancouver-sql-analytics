"""Rebuild the database: schema -> COPY raw CSV into staging -> transform -> constraints/indexes.

Usage: python src/load.py [--csv data/raw/3-1-1-service-requests.csv]
Connection: standard libpq env vars (PGDATABASE defaults to vancouver_311).
"""
import argparse
import os
import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "sql"


def run_sql_file(conn, name):
    t = time.time()
    conn.execute((SQL / name).read_text())
    conn.commit()
    print(f"  {name} ({time.time() - t:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "data/raw/3-1-1-service-requests.csv"))
    args = ap.parse_args()

    dbname = os.environ.get("PGDATABASE", "vancouver_311")
    with psycopg.connect(dbname=dbname) as conn:
        print("Creating schema")
        run_sql_file(conn, "01_schema.sql")

        print("Copying raw CSV into staging.service_requests_raw")
        t = time.time()
        with open(args.csv, "rb") as f, conn.cursor() as cur:
            with cur.copy(
                "COPY staging.service_requests_raw FROM STDIN WITH (FORMAT csv, HEADER true)"
            ) as copy:
                while chunk := f.read(1 << 20):
                    copy.write(chunk)
        conn.commit()
        n = conn.execute("SELECT count(*) FROM staging.service_requests_raw").fetchone()[0]
        print(f"  loaded {n:,} rows ({time.time() - t:.1f}s)")

        for name in ("02_transform.sql", "03_constraints_indexes.sql", "04_views.sql"):
            print(f"Running {name}")
            run_sql_file(conn, name)


if __name__ == "__main__":
    main()
