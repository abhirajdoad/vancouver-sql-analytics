# Vancouver 3-1-1 SQL Analytics

PostgreSQL analysis of 1.32 million City of Vancouver 3-1-1 service requests (January 2022 to November 2026), looking at infrastructure demand: roads, lighting and signals, sewer, water supply, and drainage/flooding.

![Dashboard](docs/screenshots/dashboard.png)

## Contents
- A staging table, a cleaned fact table and five lookup tables in PostgreSQL, with primary/foreign keys, CHECK constraints and two indexes (`sql/01-04`).
- 15 queries in `sql/queries/` (joins, CTEs, window functions, `CASE`/`FILTER` pivots, percentiles, subqueries). Outputs are saved in `results/`.
- An `EXPLAIN ANALYZE` check on one query: about 40 ms without the composite index, about 3 ms with it (`docs/query_optimization.md`).
- `src/validate.py`, which recomputes key figures from the raw CSV in pandas and compares them with the database (11 checks).
- A Streamlit dashboard reading the SQL views. I used Streamlit instead of Power BI because Power BI Desktop is not available on macOS.

## Results
Full findings and limitations are in `docs/methodology.md`. A few examples:
- 110,823 requests (8.4%) fall in the infrastructure groups I defined. Pothole and Street Light Out are the largest types.
- Drainage & Flooding requests are about 2.6 times higher in autumn and winter than in summer (seasonal index 136-137 against 52).
- A closed case is not a fixed problem. Of closed Roads & Sidewalks and Drainage requests, 61.9% and 61.0% have the closure reason "Service provided", against 86.5% for Sewer and 84.2% for Water Supply. The rest were handed off, referred, or closed with no action.

The infrastructure grouping and the closure-outcome grouping are my own classifications, described in the methodology.

## Setup
Python 3.11+ and PostgreSQL 14+ (developed with Python 3.13 and PostgreSQL 16 on macOS). The scripts connect with the standard `PG*` environment variables and default to a database named `vancouver_311`.

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
createdb vancouver_311
python src/download.py       # about 260 MB, takes a few minutes
python src/load.py           # drops and recreates the staging and analytics schemas; about 25 s
python src/validate.py       # exits non-zero if a check fails
python src/run_queries.py    # writes results/*.csv
streamlit run dashboard/app.py
```

The City updates this dataset, so a fresh download will have more rows than the 1,323,904 used here and the numbers will differ slightly. Snapshot details and the file hash are in `docs/data_source.md`.

## Layout
```
sql/            schema, transform, constraints/indexes, views
sql/queries/    analytical queries, each with a header comment
sql/explain/    EXPLAIN ANALYZE script
src/            download, load, run_queries, validate
dashboard/      Streamlit app
docs/           methodology, data dictionary, data source, optimization notes, screenshot
results/        query outputs for the snapshot
```

## Data and licence
Data: City of Vancouver Open Data, 3-1-1 service requests, under the [Open Government Licence - Vancouver](https://opendata.vancouver.ca/pages/licence/). Code: MIT.

I used Claude Code (Anthropic) as a coding assistant while building this project.
