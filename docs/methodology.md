# Methodology, findings and limitations

## Pipeline
1. `src/download.py` fetches the CSV; `src/load.py` creates the schema, bulk-loads the CSV with `COPY` into a text-only staging table, then runs `sql/02_transform.sql` (lookups + fact table), `03_constraints_indexes.sql` and `04_views.sql`.
2. `src/run_queries.py` runs the 14 queries in `sql/queries/` and writes `results/*.csv`.
3. `src/validate.py` recomputes row counts, monthly volume, infrastructure totals, neighbourhood counts and median closure days from the raw CSV in pandas and compares them with the database (11 checks, all pass).
4. `dashboard/app.py` (Streamlit + Plotly) reads the views. Power BI Desktop is not available on macOS; Streamlit keeps the dashboard as reviewable code.

## Key decisions
- **Time zone.** Timestamps are UTC but close dates are local dates. Comparing them directly flagged 44,180 requests as closed before they opened; after converting to America/Vancouver only 27 remain. Those 27 are kept, flagged `date_anomaly`, and get a NULL duration.
- **Infrastructure definition.** 22 request types are mapped to five groups (Roads & Sidewalks, Lighting/Signals/Signs, Sewer, Water Supply, Drainage & Flooding) in `02_transform.sql`. This is a judgement; types such as Boulevard Maintenance, Snow and Ice Removal or Water Conservation Violation were left out. Totals change if the mapping changes.
- **Closed is not resolved.** `status = Closed` means the 3-1-1 case was closed. `closure_reason` shows why. Only "Service provided" indicates delivered service; I grouped the other reasons into hand-offs/planned action, referrals, no action, and unknown (`dim_closure_reason.outcome_group`, my classification). Among closed infrastructure requests, 69.1% are "Service provided"; for Roads & Sidewalks it is 60.8% and Drainage & Flooding 61.0%, versus 84% for Sewer and Water Supply (Query 9).
- **Partial month.** November 2026 is incomplete and excluded from monthly, seasonal and trend queries. Year-over-year uses Jan-Oct for every year.

## Findings (snapshot of 2026-11-06)
- 1,323,904 requests; 114,748 (8.7%) fall in the infrastructure groups. Sanitation is the largest department (25.8% of all requests). (Q1)
- Largest infrastructure types: Pothole (19,823), Street Light Out (17,235), Street Repair (9,653), Street Surface Water Flooding (9,564), Sidewalk Repair (9,048). Roads & Sidewalks is the largest group (45,662). (Q2)
- Total monthly volume ranges about 19,000-29,000 with no clear long-run growth: annual totals are 283,839 (2022), 267,128 (2023), 271,017 (2024), 272,567 (2025). 2026 has 229,353 through Nov 5. (Q3, Q10)
- Seasonality differs by group. Drainage & Flooding runs at index 136-137 in winter/autumn and 52 in summer. Roads & Sidewalks peaks in spring (125) and is lowest in autumn (78). Lighting peaks in autumn/winter (115/112). Sewer and Water Supply are close to flat (index 90-115). Weather and shorter daylight are plausible drivers; no weather data was joined, so this is not tested. (Q4)
- Flooding demand is dominated by single days: 326 requests on 2023-12-04 and 281 on 2024-10-19 against trailing 60-day means of about 5-11 per day. Jan-Oct drainage requests rose 34% in 2024 and fell 45.5% in 2025, which is consistent with spike days driving annual change. (Q5, Q11)
- Highest infrastructure request counts: Kensington-Cedar Cottage (9,365), Downtown (8,737), Renfrew-Collingwood (8,401). These are raw counts, not rates. (Q6, Q7)
- Median days to close for infrastructure types ranges from 1 (Sewer Backup, Water Pressure, Pavement Marking) to 8 (Street Light Out). Street Light Out also has a long tail (mean 22 days, 90th percentile 48), and Street Light Pole Maintenance has a 90th percentile of 83 days. (Q8)
- Sewer issues are reported by phone 87% of the time, versus about 37-39% for roads and lighting, which are mostly reported through the web or mobile app. (Q13)
- 1,874 infrastructure requests are still open; 1,134 of them (across all 22 types) are more than 90 days old. Street Repair (325), Sidewalk Repair (219) and Pothole (95) lead, with the oldest about 4.8 years old. Open-and-old may mean unresolved or simply never updated. (Q14)

Possible operational uses: staff drainage/catch-basin crews for autumn-winter and for forecast storm days; review why Roads and Drainage cases close with "action planned/handed off" 20-23% of the time; audit old open cases for clean-up; look at the Street Light Out tail.

## Limitations and bias
- 3-1-1 data measures *reported* demand, not infrastructure condition. Areas with more residents, more pedestrians, or higher reporting propensity generate more requests; neighbourhood counts are not normalised by population or road length.
- 21% of requests lack a neighbourhood (1.1% of infrastructure requests), so neighbourhood totals for non-infrastructure services are understated.
- Close dates have no time of day, so durations have a one-day resolution. Duration only covers closed requests; recent requests are less likely to be closed yet, so recent medians are biased low (Q12 uses a fixed 7-day window to reduce this).
- Channel mix changed over time (mobile app adoption), which can shift volumes between categories independently of real-world issues.
- Request types and department names have been reorganised by the City ("ZZ - OLD..."). Retired types remain in totals but are excluded from closure-duration statistics.
- Duplicate reports of the same problem cannot be identified: there is no request ID and addresses are mostly missing.
- The source dataset is a live extract; results will differ on re-download.
