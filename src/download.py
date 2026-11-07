"""Download the 3-1-1 service requests export (all records, 2022 onward) and print snapshot details.

The City refreshes this dataset, so a new download will not match the hash in docs/data_source.md.
"""
import hashlib
import json
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi  # python.org builds of Python on macOS ship without system CA certificates

CTX = ssl.create_default_context(cafile=certifi.where())
BASE = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/3-1-1-service-requests"
OUT = Path(__file__).resolve().parent.parent / "data/raw/3-1-1-service-requests.csv"


def main():
    if OUT.exists():
        sys.exit(f"{OUT} already exists; inspect it and delete it manually to re-download.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    meta = json.load(urllib.request.urlopen(BASE, timeout=60, context=CTX))["metas"]["default"]
    expected = meta["records_count"]
    print("modified:", meta["modified"], "| records:", expected, "| license:", meta["license"])

    url = BASE + "/exports/csv?delimiter=%2C&list_separator=%2C&quote_all=false&with_bom=false"
    part = OUT.with_name(OUT.name + ".part")
    h = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=120, context=CTX) as r, open(part, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
            h.update(chunk)
    with open(part, "rb") as f:
        lines = sum(1 for _ in f) - 1  # minus header; the export has no embedded newlines
    if abs(lines - expected) > 1000:  # the dataset can update during a long download
        part.unlink()
        sys.exit(f"Downloaded {lines:,} rows but the API reports {expected:,}; discarded the file.")
    part.rename(OUT)
    print(f"saved {OUT}: {lines:,} rows, sha256 {h.hexdigest()}")


if __name__ == "__main__":
    main()
