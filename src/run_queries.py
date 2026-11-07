"""Run every sql/queries/*.sql file and save the result to results/<name>.csv."""
import csv
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results"


def main():
    OUT.mkdir(exist_ok=True)
    with psycopg.connect(dbname=os.environ.get("PGDATABASE", "vancouver_311")) as conn:
        for path in sorted((ROOT / "sql/queries").glob("*.sql")):
            cur = conn.execute(path.read_text())
            rows = cur.fetchall()
            with open(OUT / f"{path.stem}.csv", "w", newline="") as f:
                w = csv.writer(f, lineterminator='\n')
                w.writerow([c.name for c in cur.description])
                w.writerows(rows)
            print(f"{path.name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
