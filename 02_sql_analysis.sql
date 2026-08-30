/* ============================================================================
   CREDIT RISK ANALYSIS - SQL SCRIPT
   ----------------------------------------------------------------------------
   Project : Credit Card & Loan (Personal / Car / Home) Credit Risk Analysis
   Purpose : Schema definition + analytical queries on the cleaned customer
             dataset (credit_data_cleaned.csv loaded into `customers` table).
   Dialect : Written for PostgreSQL / SQL Server (T-SQL notes marked inline).
             Minor tweaks needed for MySQL (e.g. no FILTER clause -> use CASE).
   ============================================================================ */

-- ----------------------------------------------------------------------------
-- 1. SCHEMA
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id            VARCHAR(15) PRIMARY KEY,
    full_name               VARCHAR(100),
    phone_number             VARCHAR(15),
    email_id                 VARCHAR(100),
    age                       INT,
    gender                    VARCHAR(10),
    city                      VARCHAR(50),
    occupation                VARCHAR(50),
    employment_type            VARCHAR(20),
    annual_income               NUMERIC(14,2),
    existing_products_count      INT,
    has_credit_card               CHAR(1),
    has_personal_loan             CHAR(1),
    has_car_loan                  CHAR(1),
    has_home_loan                 CHAR(1),
    credit_score                  INT,
    existing_outstanding_debt     NUMERIC(14,2),
    monthly_emi_outstanding       NUMERIC(14,2),
    requested_loan_type           VARCHAR(20),
    requested_amount               NUMERIC(14,2),
    missed_payments_12m            INT,
    credit_utilization_pct          NUMERIC(5,2),
    years_with_bank                  NUMERIC(5,2),
    marital_status                    VARCHAR(15),
    number_of_dependents               INT,
    residence_type                      VARCHAR(20),
    employment_tenure_years              NUMERIC(5,2),
    coapplicant_income                    NUMERIC(14,2),
    existing_loans_other_banks             INT,
    previous_default_history                CHAR(1),
    requested_tenure_months                  INT,
    collateral_value                          NUMERIC(14,2),
    application_date                           DATE,
    kyc_status                                  VARCHAR(15)
);

-- Load with (PostgreSQL example):
-- \COPY customers FROM 'credit_data_cleaned.csv' WITH (FORMAT csv, HEADER true);

-- ----------------------------------------------------------------------------
-- 2. DERIVED VIEW: RISK & ELIGIBILITY (mirrors Excel formula logic)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW customer_risk AS
SELECT
    c.*,
    CASE WHEN annual_income > 0
         THEN ROUND((monthly_emi_outstanding * 12) / annual_income, 4)
         ELSE 0 END                                            AS debt_to_income_ratio,
    ROUND(
        0.4 * ((900 - credit_score) / 600.0 * 100)
      + 0.3 * LEAST(
            CASE WHEN annual_income > 0
                 THEN (monthly_emi_outstanding * 12) / annual_income * 100
                 ELSE 0 END, 100)
      + 0.2 * LEAST(missed_payments_12m * 20, 100)
      + 0.1 * credit_utilization_pct
    , 1)                                                        AS risk_score
FROM customers c;

CREATE OR REPLACE VIEW customer_risk_scored AS
SELECT
    *,
    CASE
        WHEN risk_score <= 30 THEN 'Low'
        WHEN risk_score <= 60 THEN 'Medium'
        ELSE 'High'
    END AS risk_category,
    CASE
        WHEN credit_score >= 650 AND debt_to_income_ratio <= 0.4
             AND missed_payments_12m <= 2 AND risk_score <= 50 THEN 'Eligible'
        WHEN credit_score >= 550 AND missed_payments_12m <= 4
             AND risk_score <= 75 THEN 'Review'
        ELSE 'Not Eligible'
    END AS eligibility_status
FROM customer_risk;

-- ----------------------------------------------------------------------------
-- 3. PORTFOLIO OVERVIEW KPIs
-- ----------------------------------------------------------------------------
SELECT
    COUNT(*)                                   AS total_customers,
    ROUND(AVG(annual_income), 0)                AS avg_annual_income,
    ROUND(AVG(credit_score), 0)                  AS avg_credit_score,
    ROUND(AVG(debt_to_income_ratio), 4)           AS avg_dti,
    ROUND(AVG(risk_score), 1)                      AS avg_risk_score,
    ROUND(AVG(existing_products_count), 2)          AS avg_products_per_customer
FROM customer_risk_scored;

-- ----------------------------------------------------------------------------
-- 4. ELIGIBILITY BREAKDOWN (count + % of portfolio)
-- ----------------------------------------------------------------------------
SELECT
    eligibility_status,
    COUNT(*)                                            AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS pct_of_portfolio
FROM customer_risk_scored
GROUP BY eligibility_status
ORDER BY customer_count DESC;

-- ----------------------------------------------------------------------------
-- 5. RISK CATEGORY BY REQUESTED PRODUCT (cross-tab style)
-- ----------------------------------------------------------------------------
SELECT
    requested_loan_type,
    COUNT(*)                                                          AS applications,
    SUM(CASE WHEN risk_category = 'Low'    THEN 1 ELSE 0 END)          AS low_risk,
    SUM(CASE WHEN risk_category = 'Medium' THEN 1 ELSE 0 END)          AS medium_risk,
    SUM(CASE WHEN risk_category = 'High'   THEN 1 ELSE 0 END)          AS high_risk,
    SUM(CASE WHEN eligibility_status = 'Eligible' THEN 1 ELSE 0 END)    AS eligible_count,
    ROUND(100.0 * SUM(CASE WHEN eligibility_status = 'Eligible' THEN 1 ELSE 0 END)
          / COUNT(*), 1)                                                 AS eligible_rate_pct
FROM customer_risk_scored
GROUP BY requested_loan_type
ORDER BY applications DESC;

-- ----------------------------------------------------------------------------
-- 6. CITY-WISE RISK PROFILE (identify high-risk geographies)
-- ----------------------------------------------------------------------------
SELECT
    city,
    COUNT(*)                             AS customers,
    ROUND(AVG(risk_score), 1)             AS avg_risk_score,
    ROUND(AVG(credit_score), 0)            AS avg_credit_score,
    SUM(CASE WHEN eligibility_status = 'Not Eligible' THEN 1 ELSE 0 END) AS not_eligible_count
FROM customer_risk_scored
GROUP BY city
HAVING COUNT(*) >= 10
ORDER BY avg_risk_score DESC;

-- ----------------------------------------------------------------------------
-- 7. HIGH-RISK, HIGH-EXPOSURE CUSTOMERS (priority review list)
-- ----------------------------------------------------------------------------
SELECT
    customer_id, full_name, credit_score, risk_score, risk_category,
    debt_to_income_ratio, requested_loan_type, requested_amount, eligibility_status
FROM customer_risk_scored
WHERE risk_category = 'High'
ORDER BY requested_amount DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- 8. WINDOW FUNCTION: RANK CUSTOMERS BY RISK SCORE WITHIN EACH CITY
-- ----------------------------------------------------------------------------
SELECT
    customer_id, full_name, city, risk_score,
    RANK() OVER (PARTITION BY city ORDER BY risk_score DESC) AS risk_rank_in_city
FROM customer_risk_scored
QUALIFY risk_rank_in_city <= 3          -- Snowflake/Databricks syntax
-- For PostgreSQL/SQL Server, wrap in a CTE and filter WHERE risk_rank_in_city <= 3 instead
ORDER BY city, risk_rank_in_city;

-- ----------------------------------------------------------------------------
-- 9. EXISTING PRODUCT CROSS-SELL OPPORTUNITY
--    (Eligible customers who don't yet hold a given product with the bank)
-- ----------------------------------------------------------------------------
SELECT
    'Credit Card' AS product, COUNT(*) AS cross_sell_opportunity
FROM customer_risk_scored
WHERE has_credit_card = 'N' AND eligibility_status = 'Eligible'
UNION ALL
SELECT 'Personal Loan', COUNT(*)
FROM customer_risk_scored
WHERE has_personal_loan = 'N' AND eligibility_status = 'Eligible'
UNION ALL
SELECT 'Car Loan', COUNT(*)
FROM customer_risk_scored
WHERE has_car_loan = 'N' AND eligibility_status = 'Eligible'
UNION ALL
SELECT 'Home Loan', COUNT(*)
FROM customer_risk_scored
WHERE has_home_loan = 'N' AND eligibility_status = 'Eligible';

-- ----------------------------------------------------------------------------
-- 10. MONTHLY APPLICATION TREND (for a Power BI / Excel time-series chart)
-- ----------------------------------------------------------------------------
SELECT
    DATE_TRUNC('month', application_date)          AS application_month,   -- SQL Server: FORMAT(application_date,'yyyy-MM')
    COUNT(*)                                          AS applications,
    SUM(CASE WHEN eligibility_status = 'Eligible' THEN 1 ELSE 0 END) AS eligible_applications
FROM customer_risk_scored
WHERE application_date IS NOT NULL
GROUP BY 1
ORDER BY 1;
