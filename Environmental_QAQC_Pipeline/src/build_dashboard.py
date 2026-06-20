"""
build_dashboard.py
Builds a static, self-contained interactive dashboard (Chart.js via CDN)
summarizing QA/QC and regulatory compliance KPIs -- the same end deliverable
a Power BI report would produce, packaged so it can be hosted anywhere
(no Power BI Service license required to view it).
"""
import pandas as pd
import json

OUT = "/home/claude/envqaqc/outputs"
df = pd.read_csv(f"{OUT}/validated_dataset.csv")
validation_summary = pd.read_csv(f"{OUT}/validation_summary.csv")

df["collection_date"] = pd.to_datetime(df["collection_date"])
df["quarter"] = df["collection_date"].dt.to_period("Q").astype(str)

total_records = len(df)
overall_pass_rate = round((df["overall_qaqc_status"] == "PASS").mean() * 100, 1)
total_exceedances = int(df["flag_regulatory_exceedance"].sum())
exceedance_rate = round(df[df["regulatory_mcl"].notna()]["flag_regulatory_exceedance"].mean() * 100, 1)
holding_violations = int(df["flag_holding_time_violation"].sum())
n_sites = df["site_id"].nunique()
n_locations = df["location_id"].nunique()

check_labels = validation_summary["check_category"].tolist()
fail_rates = validation_summary["fail_rate_pct"].tolist()

trend = df[df["regulatory_mcl"].notna()].groupby("quarter")["flag_regulatory_exceedance"].mean().reset_index()
trend["pct"] = round(trend["flag_regulatory_exceedance"] * 100, 2)
quarters = trend["quarter"].tolist()
trend_vals = trend["pct"].tolist()

by_analyte = df[df["regulatory_mcl"].notna()].groupby("analyte")["flag_regulatory_exceedance"].mean().sort_values(ascending=False) * 100
analyte_labels = by_analyte.index.tolist()
analyte_vals = [round(v, 1) for v in by_analyte.values.tolist()]

by_site = df[df["regulatory_mcl"].notna()].groupby("site_name")["flag_regulatory_exceedance"].mean().sort_values(ascending=False) * 100
site_labels = by_site.index.tolist()
site_vals = [round(v, 1) for v in by_site.values.tolist()]

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Environmental Data QA/QC & Regulatory Compliance Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; background:#f3f4f6; margin:0; padding:24px; color:#1f2937; }}
  h1 {{ font-size:20px; margin-bottom:4px; }}
  .sub {{ color:#6b7280; margin-bottom:20px; font-size:13px; }}
  .kpis {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
  .kpi {{ background:white; border-radius:10px; padding:16px 20px; box-shadow:0 1px 3px rgba(0,0,0,0.1); min-width:160px; flex:1; }}
  .kpi .val {{ font-size:26px; font-weight:bold; }}
  .kpi .label {{ font-size:12px; color:#6b7280; margin-top:4px; }}
  .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:20px; }}
  .card {{ background:white; border-radius:10px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
  .card h3 {{ margin:0 0 12px; font-size:14px; color:#374151; }}
  .green {{ color:#16a34a; }} .red {{ color:#dc2626; }} .orange {{ color:#d97706; }} .blue {{ color:#2563eb; }}
</style>
</head>
<body>
<h1>Environmental Data QA/QC &amp; Regulatory Compliance Dashboard</h1>
<div class="sub">{n_sites} sites · {n_locations} monitoring locations · {total_records:,} analytical records</div>

<div class="kpis">
  <div class="kpi"><div class="val green">{overall_pass_rate}%</div><div class="label">Overall QA/QC Pass Rate</div></div>
  <div class="kpi"><div class="val red">{total_exceedances}</div><div class="label">Regulatory (MCL) Exceedances</div></div>
  <div class="kpi"><div class="val orange">{exceedance_rate}%</div><div class="label">Exceedance Rate</div></div>
  <div class="kpi"><div class="val blue">{holding_violations}</div><div class="label">Holding Time Violations</div></div>
</div>

<div class="grid">
  <div class="card"><h3>Data Quality Issues by Check Category (% fail)</h3><canvas id="c1"></canvas></div>
  <div class="card"><h3>MCL Exceedance Rate by Quarter</h3><canvas id="c2"></canvas></div>
  <div class="card"><h3>MCL Exceedance Rate by Analyte</h3><canvas id="c3"></canvas></div>
  <div class="card"><h3>MCL Exceedance Rate by Site</h3><canvas id="c4"></canvas></div>
</div>

<script>
const palette = ['#2563eb','#d97706','#16a34a','#dc2626','#7c3aed'];

new Chart(document.getElementById('c1'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(check_labels)}, datasets: [{{ label: '% Fail', data: {json.dumps(fail_rates)}, backgroundColor: palette }}] }},
  options: {{ plugins: {{ legend: {{ display:false }} }}, scales: {{ y: {{ beginAtZero:true, title:{{display:true, text:'% Fail'}} }} }} }}
}});

new Chart(document.getElementById('c2'), {{
  type: 'line',
  data: {{ labels: {json.dumps(quarters)}, datasets: [{{ label:'% Exceedance', data: {json.dumps(trend_vals)}, borderColor:'#dc2626', backgroundColor:'rgba(220,38,38,0.1)', tension:0.3, fill:true }}] }},
  options: {{ scales: {{ y: {{ beginAtZero:true, title:{{display:true, text:'% Exceeding MCL'}} }} }} }}
}});

new Chart(document.getElementById('c3'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(analyte_labels)}, datasets: [{{ label:'% Exceedance', data: {json.dumps(analyte_vals)}, backgroundColor:'#2563eb' }}] }},
  options: {{ indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales: {{ x: {{ beginAtZero:true }} }} }}
}});

new Chart(document.getElementById('c4'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(site_labels)}, datasets: [{{ label:'% Exceedance', data: {json.dumps(site_vals)}, backgroundColor:'#16a34a' }}] }},
  options: {{ plugins:{{legend:{{display:false}}}}, scales: {{ y: {{ beginAtZero:true }} }} }}
}});
</script>
</body>
</html>
"""

with open(f"{OUT}/dashboard.html", "w") as f:
    f.write(html)

print("Dashboard saved.")
