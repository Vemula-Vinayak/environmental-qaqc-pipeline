"""
app.py
Flask API for the Environmental Data QA/QC & Regulatory Compliance Validation
Pipeline. Mirrors the structure of the existing recycling-analytics-api
project: a thin Flask layer over a pandas-based analytics/validation engine,
deployable as-is to Render.

Endpoints:
  GET  /                       -> health check / API info
  GET  /api/validation-summary -> pass/fail % by QA/QC check category
  GET  /api/exceedance-summary -> regulatory exceedance % by site/analyte
  GET  /api/records?status=FAIL&site_id=SITE-01  -> filtered record-level results
  POST /api/validate           -> upload a CSV EDD and run it through the engine live
"""
import os
import io
from flask import Flask, jsonify, request, send_from_directory
import pandas as pd

from validation_engine import run_validation, REQUIRED_FIELDS, HOLDING_TIMES, check_required_fields, \
    check_duplicate_ids, check_impossible_values, check_holding_time, check_regulatory_exceedance

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "validated_dataset.csv")
SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "validation_summary.csv")
EXCEEDANCE_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "exceedance_summary.csv")


@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "dashboard.html")


@app.route("/api")
def api_info():
    return jsonify({
        "service": "Environmental Data QA/QC & Regulatory Compliance Validation API",
        "endpoints": [
            "/api/validation-summary",
            "/api/exceedance-summary",
            "/api/records?status=FAIL&site_id=SITE-01",
            "POST /api/validate (multipart CSV upload, EDD-style columns)",
        ],
        "description": (
            "Runs environmental sampling data through an automated QA/QC pipeline: "
            "required-field checks, duplicate sample ID detection, physically-impossible "
            "value checks, EPA holding-time compliance, and EPA MCL regulatory exceedance comparison."
        ),
    })


@app.route("/api/validation-summary")
def validation_summary():
    df = pd.read_csv(SUMMARY_PATH)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/exceedance-summary")
def exceedance_summary():
    df = pd.read_csv(EXCEEDANCE_PATH)
    site_id = request.args.get("site_id")
    if site_id:
        df = df[df["site_id"] == site_id]
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/records")
def records():
    df = pd.read_csv(DATA_PATH)
    status = request.args.get("status")
    site_id = request.args.get("site_id")
    analyte = request.args.get("analyte")
    if status:
        df = df[df["overall_qaqc_status"] == status.upper()]
    if site_id:
        df = df[df["site_id"] == site_id]
    if analyte:
        df = df[df["analyte"].str.lower() == analyte.lower()]
    limit = int(request.args.get("limit", 200))
    return jsonify(df.head(limit).to_dict(orient="records"))


@app.route("/api/validate", methods=["POST"])
def validate_upload():
    """Run an uploaded EDD-style CSV through the same validation logic live."""
    if "file" not in request.files:
        return jsonify({"error": "Upload a CSV file under form field 'file'"}), 400
    file = request.files["file"]
    try:
        df = pd.read_csv(io.BytesIO(file.read()))
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400

    required_present = [c for c in REQUIRED_FIELDS if c in df.columns]
    if len(required_present) < len(REQUIRED_FIELDS):
        missing_cols = set(REQUIRED_FIELDS) - set(required_present)
        return jsonify({"error": f"Uploaded file missing required columns: {sorted(missing_cols)}"}), 400

    df["flag_missing_field"] = check_required_fields(df)
    df["flag_duplicate_id"] = check_duplicate_ids(df)
    if "result_value" in df.columns and "analyte" in df.columns:
        df["flag_impossible_value"] = check_impossible_values(df)
    if {"collection_date", "analysis_date", "analyte_category"}.issubset(df.columns):
        violation, lag = check_holding_time(df)
        df["flag_holding_time_violation"] = violation
        df["holding_time_days"] = lag
    if {"result_value", "regulatory_mcl"}.issubset(df.columns):
        df["flag_regulatory_exceedance"] = check_regulatory_exceedance(df)

    flag_cols = [c for c in df.columns if c.startswith("flag_")]
    df["overall_qaqc_status"] = "PASS"
    if flag_cols:
        df.loc[df[flag_cols].any(axis=1), "overall_qaqc_status"] = "FAIL"

    summary = {
        "total_records": len(df),
        "pass_count": int((df["overall_qaqc_status"] == "PASS").sum()),
        "fail_count": int((df["overall_qaqc_status"] == "FAIL").sum()),
        "flags_detected": {c: int(df[c].sum()) for c in flag_cols},
    }
    return jsonify({"summary": summary, "records": df.head(50).to_dict(orient="records")})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
