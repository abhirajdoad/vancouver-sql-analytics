# Methodology, findings and limitations

## Pipeline
1. `src/download.py` fetches the CSV. `src/load.py` creates the schema, bulk-loads the CSV with `COPY` into a text-only staging table, then runs `02_transform.sql` (lookups and fact table), `03_constraints_indexes.sql` and `04_views.sql`.
2. `src/run_queries.py` runs the 15 queries in `sql/queries/` and writes `results/*.csv`. Every number quoted below comes from one of those files.
3. `src/validate.py` recomputes results from the raw CSV in pandas and compares them with the database (11 checks): row counts, status counts, date anomalies, the sum of per-row `days_to_close`, monthly volume, the infrastructure type list (restated in the script), group totals, neighbourhood counts, median closure days, and the "Service provided" count.
4. `dashboard/app.py` reads the views.

## Decisions and assumptions
- **Time zone.** Source timestamps are UTC, close dates are local dates. Comparing them directly flagged 44,180 requests as closed before they opened; after converting to America/Vancouver, 27 remain. Those are kept, flagged `date_anomaly`, and get a NULL duration.
- **Infrastructure definition (subjective).** 24 request types are mapped to five groups in `02_transform.sql`: Roads & Sidewalks, Lighting/Signals/Signs, Sewer, Water Supply, Drainage & Flooding. I included reports of defects, damage, leaks, outages and maintenance. I excluded inquiries, permit/meter/service-line requests, requests for new assets (new signs, signals, light poles), construction-concern complaints, street cleaning and litter, and bylaw cases. Borderline inclusions: `Preventative Maintenance Program Case` (it sits under Sewer Operations), `General Street Issues Case`, and `Water Quality Concern Case`. The totals depend on this list; changing it changes every infrastructure figure.
- **Closed is not resolved.** `status = Closed` means the 3-1-1 case was closed. `closure_reason` records why. Only "Service provided" indicates that service was delivered. I grouped the other 17 reasons into four outcome groups (hand-off/action planned, referred, no action, unknown) in `dim_closure_reason.outcome_group`; that grouping is my own. Even "Service provided" is a case-system label, not a verified repair.
- **Partial month.** November 2026 is incomplete and is excluded from the monthly, seasonal and trend queries. Year-over-year compares January to October of each year.
- **Seasons** are meteorological (Dec-Feb, Mar-May, Jun-Aug, Sep-Nov). The seasonal index is a season's average monthly count divided by the mean of that group's four season averages. Winter and autumn have 14 observed months, spring and summer 15.
- **Closure durations** use closed requests with a valid close date, in whole days. Retired types ("ZZ - OLD", "Z - ") are excluded from duration statistics but not from volume counts.

## Findings (snapshot of 2026-11-06)
- There are 1,323,904 requests; 110,823 (8.4%) are in the infrastructure groups. Sanitation is the largest department (25.8% of all requests) (Q1, Q15).
- Largest infrastructure types: Pothole (19,823), Street Light Out (17,235), Street Repair (9,653), Street Surface Water Flooding (9,564) and Sidewalk Repair (9,048). Roads & Sidewalks is the largest group (42,725), then Lighting, Signals & Signs (34,479) (Q2).
- Monthly volume ranges from 18,972 to 29,182 with no clear long-run growth: annual totals are 283,839 (2022), 267,128 (2023), 271,017 (2024) and 272,567 (2025), and January-October totals are 235,714, 224,956, 226,307, 230,661 and 225,864 for 2022-2026 (Q3, Q15).
- Seasonal index by group (Q4): Drainage & Flooding is 136 in winter and 137 in autumn against 52 in summer. Roads & Sidewalks peaks in spring (127) and is lowest in autumn (76). Lighting is highest in autumn and winter (114, 110). Sewer is highest in autumn (122) and between 86 and 96 otherwise. Water Supply peaks in summer (111). The drainage autumn/winter peak appears in each year. I did not join weather data, so I can only describe the pattern, not explain it.
- Drainage & Flooding has a few extreme days: 326 requests on 2023-12-04 and 281 on 2024-10-19 against trailing 60-day means of 10.6 and 5.1 (Q11). They are not what drives its annual swings, though. The ten busiest days are 13.0% of all drainage requests and the thirty busiest 22.7%. January-October drainage requests rose 34.0% in 2024 and fell 45.5% in 2025 (Q5); excluding days with 50 or more requests the counts are 1,772 and 1,029 (a 42% fall), so the 2025 drop is not a spike effect. I do not know why 2025 was lower.
- Highest infrastructure request counts by neighbourhood: Kensington-Cedar Cottage (9,069), Downtown (8,610) and Renfrew-Collingwood (8,183). These are raw counts, not rates (Q6, Q7).
- Median days to close for infrastructure types ranges from 1 (Sewer Backup, Water Pressure, Pavement Marking Maintenance) to 10 (Pavement Markings). Street Light Out has a median of 8 days but a mean of 22.3 and a 90th percentile of 48; Street Light Pole Maintenance has a 90th percentile of 83 days (Q8).
- Outcome mix for closed infrastructure requests (Q9, Q15): 69.4% overall are "Service provided". By group: Sewer 86.5%, Water Supply 84.2%, Lighting 70.7%, Roads & Sidewalks 61.9%, Drainage & Flooding 61.0%. For Roads and Drainage, 20.4% and 22.7% were closed with "Further action has been planned", "Assigned to inspector" or "Dispatched to Crew", meaning the work continued elsewhere.
- Sewer problems are reported by phone 87.3% of the time, versus 37.1% for Roads and 37.0% for Lighting, which are mostly reported through the web or app (Q13).
- 1,854 infrastructure requests are open; 1,133 of them are more than 90 days old. Street Repair (325), Sidewalk Repair (219) and Pothole (95) have the most, and the oldest is about 4.8 years (Q14, Q15). An old open case may be unresolved or simply never updated.
- Year-over-year change by group is in Q5 and the 12-month comparison in Q10. Roads & Sidewalks fell 15.8% in 2023 and has been within about 6% of the prior year since. I did not investigate the 2023 drop.

## Limitations
- 3-1-1 data measures reported demand, not infrastructure condition. Neighbourhoods with more residents, foot traffic or reporting habit generate more requests; counts are not normalised by population or road length.
- 21.5% of requests have no neighbourhood, but only 2.6% of infrastructure requests (2,939) do. Non-infrastructure neighbourhood totals are understated more.
- Close dates have no time of day, so durations have one-day resolution. Durations only cover closed requests, and recently opened requests are less likely to be closed yet, which biases recent medians low. Q12 uses a fixed 7-day window to reduce this.
- The City reorganised request types during the period. `General Street Issues` and `Preventative Maintenance Program` first appear in August 2022, and `Sewer Operations Inquiry` falls from 593 requests in 2022 to 227 in 2023. Comparisons against 2022 are affected, and some "ZZ - OLD" types are retired.
- The channel mix changed over time (mobile app share was 18.5% in 2022, 15.8% in 2024 and 22.4% in 2026), which can move volume between categories independently of real-world conditions.
- Duplicate reports of the same problem cannot be identified: there is no request ID and most addresses are missing.
- One request has a close date of 2026-11-29, after the snapshot date. It is kept as loaded.
- The source dataset is a live extract; a new download will differ from these results.
