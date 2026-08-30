# Credit Risk Analysis — End-to-End Portfolio Project

A complete data analytics project across **Excel, SQL, Python, and Power BI**,
built on a synthetic 1,000-customer dataset covering credit card, personal
loan, car loan, and home loan applications.

## Dashboard & Charts

**Excel Summary Dashboard**

![Excel Dashboard](screenshots/excel_dashboard_screenshot.png)

**Python EDA — Risk Score Distribution & Eligibility Breakdown**

<img src="screenshots/risk_score_distribution.png" width="49%"> <img src="screenshots/eligibility_breakdown.png" width="49%">

**Python EDA — Risk by Product & Correlation Heatmap**

<img src="screenshots/risk_by_product.png" width="49%"> <img src="screenshots/correlation_heatmap.png" width="49%">

## Project Structure

| File | Tool | Purpose |
|---|---|---|
| `credit_risk_report.xlsx` | Excel | Full workbook: Summary Dashboard, cleaned Customer Data (45 columns, live formulas), and a Raw Data (Unclean) sheet |
| `credit_data_unclean.csv` | — | Raw source data with intentional data-quality issues |
| `01_data_cleaning.py` | Python | Cleans the raw CSV: dedup, standardization, validation, imputation, audit log |
| `credit_data_cleaned.csv` | — | Output of the cleaning script — analysis-ready dataset |
| `02_sql_analysis.sql` | SQL | Schema, risk/eligibility view, and 10 analytical queries (KPIs, segmentation, window functions, cross-sell) |
| `03_python_eda_analysis.py` | Python | EDA on cleaned data: risk scoring, correlation analysis, 4 charts, summary exports |
| `04_powerbi_dax_measures.txt` | Power BI | DAX calculated columns and measures for a risk dashboard |
| `05_powerbi_powerquery_m.txt` | Power BI | Power Query M script replicating the cleaning steps natively in Power BI |
| `screenshots/` | — | Dashboard and chart images embedded above (regenerate anytime via `03_python_eda_analysis.py`) |

## Workflow

```
credit_data_unclean.csv
        │
        ▼ (01_data_cleaning.py — Python)
credit_data_cleaned.csv
        │
        ├──▶ 02_sql_analysis.sql        (load into a database, run analysis)
        ├──▶ 03_python_eda_analysis.py  (EDA, charts, correlation)
        └──▶ Power BI (05 → 04)         (Power Query transform → DAX model → dashboard)
```

The Excel workbook (`credit_risk_report.xlsx`) is a standalone deliverable
that mirrors the same risk-scoring logic (Debt-to-Income Ratio, Risk Score,
Risk Category, Eligibility Status) using native Excel formulas, so the
underwriting logic is consistent whether it's implemented in Excel, SQL,
Python, or DAX — a good talking point in an interview.

## Key Business Logic (identical across all four tools)

- **Debt-to-Income Ratio** = (Monthly EMI × 12) / Annual Income
- **Risk Score (0–100)** = 40% credit-score component + 30% DTI component +
  20% missed-payments component + 10% credit-utilization component
- **Risk Category**: Low (≤30), Medium (31–60), High (>60)
- **Eligibility Status**: Eligible / Review / Not Eligible, based on credit
  score, DTI, missed payments, and risk score thresholds

*(All customer data is synthetic and generated for demonstration purposes.
Thresholds are illustrative sample underwriting rules, not a real bank's
credit policy.)*

## Highlights

- Reduced manual credit risk assessment effort by building an automated multi-factor
  scoring model (credit score, DTI, payment history, utilization) applied consistently
  across 1,000+ applicant records.
- Identified 325 eligible, 212 borderline, and 463 high-risk applicants out of 1,000
  through a rules-based eligibility engine, enabling faster underwriting triage.
- Enabled data-driven credit decisions by translating raw applicant data into clear,
  actionable eligibility categories (Eligible / Review / Not Eligible) — reducing
  reliance on manual judgment and giving underwriting teams a consistent, repeatable
  basis for approval decisions.

## How to Run

```bash
pip install pandas numpy matplotlib seaborn
python 01_data_cleaning.py        # produces credit_data_cleaned.csv
python 03_python_eda_analysis.py  # produces charts/ and summary CSVs
```

For SQL: load `credit_data_cleaned.csv` into your database of choice and run
`02_sql_analysis.sql` (written for PostgreSQL/SQL Server; minor syntax
tweaks needed for MySQL).

For Power BI: open Power BI Desktop → Get Data → Blank Query → Advanced
Editor → paste `05_powerbi_powerquery_m.txt` (update the file path) → then
add the DAX from `04_powerbi_dax_measures.txt` in Model view.
