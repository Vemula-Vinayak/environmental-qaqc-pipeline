"""
generate_gis_map.py
Builds an interactive Leaflet map of all sample locations, color-coded by
QA/QC validation status and regulatory exceedance status. Uses plain
HTML/JS (Leaflet via CDN) so it requires no ArcGIS license and no
geopandas/folium install -- runs anywhere, including as a static deployable
artifact, which is the same outcome GIS staff would want from a
shareable web map.
"""
import pandas as pd
import json

OUT = "/home/claude/envqaqc/outputs"
df = pd.read_csv(f"{OUT}/validated_dataset.csv")

# One marker per location, summarizing worst-case status at that location
loc_groups = df.groupby(["location_id", "site_name", "latitude", "longitude"]).agg(
    n_samples=("sample_id", "count"),
    n_qaqc_fail=("overall_qaqc_status", lambda s: (s == "FAIL").sum()),
    n_exceedance=("flag_regulatory_exceedance", "sum"),
).reset_index()

def classify(row):
    exceed_rate = row["n_exceedance"] / row["n_samples"]
    fail_rate = row["n_qaqc_fail"] / row["n_samples"]
    if exceed_rate >= 0.15:
        return "exceedance"
    if fail_rate >= 0.15:
        return "qaqc_fail"
    return "pass"

loc_groups["status"] = loc_groups.apply(classify, axis=1)

points = loc_groups.to_dict(orient="records")
points_json = json.dumps(points)

color_map = {"pass": "#2ecc71", "qaqc_fail": "#f39c12", "exceedance": "#e74c3c"}

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Environmental Sampling Locations — QA/QC & Regulatory Status</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; font-family: Arial, sans-serif; }}
  #map {{ height: 92vh; width: 100%; }}
  #header {{ padding: 10px 16px; background:#1f2937; color:white; font-size:16px; }}
  .legend {{ background: white; padding: 8px 12px; border-radius: 6px; line-height: 1.6; font-size: 13px; box-shadow: 0 1px 4px rgba(0,0,0,0.3); }}
  .dot {{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:6px; }}
</style>
</head>
<body>
<div id="header">Environmental Sampling Locations — QA/QC Validation &amp; Regulatory (MCL) Exceedance Status</div>
<div id="map"></div>
<script>
  const points = {points_json};
  const colors = {json.dumps(color_map)};

  const map = L.map('map').setView([40.78, -74.19], 10);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);

  points.forEach(p => {{
    const color = colors[p.status];
    const marker = L.circleMarker([p.latitude, p.longitude], {{
      radius: 8, fillColor: color, color: '#333', weight: 1, fillOpacity: 0.85
    }}).addTo(map);
    marker.bindPopup(
      `<b>${{p.location_id}}</b><br/>${{p.site_name}}<br/>` +
      `Samples: ${{p.n_samples}}<br/>` +
      `QA/QC Failures: ${{p.n_qaqc_fail}}<br/>` +
      `Regulatory Exceedances: ${{p.n_exceedance}}<br/>` +
      `Status: <b style="color:${{color}}">${{p.status.replace('_',' ').toUpperCase()}}</b>`
    );
  }});

  const legend = L.control({{position: 'bottomright'}});
  legend.onAdd = function() {{
    const div = L.DomUtil.create('div', 'legend');
    div.innerHTML = `
      <b>Location Status</b><br/>
      <span class="dot" style="background:#2ecc71"></span>Pass — within limits<br/>
      <span class="dot" style="background:#f39c12"></span>QA/QC issue flagged<br/>
      <span class="dot" style="background:#e74c3c"></span>Regulatory exceedance
    `;
    return div;
  }};
  legend.addTo(map);
</script>
</body>
</html>
"""

with open(f"{OUT}/gis_sample_locations_map.html", "w") as f:
    f.write(html)

print(f"Map saved with {len(points)} locations.")
print(loc_groups["status"].value_counts())
