"""
================================================================================
 CREDIT RISK ANALYSIS - EXPLORATORY DATA ANALYSIS (EDA)
--------------------------------------------------------------------------------
 Project : Credit Card & Loan (Personal / Car / Home) Credit Risk Analysis
 Purpose : Compute risk/eligibility metrics, run portfolio-level analysis,
           and export summary tables + charts (for reports / Power BI / resume).
 Input   : credit_data_cleaned.csv
 Output  : /charts/*.png, portfolio_summary.csv
 Tech    : Python, pandas, numpy, matplotlib, seaborn
================================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set_theme(style="whitegrid")
os.makedirs("charts", exist_ok=True)

df = pd.read_csv("credit_data_cleaned.csv")
print(f"Loaded cleaned dataset: {df.shape[0]} rows, {df.shape[1]} columns")

# ----------------------------------------------------------------------------
# 1. FEATURE ENGINEERING: Risk Score, Risk Category, Eligibility Status
#    (mirrors the logic used in the Excel workbook / SQL view for consistency
#     across all three tools)
# ----------------------------------------------------------------------------
df["debt_to_income_ratio"] = np.where(
    df["Annual Income"] > 0,
    (df["Monthly EMI Outstanding"] * 12) / df["Annual Income"],
    0
)

credit_component = (900 - df["Credit Score"]) / 600 * 100
dti_component = np.minimum(df["debt_to_income_ratio"] * 100, 100)
missed_component = np.minimum(df["Missed Payments (12M)"] * 20, 100)
util_component = df["Credit Utilization (%)"]

df["risk_score"] = (0.4 * credit_component + 0.3 * dti_component
                     + 0.2 * missed_component + 0.1 * util_component).round(1)

df["risk_category"] = pd.cut(
    df["risk_score"], bins=[-1, 30, 60, 1000], labels=["Low", "Medium", "High"]
)


def eligibility(row):
    if (row["Credit Score"] >= 650 and row["debt_to_income_ratio"] <= 0.4
            and row["Missed Payments (12M)"] <= 2 and row["risk_score"] <= 50):
        return "Eligible"
    if (row["Credit Score"] >= 550 and row["Missed Payments (12M)"] <= 4
            and row["risk_score"] <= 75):
        return "Review"
    return "Not Eligible"


df["eligibility_status"] = df.apply(eligibility, axis=1)

# ----------------------------------------------------------------------------
# 2. PORTFOLIO OVERVIEW
# ----------------------------------------------------------------------------
overview = {
    "total_customers": len(df),
    "avg_annual_income": round(df["Annual Income"].mean(), 0),
    "avg_credit_score": round(df["Credit Score"].mean(), 0),
    "avg_dti": round(df["debt_to_income_ratio"].mean(), 4),
    "avg_risk_score": round(df["risk_score"].mean(), 1),
    "eligible_pct": round((df["eligibility_status"] == "Eligible").mean() * 100, 1),
}
print("\nPortfolio Overview:")
for k, v in overview.items():
    print(f"  {k}: {v}")

# ----------------------------------------------------------------------------
# 3. ELIGIBILITY & RISK BREAKDOWNS
# ----------------------------------------------------------------------------
eligibility_counts = df["eligibility_status"].value_counts()
risk_counts = df["risk_category"].value_counts()

print("\nEligibility Breakdown:\n", eligibility_counts)
print("\nRisk Category Breakdown:\n", risk_counts)

# ----------------------------------------------------------------------------
# 4. PRODUCT-LEVEL ANALYSIS
# ----------------------------------------------------------------------------
product_summary = (
    df.groupby("Requested Loan Type")
      .agg(applications=("Customer ID", "count"),
           avg_risk_score=("risk_score", "mean"),
           eligible_rate=("eligibility_status", lambda s: (s == "Eligible").mean() * 100))
      .round(1)
      .sort_values("applications", ascending=False)
)
print("\nProduct-level summary:\n", product_summary)

# ----------------------------------------------------------------------------
# 5. CORRELATION ANALYSIS (numeric risk drivers)
# ----------------------------------------------------------------------------
corr_cols = ["Credit Score", "debt_to_income_ratio", "Missed Payments (12M)",
             "Credit Utilization (%)", "risk_score", "Annual Income"]
corr = df[corr_cols].corr()

# ----------------------------------------------------------------------------
# 6. CHARTS
# ----------------------------------------------------------------------------
# 6a. Risk score distribution
plt.figure(figsize=(8, 5))
sns.histplot(df["risk_score"], bins=30, kde=True, color="#1F4E78")
plt.title("Distribution of Credit Risk Score")
plt.xlabel("Risk Score (0-100, higher = riskier)")
plt.tight_layout()
plt.savefig("charts/risk_score_distribution.png", dpi=150)
plt.close()

# 6b. Eligibility breakdown
plt.figure(figsize=(6, 6))
eligibility_counts.plot.pie(autopct="%1.1f%%",
                             colors=["#70AD47", "#FFC000", "#C00000"])
plt.title("Eligibility Status Distribution")
plt.ylabel("")
plt.tight_layout()
plt.savefig("charts/eligibility_breakdown.png", dpi=150)
plt.close()

# 6c. Risk category by product
plt.figure(figsize=(9, 5))
pd.crosstab(df["Requested Loan Type"], df["risk_category"]).plot(
    kind="bar", stacked=True, ax=plt.gca(),
    color=["#70AD47", "#FFC000", "#C00000"])
plt.title("Risk Category by Requested Product")
plt.ylabel("Number of Customers")
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig("charts/risk_by_product.png", dpi=150)
plt.close()

# 6d. Correlation heatmap
plt.figure(figsize=(7, 6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0)
plt.title("Correlation Between Key Risk Drivers")
plt.tight_layout()
plt.savefig("charts/correlation_heatmap.png", dpi=150)
plt.close()

print("\nCharts saved to ./charts/")

# ----------------------------------------------------------------------------
# 7. EXPORT SUMMARY TABLES
# ----------------------------------------------------------------------------
summary_rows = []
for k, v in overview.items():
    summary_rows.append({"metric": k, "value": v})
pd.DataFrame(summary_rows).to_csv("portfolio_summary.csv", index=False)
product_summary.to_csv("product_summary.csv")

print("\nSummary tables exported: portfolio_summary.csv, product_summary.csv")
