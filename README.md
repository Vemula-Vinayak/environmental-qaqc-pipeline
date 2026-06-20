# Environmental Data QA/QC and Regulatory Compliance Validation Pipeline

An end-to-end data validation and regulatory compliance pipeline for environmental
sampling data, built to replicate the data management workflows used in environmental
consulting (lab EDD review, EQuIS-style validation, regulatory comparison, and client
reporting).

**Live API:** deploy via the instructions below (modeled after `recycling-analytics-api.onrender.com`)

## What this project does

Environmental consulting teams routinely receive laboratory analytical data as
Electronic Data Deliverables (EDDs) — e.g., in EarthSoft EQuIS format — that must be
**validated for data quality** and **compared against regulatory criteria** before
they can be loaded into a project database or used in a client deliverable or
regulatory submission. This project builds that workflow end-to-end:

1. **Data ingestion** — a 2,400-record synthetic groundwater/soil sampling dataset
   modeled on real EQuIS EDD structure (sample IDs, lab results, detection limits,
   analytical methods, coordinates, validator initials).
2. **QA/QC validation engine** (`src/validation_engine.py`) — five automated checks:
   - Required-field completeness (sample ID, date, location, analyte)
   - Duplicate sample ID detection
   - Physically-impossible value detection (negative concentrations, impossible pH)
   - **Holding time compliance** — flags any result where the lab analysis date
     exceeds the EPA-standard holding time for that analyte category (14 days for
     VOCs, 180 days for metals, etc.)
   - **Regulatory exceedance** — compares every result against its EPA Maximum
     Contaminant Level (MCL)
3. **Regulatory compliance comparison** — a 12-analyte EPA MCL lookup table and
   automated exceedance-percentage rollup by site and analyte.
4. **GIS mapping** (`src/generate_gis_map.py`) — an interactive Leaflet map of all
   38 monitoring locations, color-coded by QA/QC and exceedance status. Built with
   plain HTML/JS so it requires no ArcGIS license to view or deploy.
5. **Reporting** — a formatted Excel client deliverable
   (`outputs/Environmental_QAQC_Deliverable.xlsx`), four summary figures, and a
   written technical summary (`outputs/technical_summary.md`).
6. **Dashboard** — a self-contained interactive HTML dashboard
   (`outputs/dashboard.html`) summarizing QA/QC and exceedance KPIs (Power-BI-style
   report, viewable without a Power BI license).
7. **Flask API** (`src/app.py`) — exposes the validation summary, exceedance summary,
   filtered record lookup, and a live CSV-upload validation endpoint.

## Project structure

```
envqaqc/
├── data/
│   ├── raw_lab_edd.csv              # synthetic lab EDD (2,400 records)
│   └── epa_mcl_reference.csv        # EPA MCL lookup table (12 analytes)
├── src/
│   ├── generate_data.py             # step 1: data generation
│   ├── validation_engine.py         # step 2: QA/QC + regulatory checks (core)
│   ├── visualizations.py            # step 3: figures
│   ├── generate_gis_map.py          # step 4: interactive map
│   ├── build_excel_deliverable.py   # step 5: Excel client deliverable
│   ├── build_dashboard.py           # step 6: HTML dashboard
│   └── app.py                       # Flask API
├── outputs/                         # all generated deliverables
├── notebooks/
│   └── walkthrough.ipynb            # end-to-end notebook walkthrough
├── requirements.txt
├── Procfile
└── README.md
```

## Running it locally

```bash
pip install -r requirements.txt
python src/generate_data.py
python src/validation_engine.py
python src/visualizations.py
python src/generate_gis_map.py
python src/build_excel_deliverable.py
python src/build_dashboard.py

# Run the API
cd src && python app.py
```

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /` | API info |
| `GET /api/validation-summary` | Pass/fail % by QA/QC check category |
| `GET /api/exceedance-summary?site_id=SITE-01` | Regulatory exceedance % by site/analyte |
| `GET /api/records?status=FAIL&site_id=SITE-01&limit=200` | Filtered record-level results |
| `POST /api/validate` | Upload a CSV EDD (multipart, field `file`) and run it through the engine live |

## Deploying to Render (same pattern as recycling-analytics-api)

1. Push this repo to GitHub.
2. In Render: **New → Web Service** → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app` (Procfile already set, working directory `src/`)
5. Add an environment variable `PYTHON_VERSION=3.11.0` if needed.
6. Deploy — Render will expose a public URL (e.g. `env-qaqc-api.onrender.com`).

## Key concepts demonstrated

`data validation` · `QA/QC` · `regulatory criteria` · `environmental standards` ·
`data quality issues` · `holding time compliance` · `EPA Maximum Contaminant Levels` ·
`EQuIS-style EDD review` · `GIS coordination` · `Excel and Power-BI-style reporting`

