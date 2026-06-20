"""
generate_data.py
Generates a realistic synthetic environmental sampling dataset that mimics
an EarthSoft EQuIS-style Electronic Data Deliverable (EDD): groundwater and
soil analytical results from a multi-site investigation/remediation program.

Output: data/raw_lab_edd.csv
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RNG = np.random.default_rng(42)

N_RECORDS = 2400

# --- Site / location setup -------------------------------------------------
SITES = [
    {"site_id": "SITE-01", "name": "Former Dry Cleaner - Newark", "lat": 40.7357, "lon": -74.1724, "matrix_bias": "GW"},
    {"site_id": "SITE-02", "name": "Industrial Park - Elizabeth", "lat": 40.6639, "lon": -74.2107, "matrix_bias": "SOIL"},
    {"site_id": "SITE-03", "name": "Former Gas Station - Paterson", "lat": 40.9168, "lon": -74.1718, "matrix_bias": "GW"},
    {"site_id": "SITE-04", "name": "Rail Yard - Kearny", "lat": 40.7684, "lon": -74.1454, "matrix_bias": "SOIL"},
    {"site_id": "SITE-05", "name": "Chemical Plant - Linden", "lat": 40.6220, "lon": -74.2446, "matrix_bias": "GW"},
]

# Monitoring wells / borings per site
LOCATIONS = []
for site in SITES:
    n_loc = RNG.integers(6, 11)
    for i in range(n_loc):
        prefix = "MW" if site["matrix_bias"] == "GW" else "SB"
        LOCATIONS.append({
            "site_id": site["site_id"],
            "site_name": site["name"],
            "location_id": f"{prefix}-{site['site_id'][-2:]}-{i+1:02d}",
            "matrix": site["matrix_bias"],
            "latitude": round(site["lat"] + RNG.uniform(-0.01, 0.01), 6),
            "longitude": round(site["lon"] + RNG.uniform(-0.01, 0.01), 6),
        })

# --- Analyte list with EPA MCLs (groundwater) and typical units -----------
# MCL = EPA Maximum Contaminant Level for drinking water (ug/L unless noted)
# Soil values compared against NJDEP/EPA RSL-style screening levels for context only;
# this project focuses validation logic on the GW MCL comparison, which is the
# standard "regulatory exceedance" workflow analysts run in EQuIS.
ANALYTES = {
    "Benzene":               {"unit": "ug/L", "mcl": 5,     "method": "EPA 8260",  "category": "VOC",   "holding_days": 14},
    "Trichloroethylene":     {"unit": "ug/L", "mcl": 5,     "method": "EPA 8260",  "category": "VOC",   "holding_days": 14},
    "Tetrachloroethylene":   {"unit": "ug/L", "mcl": 5,     "method": "EPA 8260",  "category": "VOC",   "holding_days": 14},
    "Vinyl Chloride":        {"unit": "ug/L", "mcl": 2,     "method": "EPA 8260",  "category": "VOC",   "holding_days": 14},
    "1,1-Dichloroethylene":  {"unit": "ug/L", "mcl": 7,     "method": "EPA 8260",  "category": "VOC",   "holding_days": 14},
    "Lead":                  {"unit": "ug/L", "mcl": 15,    "method": "EPA 6020",  "category": "METAL", "holding_days": 180},
    "Arsenic":               {"unit": "ug/L", "mcl": 10,    "method": "EPA 6020",  "category": "METAL", "holding_days": 180},
    "Chromium":              {"unit": "ug/L", "mcl": 100,   "method": "EPA 6020",  "category": "METAL", "holding_days": 180},
    "Cadmium":               {"unit": "ug/L", "mcl": 5,     "method": "EPA 6020",  "category": "METAL", "holding_days": 180},
    "Mercury":               {"unit": "ug/L", "mcl": 2,     "method": "EPA 7470",  "category": "METAL", "holding_days": 28},
    "Nitrate":               {"unit": "mg/L", "mcl": 10,    "method": "EPA 300.0", "category": "WET_CHEM", "holding_days": 2},
    "pH":                    {"unit": "SU",   "mcl": None,  "method": "EPA 9040",  "category": "FIELD", "holding_days": 0},
}

ANALYTE_NAMES = list(ANALYTES.keys())

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 6, 30)


def random_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=int(RNG.integers(0, delta)))


def simulate_concentration(analyte, mcl):
    """Simulate a result that is usually below the MCL, sometimes near it,
    and occasionally exceeds it (realistic right-skewed contaminant distribution)."""
    if analyte == "pH":
        return round(RNG.normal(7.0, 0.8), 2)
    if mcl is None:
        mcl = 10
    roll = RNG.random()
    if roll < 0.55:
        val = RNG.uniform(0, mcl * 0.3)        # clean
    elif roll < 0.80:
        val = RNG.uniform(mcl * 0.3, mcl * 0.9)  # detected, below MCL
    elif roll < 0.93:
        val = RNG.uniform(mcl * 0.9, mcl * 2.5)  # exceedance
    else:
        val = RNG.uniform(mcl * 2.5, mcl * 12)   # major exceedance
    return round(val, 3)


rows = []
sample_counter = 1

for _ in range(N_RECORDS):
    loc = LOCATIONS[RNG.integers(0, len(LOCATIONS))]
    analyte_name = ANALYTE_NAMES[RNG.integers(0, len(ANALYTE_NAMES))]
    a = ANALYTES[analyte_name]

    collection_date = random_date(START_DATE, END_DATE)

    # Holding time: usually compliant, sometimes blown (lab/logistics delay)
    if RNG.random() < 0.08:
        lag_days = a["holding_days"] + RNG.integers(1, 20)  # violation
    else:
        max_lag = max(a["holding_days"] - 1, 1)
        lag_days = RNG.integers(0, max_lag + 1)
    analysis_date = collection_date + timedelta(days=int(lag_days))

    detection_limit = round(a.get("mcl", 1) * 0.05, 4) if a.get("mcl") else 0.01
    result = simulate_concentration(analyte_name, a["mcl"])

    # Detect/non-detect flag
    is_nondetect = analyte_name != "pH" and result < detection_limit and RNG.random() < 0.5
    qualifier = "U" if is_nondetect else ""

    sample_id = f"{loc['location_id']}-{collection_date.strftime('%Y%m%d')}-{sample_counter:05d}"
    sample_counter += 1

    rows.append({
        "sample_id": sample_id,
        "site_id": loc["site_id"],
        "site_name": loc["site_name"],
        "location_id": loc["location_id"],
        "matrix": loc["matrix"],
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "collection_date": collection_date.strftime("%Y-%m-%d"),
        "analysis_date": analysis_date.strftime("%Y-%m-%d"),
        "analyte": analyte_name,
        "analytical_method": a["method"],
        "analyte_category": a["category"],
        "result_value": result,
        "result_unit": a["unit"],
        "detection_limit": detection_limit,
        "qualifier": qualifier,
        "regulatory_mcl": a["mcl"] if a["mcl"] is not None else "",
        "lab_name": RNG.choice(["Pace Analytical", "Eurofins TestAmerica", "ALS Environmental"]),
        "validator_initials": RNG.choice(["JM", "KP", "RS", "TL"]),
    })

df = pd.DataFrame(rows)

# --- Inject realistic data-quality defects for the QA/QC engine to catch ---
n = len(df)

# 1. Missing required fields (~2%)
for col in ["sample_id", "collection_date", "location_id", "analyte"]:
    idx = RNG.choice(n, size=max(1, int(n * 0.005)), replace=False)
    df.loc[idx, col] = np.where(df.loc[idx, col].notna(), None, None)
    df.loc[idx, col] = None

# 2. Duplicate sample IDs (~1%)
dup_idx = RNG.choice(n, size=int(n * 0.01), replace=False)
for i in dup_idx:
    target = RNG.integers(0, n)
    df.loc[i, "sample_id"] = df.loc[target, "sample_id"]

# 3. Impossible values: negative concentrations, impossible pH (~1.5%)
neg_idx = RNG.choice(df[df["analyte"] != "pH"].index, size=int(n * 0.01), replace=False)
df.loc[neg_idx, "result_value"] = -abs(df.loc[neg_idx, "result_value"])

ph_idx = df[df["analyte"] == "pH"].sample(frac=0.1, random_state=1).index
df.loc[ph_idx, "result_value"] = RNG.choice([-1.0, 15.5, 22.0], size=len(ph_idx))

df.to_csv("/home/claude/envqaqc/data/raw_lab_edd.csv", index=False)

# Save analyte/MCL reference table separately too
mcl_df = pd.DataFrame([
    {"analyte": k, "unit": v["unit"], "epa_mcl": v["mcl"], "method": v["method"],
     "category": v["category"], "standard_holding_time_days": v["holding_days"]}
    for k, v in ANALYTES.items()
])
mcl_df.to_csv("/home/claude/envqaqc/data/epa_mcl_reference.csv", index=False)

print(f"Generated {len(df)} records across {len(SITES)} sites / {len(LOCATIONS)} locations.")
print(df.head(3).to_string())
