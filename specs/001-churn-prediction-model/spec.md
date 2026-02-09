# Feature Specification: Customer Churn Prediction Model

**Feature Branch**: `001-churn-prediction-model`  
**Created**: 2026-02-09  
**Status**: Draft  
**Input**: Build a logistic regression model using Microsoft Fabric to predict customer churn and identify features with the greatest correlation to churn. This will identify customers in a likely zone of churn AND monitor policies in place to prevent churn to see efficacy of policy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Predict At-Risk Customers (Priority: P1)

As a Sales/Customer Success Manager, I need to identify which customers are most likely to churn in the next 30-90 days so that I can prioritize retention outreach and allocate resources effectively.

**Why this priority**: This is the core value proposition—without accurate churn predictions, all other features have no foundation. Early identification of at-risk customers directly enables proactive retention efforts.

**Independent Test**: Can be fully tested by running the model on a holdout dataset and validating predictions against actual churn outcomes. Delivers immediate value by producing a ranked list of at-risk customers.

**Acceptance Scenarios**:

1. **Given** historical customer data is loaded, **When** the model is trained and scored on current customers, **Then** a ranked list of customers by churn probability is produced with confidence scores.
2. **Given** a customer with known high-risk indicators, **When** the model scores this customer, **Then** they appear in the top 20% of churn risk.
3. **Given** model predictions from 90 days ago, **When** compared to actual churn outcomes, **Then** the AUC-ROC is at least 0.70.

---

### User Story 2 - Identify Churn Drivers (Priority: P1)

As a Business Analyst, I need to understand which customer attributes and behaviors most strongly correlate with churn so that I can recommend targeted interventions and inform product/service improvements.

**Why this priority**: Equal priority to predictions because understanding "why" customers churn is essential for actionable business decisions. Without this, predictions are a black box.

**Independent Test**: Can be tested by examining feature importance rankings and validating they align with domain expertise. Delivers value through a documented feature importance report with statistical significance.

**Acceptance Scenarios**:

1. **Given** a trained logistic regression model, **When** feature importance is extracted, **Then** the top 10 features are listed with their coefficients, odds ratios, and confidence intervals.
2. **Given** feature importance results, **When** reviewed by business stakeholders, **Then** at least 7 of the top 10 features have clear business interpretation.
3. **Given** a new feature is added to the model, **When** retrained, **Then** the feature importance report updates to include the new feature's relative contribution.

---

### User Story 3 - Monitor Policy Effectiveness (Priority: P2)

As a Business Operations Manager, I need to track whether retention policies (discounts, outreach campaigns, service improvements) are reducing churn among targeted customer segments so that I can measure ROI and adjust strategies.

**Why this priority**: Secondary to core prediction/identification because it requires the foundation of P1 stories. However, critical for closing the feedback loop on business interventions.

**Independent Test**: Can be tested by comparing churn rates before and after policy implementation for targeted vs. control groups. Delivers value through dashboards showing policy impact metrics.

**Acceptance Scenarios**:

1. **Given** a retention policy was applied to a customer segment 60 days ago, **When** the efficacy report is generated, **Then** it shows churn rates before vs. after with statistical significance indicators.
2. **Given** multiple policies are active, **When** the dashboard is viewed, **Then** each policy is tracked separately with customer counts, baseline churn, and current churn rate.
3. **Given** no statistically significant change in churn, **When** the report is generated, **Then** it clearly indicates insufficient evidence to claim policy success.

---

### User Story 4 - Automated Risk Alerts (Priority: P3)

As a Customer Success Representative, I need to receive automated alerts when a customer's churn risk significantly increases so that I can take immediate action before it's too late.

**Why this priority**: Enhancement that improves usability but requires all upstream components to be working. Not essential for initial MVP.

**Independent Test**: Can be tested by simulating a customer whose risk score crosses the threshold and verifying an alert is generated. Delivers value through timely notifications.

**Acceptance Scenarios**:

1. **Given** a customer's churn probability crosses the high-risk threshold (e.g., >70%), **When** the weekly scoring batch completes, **Then** an alert is sent to the assigned representative.
2. **Given** alert preferences are configured, **When** an alert triggers, **Then** it is delivered via the specified channel (email/Teams/dashboard).

---

### Edge Cases

- What happens when a customer has minimal historical data (new customers)?
  - Model should flag these as "insufficient data" rather than produce unreliable predictions.
- How does the system handle missing values in key features?
  - Missing values should be imputed using documented strategy (median/mode) or flagged for review.
- What if the training data has class imbalance (few churners vs. many retained)?
  - Model training should use appropriate techniques (SMOTE, class weights) documented in model card.
- How does the model behave during data pipeline failures?
  - Predictions should not run on stale data; system should alert on data freshness violations.
- How does seasonality affect predictions?
  - 18 months of historical data ensures full seasonal cycle coverage; model should account for seasonal patterns in churn behavior.
- How are customers classified across multiple inactivity buckets?
  - A customer in the >90 day bucket is also counted in >60 and >30 buckets for reporting; predictions focus on the most severe applicable bucket.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ingest customer data from the designated Fabric Lakehouse/Warehouse.
- **FR-002**: System MUST train a logistic regression model using historical customer data with labeled churn outcomes.
- **FR-003**: System MUST produce a churn probability score (0-1) for each customer.
- **FR-004**: System MUST calculate and display feature importance with statistical metrics (coefficients, p-values, confidence intervals).
- **FR-005**: System MUST categorize customers into risk tiers (Low, Medium, High, Critical) based on configurable thresholds.
- **FR-006**: System MUST track model performance metrics (AUC-ROC, precision, recall, F1) over time.
- **FR-007**: System MUST support retraining on updated data without manual intervention.
- **FR-008**: System MUST log all predictions with timestamps for auditability and policy monitoring.
- **FR-009**: System MUST generate policy efficacy reports comparing churn rates across segments and time periods.
- **FR-010**: System MUST integrate with Power BI for stakeholder dashboards.
- **FR-011**: System MUST refresh predictions on a weekly cadence aligned with data pipeline updates.
- **FR-012**: System MUST classify churn events into defined inactivity buckets (>30 days, >60 days, >90 days) and explicit cancellations.

### Churn Definition

Churn is classified into the following buckets based on customer inactivity or explicit action:

| Bucket | Definition | Use Case |
|--------|------------|----------|
| **Early Warning (>30 days)** | No customer activity for more than 30 days | Early intervention opportunity |
| **At Risk (>60 days)** | No customer activity for more than 60 days | Escalated outreach required |
| **Likely Churned (>90 days)** | No customer activity for more than 90 days | Near-certain churn, last resort actions |
| **Explicit Cancellation** | Customer explicitly cancels service/contract | Confirmed churn, exit interview opportunity |

Notes:
- Buckets are cumulative for reporting (a >90 day customer appears in all inactivity buckets)
- Model predictions target the probability of reaching each bucket
- Explicit cancellations are tracked separately as they provide definitive churn signal

### Key Entities

- **Customer**: Individual or account being scored; includes demographics, tenure, product usage, support interactions, billing history.
- **Churn Event**: Historical record of a customer leaving; includes date, reason (if known), churn bucket classification, final state.
- **Prediction**: Point-in-time churn probability for a customer; includes score per bucket, overall risk tier, confidence, timestamp.
- **Feature**: Input variable used in model; includes name, importance score, coefficient, statistical significance.
- **Policy**: Retention intervention applied to customers; includes type, start date, target segment, expected impact.
- **Policy Cohort**: Group of customers targeted by a policy; tracked for pre/post churn comparison.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Model achieves AUC-ROC of at least 0.70 on holdout test data within first training cycle.
- **SC-002**: Business stakeholders can identify top 5 churn drivers within 5 minutes of viewing the feature importance report.
- **SC-003**: Customers flagged as "high risk" (top 20%) account for at least 50% of actual churners in validation period.
- **SC-004**: Policy efficacy dashboard updates within 24 hours of weekly data refresh.
- **SC-005**: Sales team can access at-risk customer list and take action within 1 business day of weekly model scoring.
- **SC-006**: Model retraining completes within 4 hours when triggered.
- **SC-007**: Feature importance report includes statistical significance for all top 10 features.
- **SC-008**: Churn predictions are available for each inactivity bucket (>30, >60, >90 days) enabling tiered intervention strategies.

## Assumptions

- Historical customer data with labeled churn outcomes exists in the Fabric environment.
- At least 18 months of historical data is available for training to capture full seasonal cycles and distinguish signal from noise.
- Churn is classified into buckets: >30 days inactivity, >60 days inactivity, >90 days inactivity, and explicit cancellations.
- Data refresh frequency is weekly.
- Target users have Power BI access for dashboard consumption.
- Risk thresholds will be: Low (<30%), Medium (30-50%), High (50-70%), Critical (>70%).
