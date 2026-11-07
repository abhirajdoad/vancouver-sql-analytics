"""Streamlit dashboard for the Vancouver 3-1-1 analytics database.

Run: streamlit run dashboard/app.py   (PostgreSQL must be loaded via src/load.py)
"""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg
import streamlit as st

DB = os.environ.get("PGDATABASE", "vancouver_311")
GROUPS = ["Roads & Sidewalks", "Lighting, Signals & Signs", "Sewer", "Water Supply", "Drainage & Flooding"]
# Okabe-Ito colour-blind-safe palette, one colour per infrastructure group.
COLORS = dict(zip(GROUPS, ["#0072B2", "#E69F00", "#009E73", "#56B4E9", "#CC79A7"]))
SEASONS = ["Winter", "Spring", "Summer", "Autumn"]
TEMPLATE = "plotly_white"

st.set_page_config(page_title="Vancouver 3-1-1 Infrastructure Requests", layout="wide")
st.markdown(
    "<style>.block-container{padding-top:2rem;max-width:1300px}"
    "[data-testid=stMetricValue]{font-size:1.9rem}</style>",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    with psycopg.connect(dbname=DB) as conn:
        cur = conn.execute(sql, params)
        return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


meta = query("SELECT min(opened_date) lo, max(opened_date) hi, count(*) n FROM analytics.fact_service_request").iloc[0]
last_complete = query("SELECT max(opened_month) m FROM analytics.v_complete_months").iloc[0]["m"]

st.title("Vancouver 3-1-1 Service Requests: Infrastructure Demand")
st.caption(
    f"{meta.n:,} requests opened {meta.lo:%b %d, %Y} to {meta.hi:%b %d, %Y}. Source: City of Vancouver Open Data, "
    "Open Government Licence - Vancouver. Monthly and seasonal charts use complete months only "
    f"(through {pd.Timestamp(last_complete):%b %Y})."
)

with st.sidebar:
    st.header("Filters")
    sel_groups = st.multiselect("Infrastructure groups", GROUPS, default=GROUPS)
    years = st.slider("Year opened", int(meta.lo.year), int(meta.hi.year), (int(meta.lo.year), int(meta.hi.year)))
    st.caption("Filters apply to the infrastructure sections. 'Infrastructure' is an analyst-defined grouping "
               "of request types (see docs/methodology.md).")

if not sel_groups:
    st.warning("Select at least one infrastructure group.")
    st.stop()
G, Y = list(sel_groups), years

# ---- KPIs ----------------------------------------------------------------
k = query(
    """SELECT count(*) AS infra,
              count(*) FILTER (WHERE status = 'Open') AS open_n,
              count(*) FILTER (WHERE outcome_group = 'Service provided' AND status = 'Closed') AS provided,
              count(*) FILTER (WHERE status = 'Closed') AS closed,
              percentile_cont(0.5) WITHIN GROUP (ORDER BY days_to_close) AS median_days
       FROM analytics.v_request_detail
       WHERE infrastructure_group = ANY(%s) AND opened_year BETWEEN %s AND %s""", (G, *Y)).iloc[0]
total = query("SELECT count(*) n FROM analytics.v_request_detail WHERE opened_year BETWEEN %s AND %s", Y).iloc[0].n

c = st.columns(5)
c[0].metric("All 3-1-1 requests", f"{total:,}")
c[1].metric(f"Infrastructure ({k.infra / total:.1%})", f"{int(k.infra):,}")
c[2].metric("Median days to close", f"{k.median_days:.0f}" if pd.notna(k.median_days) else "n/a")
c[3].metric("Closed as 'Service provided'", f"{k.provided / k.closed:.0%}" if k.closed else "n/a")
c[4].metric("Still open", f"{int(k.open_n):,}")
st.caption("'Closed' is a 3-1-1 case status. Only the 'Service provided' closure reason indicates delivered service; "
           "other reasons include referrals, hand-offs to crews and no-action closures.")

# ---- Monthly volume -------------------------------------------------------
st.subheader("Monthly request volume")
mv = query("SELECT opened_month, category, requests FROM analytics.v_monthly_volume ORDER BY 1")
mv["opened_month"] = pd.to_datetime(mv["opened_month"])
mv = mv[(mv.opened_month.dt.year >= Y[0]) & (mv.opened_month.dt.year <= Y[1])]
left, right = st.columns(2)
tot = mv.groupby("opened_month", as_index=False).requests.sum()
f1 = px.line(tot, x="opened_month", y="requests", template=TEMPLATE, title="All 3-1-1 requests")
f1.update_traces(line_color="#444444")
f1.update_layout(xaxis_title=None, yaxis_title="Requests per month", yaxis_rangemode="tozero", margin=dict(t=50, b=10))
left.plotly_chart(f1, width="stretch")
inf = mv[mv.category.isin(sel_groups)]
f2 = px.bar(inf, x="opened_month", y="requests", color="category", color_discrete_map=COLORS,
            category_orders={"category": GROUPS}, template=TEMPLATE, title="Infrastructure requests by group")
f2.update_layout(xaxis_title=None, yaxis_title="Requests per month", legend_title=None,
                 legend=dict(orientation="h", y=-0.15), margin=dict(t=50, b=10))
right.plotly_chart(f2, width="stretch")

# ---- Categories & neighbourhoods -----------------------------------------
st.subheader("Where demand comes from")
left, right = st.columns(2)
types = query(
    """SELECT infrastructure_group, regexp_replace(service_request_type, ' Case$', '') AS request_type, count(*) AS requests
       FROM analytics.v_request_detail
       WHERE infrastructure_group = ANY(%s) AND opened_year BETWEEN %s AND %s GROUP BY 1, 2
       ORDER BY 3 DESC LIMIT 15""", (G, *Y)).sort_values("requests")
f3 = px.bar(types, x="requests", y="request_type", color="infrastructure_group", color_discrete_map=COLORS,
            orientation="h", template=TEMPLATE, title="Top 15 infrastructure request types",
            category_orders={"request_type": types.request_type.tolist()})
f3.update_layout(yaxis_title=None, xaxis_title="Requests", legend_title=None, legend=dict(orientation="h", y=-0.2),
                 margin=dict(t=50, b=10))
left.plotly_chart(f3, width="stretch")

nb = query(
    """SELECT local_area, infrastructure_group, count(*) AS requests
       FROM analytics.v_request_detail
       WHERE infrastructure_group = ANY(%s) AND local_area IS NOT NULL AND opened_year BETWEEN %s AND %s
       GROUP BY 1, 2""", (G, *Y))
order = nb.groupby("local_area").requests.sum().sort_values().index.tolist()
f4 = px.bar(nb, x="requests", y="local_area", color="infrastructure_group", color_discrete_map=COLORS,
            orientation="h", template=TEMPLATE, title="Infrastructure requests by neighbourhood (raw counts)",
            category_orders={"local_area": order})
f4.update_layout(yaxis_title=None, xaxis_title="Requests", showlegend=False, height=520, margin=dict(t=50, b=10))
right.plotly_chart(f4, width="stretch")
right.caption("Raw counts, not per capita; neighbourhood population and area differ. "
              "Requests without a recorded location are excluded here.")

# ---- Closure durations ----------------------------------------------------
st.subheader("Time to close")
left, right = st.columns(2)
dur = query(
    """SELECT infrastructure_group, days_to_close
       FROM analytics.v_request_detail
       WHERE status = 'Closed' AND days_to_close IS NOT NULL AND infrastructure_group = ANY(%s)
         AND opened_year BETWEEN %s AND %s""", (G, *Y))
f5 = px.box(dur, x="infrastructure_group", y="days_to_close", color="infrastructure_group", color_discrete_map=COLORS,
            category_orders={"infrastructure_group": GROUPS}, template=TEMPLATE, points=False,
            title="Days from open to close (closed requests)")
f5.update_yaxes(range=[0, 60], title="Days (axis capped at 60)")
f5.update_layout(xaxis_title=None, showlegend=False, margin=dict(t=50, b=10))
left.plotly_chart(f5, width="stretch")
left.caption("Close date has day resolution, so same-day closure is 0 days. Recently opened requests are less "
             "likely to be closed yet, which biases recent durations downward.")

out = query(
    """SELECT infrastructure_group, outcome_group, count(*) AS n
       FROM analytics.v_request_detail
       WHERE status = 'Closed' AND infrastructure_group = ANY(%s) AND opened_year BETWEEN %s AND %s
       GROUP BY 1, 2""", (G, *Y))
out["pct"] = 100 * out.n / out.groupby("infrastructure_group").n.transform("sum")
OUT_ORDER = ["Service provided", "Action planned / handed off", "Referred / redirected",
             "No action / unable to act", "Other / unknown"]
f6 = px.bar(out, x="pct", y="infrastructure_group", color="outcome_group", orientation="h", template=TEMPLATE,
            category_orders={"outcome_group": OUT_ORDER, "infrastructure_group": GROUPS[::-1]},
            color_discrete_sequence=["#0072B2", "#56B4E9", "#E69F00", "#999999", "#DDDDDD"],
            title="What 'Closed' means: closure outcome mix")
f6.update_layout(xaxis_title="% of closed requests", yaxis_title=None, legend_title=None,
                 legend=dict(orientation="h", y=-0.25), margin=dict(t=50, b=10))
right.plotly_chart(f6, width="stretch")

# ---- Seasonality ----------------------------------------------------------
st.subheader("Seasonal pattern")
sea = query("""
    SELECT category, season, avg(requests) AS avg_monthly
    FROM (SELECT v.category, v.requests,
                 CASE WHEN extract(month FROM v.opened_month) IN (12,1,2) THEN 'Winter'
                      WHEN extract(month FROM v.opened_month) IN (3,4,5) THEN 'Spring'
                      WHEN extract(month FROM v.opened_month) IN (6,7,8) THEN 'Summer' ELSE 'Autumn' END AS season
          FROM analytics.v_monthly_volume v
          WHERE extract(year FROM v.opened_month) BETWEEN %s AND %s) s
    GROUP BY 1, 2""", Y)
sea["avg_monthly"] = sea["avg_monthly"].astype(float)
sea = sea[sea.category.isin(sel_groups)]
sea["index"] = 100 * sea.avg_monthly / sea.groupby("category").avg_monthly.transform("mean")
heat = sea.pivot(index="category", columns="season", values="index").reindex(
    [g for g in GROUPS if g in sel_groups])[SEASONS]
f7 = go.Figure(go.Heatmap(z=heat.values, x=SEASONS, y=heat.index, zmid=100, zmin=20, zmax=180,
                          colorscale="RdBu_r", text=heat.round(0).astype(int).values, texttemplate="%{text}",
                          colorbar=dict(title="Index")))
f7.update_layout(template=TEMPLATE, title="Seasonal index (100 = mean of the group's four season averages)",
                 yaxis_autorange="reversed", margin=dict(t=50, b=10), height=330)
st.plotly_chart(f7, width="stretch")

# ---- Observations ------------------------------------------------------
st.subheader("Operational observations")
top_type = types.iloc[-1]
top_nb = order[-1]
fl = sea[sea.category == "Drainage & Flooding"].set_index("season")["index"] if "Drainage & Flooding" in sel_groups else None
slow = query(
    """SELECT regexp_replace(service_request_type, ' Case$', '') AS t,
              percentile_cont(0.5) WITHIN GROUP (ORDER BY days_to_close) AS median_days,
              percentile_cont(0.9) WITHIN GROUP (ORDER BY days_to_close) AS p90_days
       FROM analytics.v_request_detail
       WHERE status = 'Closed' AND days_to_close IS NOT NULL AND NOT is_legacy
         AND infrastructure_group = ANY(%s) AND opened_year BETWEEN %s AND %s
       GROUP BY 1 HAVING count(*) >= 200 ORDER BY p90_days DESC LIMIT 1""", (G, *Y))
spikes = query(
    """SELECT opened_date, count(*) AS requests FROM analytics.v_request_detail
       WHERE infrastructure_group = 'Drainage & Flooding' AND opened_year BETWEEN %s AND %s
       GROUP BY 1 ORDER BY 2 DESC LIMIT 1""", Y)
bullets = [
    f"**{top_type.request_type}** is the largest infrastructure request type in the selected period "
    f"({int(top_type.requests):,} requests); **{top_nb}** has the most infrastructure requests of any neighbourhood.",
]
if fl is not None and not fl.empty:
    bullets.append(f"Drainage and flooding requests peak at {fl.max():.0f} on the seasonal index ({fl.idxmax()}) "
                   f"and bottom out at {fl.min():.0f} ({fl.idxmin()}). Weather was not analysed here.")
if not slow.empty:
    s = slow.iloc[0]
    bullets.append(f"**{s.t}** has the longest tail among closed requests: median {s.median_days:.0f} days, 90th percentile {s.p90_days:.0f} days.")
if "Drainage & Flooding" in sel_groups and len(spikes):
    bullets.append(f"The busiest single day for drainage and flooding requests in these years was "
                   f"{spikes.iloc[0].opened_date:%b %d, %Y} ({int(spikes.iloc[0].requests):,} requests).")
for b in bullets:
    st.markdown(f"- {b}")
st.caption("Observations describe reported 3-1-1 demand, not physical infrastructure condition. See docs/methodology.md for limitations.")
