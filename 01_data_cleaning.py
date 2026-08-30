"""
================================================================================
 CREDIT RISK DATA CLEANING PIPELINE
--------------------------------------------------------------------------------
 Project : Credit Card & Loan (Personal / Car / Home) Credit Risk Analysis
 Purpose : Clean a raw, messy customer dataset (missing values, inconsistent
           formats, duplicates, invalid contact info, mixed date formats,
           outliers) into an analysis-ready dataset.
 Input   : credit_data_unclean.csv
 Output  : credit_data_cleaned.csv  +  data_cleaning_log.txt (audit trail)

 Author  : <Your Name>
 Tech    : Python, pandas, numpy, re
================================================================================
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime

INPUT_FILE = "credit_data_unclean.csv"
OUTPUT_FILE = "credit_data_cleaned.csv"
LOG_FILE = "data_cleaning_log.txt"

log_lines = []


def log(msg):
    print(msg)
    log_lines.append(msg)


# --------------------------------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------------------------------
df = pd.read_csv(INPUT_FILE, dtype=str)  # read everything as string first; we'll cast explicitly
log(f"[1] Loaded raw file: {df.shape[0]} rows, {df.shape[1]} columns")

# --------------------------------------------------------------------------
# 2. DROP FULLY BLANK ROWS
# --------------------------------------------------------------------------
before = len(df)
df = df.dropna(how="all")
df = df[~(df.apply(lambda r: r.astype(str).str.strip().eq("").all(), axis=1))]
log(f"[2] Dropped fully blank rows: {before - len(df)} removed")

# --------------------------------------------------------------------------
# 3. TRIM WHITESPACE ON ALL TEXT COLUMNS
# --------------------------------------------------------------------------
for col in df.columns:
    df[col] = df[col].astype(str).str.strip()
    df[col] = df[col].replace({"nan": np.nan, "": np.nan, "N/A": np.nan, "NA": np.nan})
log("[3] Trimmed whitespace and normalized blank/NA markers to NaN")

# --------------------------------------------------------------------------
# 4. REMOVE DUPLICATE RECORDS
#    (Same Customer ID -> keep first occurrence; also drop fully duplicated rows)
# --------------------------------------------------------------------------
before = len(df)
df = df.drop_duplicates()
dup_full = before - len(df)

before = len(df)
df = df.drop_duplicates(subset=["Customer ID"], keep="first")
dup_id = before - len(df)
log(f"[4] Removed {dup_full} exact-duplicate rows and {dup_id} duplicate Customer IDs")

# Drop rows with no Customer ID at all (cannot be reliably matched/tracked)
before = len(df)
df = df[df["Customer ID"].notna()]
log(f"[4b] Dropped rows with missing Customer ID: {before - len(df)} removed")

# --------------------------------------------------------------------------
# 5. STANDARDIZE CATEGORICAL / TEXT FIELDS
# --------------------------------------------------------------------------


def clean_title(s):
    if pd.isna(s):
        return s
    return " ".join(str(s).split()).title()


def clean_upper(s):
    if pd.isna(s):
        return s
    return " ".join(str(s).split()).upper()


df["Full Name"] = df["Full Name"].apply(clean_title)
df["City"] = df["City"].apply(clean_title)
df["Occupation"] = df["Occupation"].apply(clean_title)
df["Requested Loan Type"] = df["Requested Loan Type"].apply(clean_title)
df["Residence Type"] = df["Residence Type"].apply(clean_title)

# Gender: normalize M/F/Male/Female variants
gender_map = {"M": "Male", "F": "Female", "MALE": "Male", "FEMALE": "Female",
              "Male": "Male", "Female": "Female"}
df["Gender"] = df["Gender"].apply(lambda x: gender_map.get(str(x).strip().upper(), x))

# Marital status casing
df["Marital Status"] = df["Marital Status"].apply(clean_title)

# KYC status casing
df["KYC Status"] = df["KYC Status"].apply(clean_title)

# City typo/alias normalization
city_alias = {
    "Bangalore": "Bengaluru", "Banglore": "Bengaluru",
    "Bombay": "Mumbai", "Calcutta": "Kolkata", "New Delhi": "Delhi",
}
df["City"] = df["City"].replace(city_alias)

log("[5] Standardized text casing for names, city, occupation, gender, "
    "marital status, KYC status; normalized city name aliases/typos")

# --------------------------------------------------------------------------
# 6. STANDARDIZE YES/NO FLAG COLUMNS
# --------------------------------------------------------------------------
flag_cols = ["Has Credit Card", "Has Personal Loan", "Has Car Loan", "Has Home Loan",
             "Previous Default History"]

yes_set = {"Y", "YES", "1", "TRUE"}
no_set = {"N", "NO", "0", "FALSE"}


def normalize_flag(v):
    if pd.isna(v):
        return np.nan
    v_up = str(v).strip().upper()
    if v_up in yes_set:
        return "Y"
    if v_up in no_set:
        return "N"
    return np.nan  # unrecognized -> treat as missing, flagged for review


for col in flag_cols:
    df[col] = df[col].apply(normalize_flag)
log(f"[6] Standardized {len(flag_cols)} Yes/No flag columns to consistent 'Y'/'N' values")

# --------------------------------------------------------------------------
# 7. CLEAN NUMERIC / CURRENCY COLUMNS
#    (strip currency symbols, commas; coerce to numeric; fix invalid negatives)
# --------------------------------------------------------------------------
currency_cols = ["Annual Income", "Existing Outstanding Debt", "Monthly EMI Outstanding",
                  "Requested Amount", "Co-Applicant Income", "Collateral Value"]


def clean_currency(v):
    if pd.isna(v):
        return np.nan
    s = re.sub(r"[₹,\s]", "", str(v))
    try:
        val = float(s)
    except ValueError:
        return np.nan
    return abs(val)  # negative currency values are data-entry errors here


for col in currency_cols:
    df[col] = df[col].apply(clean_currency)

plain_numeric_cols = ["Existing Products Count", "Credit Score", "Missed Payments (12M)",
                       "Credit Utilization (%)", "Years with Bank", "Number of Dependents",
                       "Employment Tenure (Years)", "Existing Loans (Other Banks)",
                       "Requested Tenure (Months)"]
for col in plain_numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

log(f"[7] Cleaned {len(currency_cols)} currency columns (stripped symbols/commas, "
    f"fixed negatives) and coerced {len(plain_numeric_cols)} numeric columns")

# --------------------------------------------------------------------------
# 8. CLEAN & VALIDATE AGE
# --------------------------------------------------------------------------
df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
invalid_age_mask = ~df["Age"].between(18, 100)
n_invalid_age = invalid_age_mask.sum()
df.loc[invalid_age_mask, "Age"] = np.nan
log(f"[8] Flagged {n_invalid_age} out-of-range ages (<18 or >100) as missing")

# --------------------------------------------------------------------------
# 9. CLEAN PHONE NUMBERS -> STANDARD 10-DIGIT FORMAT
# --------------------------------------------------------------------------


def clean_phone(v):
    if pd.isna(v):
        return np.nan
    digits = re.sub(r"\D", "", str(v))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return digits
    return np.nan  # invalid / unrecoverable phone number


df["Phone Number"] = df["Phone Number"].apply(clean_phone)
n_invalid_phone = df["Phone Number"].isna().sum()
log(f"[9] Standardized phone numbers to 10-digit format; {n_invalid_phone} invalid/missing")

# --------------------------------------------------------------------------
# 10. VALIDATE EMAIL ADDRESSES
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_email(v):
    if pd.isna(v):
        return np.nan
    e = str(v).strip().lower().replace(" at ", "@").replace(",com", ".com")
    e = e.replace(" ", "")
    return e if EMAIL_RE.match(e) else np.nan


df["Email ID"] = df["Email ID"].apply(clean_email)
n_invalid_email = df["Email ID"].isna().sum()
log(f"[10] Validated email format; {n_invalid_email} invalid/missing after cleaning")

# --------------------------------------------------------------------------
# 11. PARSE MIXED-FORMAT DATES
# --------------------------------------------------------------------------
DATE_FORMATS = ["%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%d %b %Y", "%Y-%m-%d"]


def parse_date(v):
    if pd.isna(v):
        return pd.NaT
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(v).strip(), fmt)
        except ValueError:
            continue
    return pd.NaT


df["Application Date"] = df["Application Date"].apply(parse_date)
n_invalid_date = df["Application Date"].isna().sum()
log(f"[11] Parsed 5 mixed date formats into a single standard datetime; "
    f"{n_invalid_date} unparseable/missing")

# --------------------------------------------------------------------------
# 12. IMPUTE / HANDLE REMAINING MISSING VALUES
# --------------------------------------------------------------------------
# Numeric: median imputation (robust to outliers) for core underwriting fields
median_impute_cols = ["Annual Income", "Credit Score", "Age", "Credit Utilization (%)",
                       "Years with Bank", "Employment Tenure (Years)"]
for col in median_impute_cols:
    med = df[col].median()
    n_missing = df[col].isna().sum()
    df[col] = df[col].fillna(med)
    if n_missing:
        log(f"[12] Imputed {n_missing} missing '{col}' values with median ({med:.1f})")

# Co-applicant income / collateral value: missing genuinely means "None" -> 0
df["Co-Applicant Income"] = df["Co-Applicant Income"].fillna(0)
df["Collateral Value"] = df["Collateral Value"].fillna(0)

# Flag columns: unresolved Y/N -> default to "N" (conservative assumption) and log count
for col in flag_cols:
    n_missing = df[col].isna().sum()
    df[col] = df[col].fillna("N")
    if n_missing:
        log(f"[12] Defaulted {n_missing} missing '{col}' values to 'N'")

# --------------------------------------------------------------------------
# 13. FINAL TYPE CASTING
# --------------------------------------------------------------------------
int_cols = ["Existing Products Count", "Credit Score", "Missed Payments (12M)",
            "Number of Dependents", "Existing Loans (Other Banks)", "Requested Tenure (Months)"]
for col in int_cols:
    df[col] = df[col].round(0).astype("Int64")

df["Application Date"] = df["Application Date"].dt.strftime("%Y-%m-%d")

# --------------------------------------------------------------------------
# 14. DROP ROWS THAT ARE STILL UNUSABLE (no email AND no phone AND no income)
# --------------------------------------------------------------------------
before = len(df)
unusable = df["Email ID"].isna() & df["Phone Number"].isna() & df["Annual Income"].isna()
df = df[~unusable]
log(f"[14] Dropped {before - len(df)} rows unusable due to missing all contact/income info")

# --------------------------------------------------------------------------
# 15. SAVE CLEANED OUTPUT
# --------------------------------------------------------------------------
df = df.reset_index(drop=True)
df.to_csv(OUTPUT_FILE, index=False)
log(f"[15] Saved cleaned dataset: {df.shape[0]} rows, {df.shape[1]} columns -> {OUTPUT_FILE}")

with open(LOG_FILE, "w") as f:
    f.write("\n".join(log_lines))

log(f"\nCleaning complete. Audit log written to {LOG_FILE}")
