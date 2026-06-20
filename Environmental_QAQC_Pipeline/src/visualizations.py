"""
visualizations.py
Generates the figures used in the technical summary deliverable.
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=0.95)
OUT = "/home/claude/envqaqc/outputs"

df = pd.read_csv(f"{OUT}/validated_dataset.csv")
df["collection_date"] = pd.to_datetime(df["collection_date"])
df["quarter"] = df["collection_date"].dt.to_period("Q").astype(str)

# --- 1. Validation issue breakdown by category ---
flag_cols = {
    "Missing Field": "flag_missing_field",
    "Duplicate ID": "flag_duplicate_id",
    "Impossible Value": "flag_impossible_value",
    "Holding Time Violation": "flag_holding_time_violation",
    "Regulatory Exceedance": "flag_regulatory_exceedance",
}
counts = {label: int(df[col].sum()) for label, col in flag_cols.items()}

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(counts.keys(), counts.values(), color=["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"])
ax.set_title("Data Quality & Compliance Issues by Category", fontsize=13, weight="bold")
ax.set_ylabel("Number of Records Flagged")
plt.xticks(rotation=20, ha="right")
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+5, str(int(b.get_height())), ha="center", fontsize=9)
plt.tight_layout()
plt.savefig(f"{OUT}/fig1_validation_breakdown.png", dpi=150)
plt.close()

# --- 2. Regulatory exceedance trend over time ---
trend = df[df["regulatory_mcl"].notna()].groupby("quarter")["flag_regulatory_exceedance"].mean().reset_index()
trend["exceedance_pct"] = trend["flag_regulatory_exceedance"] * 100

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(trend["quarter"], trend["exceedance_pct"], marker="o", color="#C44E52", linewidth=2)
ax.set_title("Regulatory (MCL) Exceedance Rate by Quarter", fontsize=13, weight="bold")
ax.set_ylabel("% of Samples Exceeding MCL")
ax.set_xlabel("Quarter")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(f"{OUT}/fig2_exceedance_trend.png", dpi=150)
plt.close()

# --- 3. Exceedance by analyte ---
exceed_by_analyte = df[df["regulatory_mcl"].notna()].groupby("analyte")["flag_regulatory_exceedance"].mean().sort_values(ascending=False) * 100

fig, ax = plt.subplots(figsize=(8, 5))
exceed_by_analyte.plot(kind="barh", ax=ax, color="#4C72B0")
ax.set_title("MCL Exceedance Rate by Analyte", fontsize=13, weight="bold")
ax.set_xlabel("% of Samples Exceeding MCL")
ax.invert_yaxis()
plt.tight_layout()
plt.savefig(f"{OUT}/fig3_exceedance_by_analyte.png", dpi=150)
plt.close()

# --- 4. Geographic / site-level exceedance distribution (bar, complements map) ---
site_exceed = df[df["regulatory_mcl"].notna()].groupby("site_name")["flag_regulatory_exceedance"].mean().sort_values(ascending=False) * 100

fig, ax = plt.subplots(figsize=(8, 5))
site_exceed.plot(kind="bar", ax=ax, color="#55A868")
ax.set_title("MCL Exceedance Rate by Site", fontsize=13, weight="bold")
ax.set_ylabel("% of Samples Exceeding MCL")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig(f"{OUT}/fig4_exceedance_by_site.png", dpi=150)
plt.close()

print("Saved 4 figures to outputs/")
