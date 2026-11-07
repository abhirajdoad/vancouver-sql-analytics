"""Download the 3-1-1 service requests export (all records, 2022 onward) and print snapshot details."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/3-1-1-service-requests"
OUT = Path(__file__).resolve().parent.parent / "data/raw/3-1-1-service-requests.csv"


def main():
    if OUT.exists():
        sys.exit(f"{OUT} already exists; inspect it and delete it manually to re-download.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    meta = json.load(urllib.request.urlopen(BASE))["metas"]["default"]
    print("modified:", meta["modified"], "| records:", meta["records_count"], "| license:", meta["license"])
    url = BASE + "/exports/csv?delimiter=%2C&list_separator=%2C&quote_all=false&with_bom=false"
    h = hashlib.sha256()
    with urllib.request.urlopen(url) as r, open(OUT, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
            h.update(chunk)
    print("saved", OUT, "sha256", h.hexdigest())


if __name__ == "__main__":
    main()
