"""
validation_engine.py
Core Environmental Data QA/QC Validation Engine.

Replicates the checks an Environmental Data Analyst runs on lab Electronic
Data Deliverables (EDDs) before they're loaded into EQuIS / used in a
regulatory submission:

  1. Required-field completeness check
  2. Duplicate sample ID check
  3. Physically-impossible value check (negative concentrations, impossible pH)
  4. Holding-time violation check (collection date -> analysis date vs. EPA
     standard holding times by analyte category)
  5. Regulatory exceedance check (result vs. EPA MCL)

Outputs:
  outputs/validated_dataset.csv      -- original data + per-row flags
  outputs/validation_summary.csv     -- pass/fail % by check category
  outputs/exceedance_summary.csv     -- exceedance % by site/analyte
"""

import pandas as pd
import numpy as np

REQUIRED_FIELDS = ["sample_id", "collection_date", "location_id", "analyte"]

# EPA standard holding times by analyte category (days) -- mirrors the
# reference table generated alongside the dataset.
HOLDING_TIMES = {
    "VOC": 14,
    "METAL": 180,
    "WET_CHEM": 2,
    "FIELD": 0,
}


def load_data():
    df = pd.read_csv("/home/claude/envqaqc/data/raw_lab_edd.csv")
    mcl_ref = pd.read_csv("/home/claude/envqaqc/data/epa_mcl_reference.csv")
    return df, mcl_ref


def check_required_fields(df):
    missing_mask = df[REQUIRED_FIELDS].isna().any(axis=1)
    return missing_mask


def check_duplicate_ids(df):
    # A duplicate is only a real QA issue if the sample_id is non-null and repeats
    non_null = df["sample_id"].notna()
    dup_mask = df["sample_id"].duplicated(keep=False) & non_null
    return dup_mask


def check_impossible_values(df):
    impossible = pd.Series(False, index=df.index)
    impossible |= (df["analyte"] != "pH") & (df["result_value"] < 0)
    ph_mask = df["analyte"] == "pH"
    impossible |= ph_mask & ((df["result_value"] < 0) | (df["result_value"] > 14))
    return impossible


def check_holding_time(df):
    coll = pd.to_datetime(df["collection_date"], errors="coerce")
    anal = pd.to_datetime(df["analysis_date"], errors="coerce")
    lag_days = (anal - coll).dt.days
    standard = df["analyte_category"].map(HOLDING_TIMES)
    violation = (lag_days > standard) | lag_days.isna()
    return violation, lag_days


def check_regulatory_exceedance(df):
    mcl = pd.to_numeric(df["regulatory_mcl"], errors="coerce")
    result = pd.to_numeric(df["result_value"], errors="coerce")
    exceeds = (mcl.notna()) & (result > mcl) & (result >= 0)
    return exceeds


def run_validation():
    df, mcl_ref = load_data()

    df["flag_missing_field"] = check_required_fields(df)
    df["flag_duplicate_id"] = check_duplicate_ids(df)
    df["flag_impossible_value"] = check_impossible_values(df)
    holding_violation, lag_days = check_holding_time(df)
    df["holding_time_days"] = lag_days
    df["flag_holding_time_violation"] = holding_violation
    df["flag_regulatory_exceedance"] = check_regulatory_exceedance(df)

    flag_cols = [
        "flag_missing_field", "flag_duplicate_id", "flag_impossible_value",
        "flag_holding_time_violation",
    ]
    df["overall_qaqc_status"] = np.where(
        df[flag_cols].any(axis=1), "FAIL", "PASS"
    )
    df["regulatory_status"] = np.where(
        df["flag_regulatory_exceedance"], "EXCEEDANCE", "WITHIN_LIMIT"
    )

    df.to_csv("/home/claude/envqaqc/outputs/validated_dataset.csv", index=False)

    # --- Validation summary (% pass/fail per check) ---
    total = len(df)
    summary_rows = []
    checks = {
        "Required Field Completeness": "flag_missing_field",
        "Duplicate Sample ID": "flag_duplicate_id",
        "Physically Possible Value Range": "flag_impossible_value",
        "Holding Time Compliance": "flag_holding_time_violation",
        "Regulatory Threshold (MCL) Compliance": "flag_regulatory_exceedance",
    }
    for label, col in checks.items():
        fails = int(df[col].sum())
        passes = total - fails
        summary_rows.append({
            "check_category": label,
            "total_records": total,
            "pass_count": passes,
            "fail_count": fails,
            "pass_rate_pct": round(passes / total * 100, 2),
            "fail_rate_pct": round(fails / total * 100, 2),
        })
    validation_summary = pd.DataFrame(summary_rows)
    validation_summary.to_csv("/home/claude/envqaqc/outputs/validation_summary.csv", index=False)

    # --- Exceedance summary by site / analyte ---
    exceed_df = df[df["regulatory_mcl"].notna() & (df["result_value"] >= 0)].copy()
    grp = exceed_df.groupby(["site_id", "site_name", "analyte"]).agg(
        n_samples=("sample_id", "count"),
        n_exceedances=("flag_regulatory_exceedance", "sum"),
    ).reset_index()
    grp["exceedance_pct"] = round(grp["n_exceedances"] / grp["n_samples"] * 100, 2)
    grp = grp.sort_values("exceedance_pct", ascending=False)
    grp.to_csv("/home/claude/envqaqc/outputs/exceedance_summary.csv", index=False)

    print("=== VALIDATION SUMMARY ===")
    print(validation_summary.to_string(index=False))
    print(f"\nOverall QA/QC pass rate: {(df['overall_qaqc_status']=='PASS').mean()*100:.2f}%")
    print(f"Total regulatory exceedances flagged: {int(df['flag_regulatory_exceedance'].sum())} "
          f"({df['flag_regulatory_exceedance'].mean()*100:.2f}% of comparable samples)")

    return df, validation_summary, grp


if __name__ == "__main__":
    run_validation()
