# Data Model: Customer Churn Prediction

**Feature**: 001-churn-prediction-model  
**Date**: 2026-02-09

## Entity Relationship Overview

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│  Customer   │──────<│ Customer_Activity │       │   Policy    │
└─────────────┘       └──────────────────┘       └─────────────┘
       │                                                │
       │              ┌──────────────────┐              │
       └─────────────>│   Churn_Event    │              │
       │              └──────────────────┘              │
       │                                                │
       │              ┌──────────────────┐              │
       └─────────────>│    Prediction    │              │
       │              └──────────────────┘              │
       │                                                │
       │              ┌──────────────────┐              │
       └─────────────>│  Policy_Cohort   │<─────────────┘
                      └──────────────────┘
```

## Tables

### 1. customers

Master customer dimension table.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| customer_id | STRING | Unique customer identifier | PK, NOT NULL |
| customer_name | STRING | Customer display name | |
| account_type | STRING | Customer segment (Enterprise, SMB, Consumer) | |
| industry | STRING | Industry classification | |
| region | STRING | Geographic region | |
| tenure_months | INT | Months since first purchase | ≥0 |
| contract_type | STRING | Monthly, Annual, Multi-year | |
| contract_start_date | DATE | Current contract start | |
| contract_end_date | DATE | Current contract end | |
| total_revenue_ltv | DECIMAL(12,2) | Lifetime revenue | |
| assigned_rep_id | STRING | Customer success rep ID | |
| created_at | TIMESTAMP | Record creation | NOT NULL |
| updated_at | TIMESTAMP | Last update | NOT NULL |

### 2. customer_activity

Customer interaction and usage events for inactivity calculation.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| activity_id | STRING | Unique activity identifier | PK, NOT NULL |
| customer_id | STRING | Reference to customer | FK, NOT NULL |
| activity_date | DATE | Date of activity | NOT NULL |
| activity_type | STRING | Login, Purchase, Support, Usage | NOT NULL |
| activity_value | DECIMAL(12,2) | Monetary value if applicable | |
| channel | STRING | Web, Mobile, API, Phone | |
| created_at | TIMESTAMP | Record creation | NOT NULL |

**Index**: customer_id, activity_date DESC

### 3. churn_events

Historical churn records for training labels.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| churn_event_id | STRING | Unique event identifier | PK, NOT NULL |
| customer_id | STRING | Reference to customer | FK, NOT NULL |
| churn_date | DATE | Date of churn determination | NOT NULL |
| churn_bucket | STRING | 30_day, 60_day, 90_day, explicit | NOT NULL |
| churn_reason | STRING | Reason if known (competitive, price, product, other) | |
| last_activity_date | DATE | Date of last activity before churn | |
| days_inactive | INT | Days between last activity and churn date | |
| is_explicit | BOOLEAN | True if explicit cancellation | NOT NULL |
| created_at | TIMESTAMP | Record creation | NOT NULL |

### 4. features

Engineered feature store for model training and scoring.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| feature_snapshot_id | STRING | Unique snapshot identifier | PK, NOT NULL |
| customer_id | STRING | Reference to customer | FK, NOT NULL |
| snapshot_date | DATE | Date features were calculated | NOT NULL |
| tenure_months | INT | Customer tenure | |
| days_since_last_activity | INT | Inactivity days | |
| days_since_last_purchase | INT | Days since last purchase | |
| total_purchases_90d | INT | Purchases in last 90 days | |
| total_revenue_90d | DECIMAL(12,2) | Revenue in last 90 days | |
| support_tickets_90d | INT | Support tickets in last 90 days | |
| login_count_30d | INT | Logins in last 30 days | |
| usage_trend | DECIMAL(5,2) | Usage change % (current vs prior period) | |
| contract_days_remaining | INT | Days until contract end | |
| price_change_flag | BOOLEAN | Recent price increase | |
| nps_score | INT | Net Promoter Score if available | |
| created_at | TIMESTAMP | Record creation | NOT NULL |

**Note**: Additional features to be determined during EDA phase.

### 5. predictions

Model predictions output table.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| prediction_id | STRING | Unique prediction identifier | PK, NOT NULL |
| customer_id | STRING | Reference to customer | FK, NOT NULL |
| prediction_date | DATE | Date prediction was made | NOT NULL |
| model_version | STRING | MLflow model version/run ID | NOT NULL |
| prob_churn_30d | DECIMAL(5,4) | Probability of >30 day inactivity | 0-1 |
| prob_churn_60d | DECIMAL(5,4) | Probability of >60 day inactivity | 0-1 |
| prob_churn_90d | DECIMAL(5,4) | Probability of >90 day inactivity | 0-1 |
| prob_explicit_cancel | DECIMAL(5,4) | Probability of explicit cancellation | 0-1 |
| risk_tier | STRING | Low, Medium, High, Critical | NOT NULL |
| risk_score_composite | DECIMAL(5,4) | Weighted composite score | 0-1 |
| created_at | TIMESTAMP | Record creation | NOT NULL |

**Risk Tier Thresholds** (based on composite score):
- Low: <0.30
- Medium: 0.30-0.50
- High: 0.50-0.70
- Critical: >0.70

### 6. model_metrics

Model performance tracking over time.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| metric_id | STRING | Unique metric identifier | PK, NOT NULL |
| model_version | STRING | MLflow model version/run ID | NOT NULL |
| churn_bucket | STRING | Which bucket this metric applies to | NOT NULL |
| evaluation_date | DATE | Date of evaluation | NOT NULL |
| dataset_type | STRING | train, validation, test, production | NOT NULL |
| auc_roc | DECIMAL(5,4) | Area under ROC curve | |
| precision | DECIMAL(5,4) | Precision at threshold | |
| recall | DECIMAL(5,4) | Recall at threshold | |
| f1_score | DECIMAL(5,4) | F1 score | |
| threshold | DECIMAL(5,4) | Classification threshold used | |
| true_positives | INT | Confusion matrix TP | |
| false_positives | INT | Confusion matrix FP | |
| true_negatives | INT | Confusion matrix TN | |
| false_negatives | INT | Confusion matrix FN | |
| created_at | TIMESTAMP | Record creation | NOT NULL |

### 7. feature_importance

Feature importance results per model.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| importance_id | STRING | Unique identifier | PK, NOT NULL |
| model_version | STRING | MLflow model version/run ID | FK, NOT NULL |
| churn_bucket | STRING | Which bucket model | NOT NULL |
| feature_name | STRING | Feature column name | NOT NULL |
| coefficient | DECIMAL(10,6) | Logistic regression coefficient | |
| odds_ratio | DECIMAL(10,4) | exp(coefficient) | |
| std_error | DECIMAL(10,6) | Standard error of coefficient | |
| z_score | DECIMAL(10,4) | Wald z-statistic | |
| p_value | DECIMAL(10,6) | Statistical significance | |
| ci_lower | DECIMAL(10,6) | 95% CI lower bound (coefficient) | |
| ci_upper | DECIMAL(10,6) | 95% CI upper bound (coefficient) | |
| importance_rank | INT | Rank by absolute coefficient | |
| created_at | TIMESTAMP | Record creation | NOT NULL |

### 8. policies

Retention policy definitions.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| policy_id | STRING | Unique policy identifier | PK, NOT NULL |
| policy_name | STRING | Descriptive name | NOT NULL |
| policy_type | STRING | Discount, Outreach, Service, Product | NOT NULL |
| description | STRING | Policy details | |
| start_date | DATE | Policy effective start | NOT NULL |
| end_date | DATE | Policy end (NULL if ongoing) | |
| target_segment | STRING | Target customer criteria | |
| expected_impact | DECIMAL(5,4) | Expected churn reduction % | |
| status | STRING | Active, Completed, Cancelled | NOT NULL |
| created_at | TIMESTAMP | Record creation | NOT NULL |
| updated_at | TIMESTAMP | Last update | NOT NULL |

### 9. policy_cohorts

Customer assignments to policies for efficacy tracking.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| cohort_id | STRING | Unique cohort assignment ID | PK, NOT NULL |
| policy_id | STRING | Reference to policy | FK, NOT NULL |
| customer_id | STRING | Reference to customer | FK, NOT NULL |
| assignment_date | DATE | Date customer added to policy | NOT NULL |
| cohort_type | STRING | Treatment, Control | NOT NULL |
| baseline_risk_score | DECIMAL(5,4) | Risk score at assignment | |
| baseline_churn_bucket | STRING | Highest risk bucket at assignment | |
| exit_date | DATE | Date customer exited cohort | |
| exit_reason | STRING | Churned, Retained, PolicyEnded | |
| created_at | TIMESTAMP | Record creation | NOT NULL |

## Data Validation Rules

### customers
- customer_id must be unique
- tenure_months ≥ 0
- contract_end_date ≥ contract_start_date

### customer_activity  
- customer_id must exist in customers
- activity_date ≤ current_date

### predictions
- All probability columns between 0 and 1
- risk_tier must be one of: Low, Medium, High, Critical
- model_version must reference valid MLflow run

### feature_importance
- p_value between 0 and 1
- ci_lower < coefficient < ci_upper

## State Transitions

### Customer Churn State
```
Active → Early Warning (>30d inactive) → At Risk (>60d) → Likely Churned (>90d)
                                                                    ↓
Active → Explicit Cancellation ←────────────────────────────────────┘
```

### Policy Cohort State
```
Assigned → Active → [Churned | Retained | PolicyEnded]
```
