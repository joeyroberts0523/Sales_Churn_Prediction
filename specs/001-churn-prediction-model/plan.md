# Implementation Plan: Customer Churn Prediction Model

**Branch**: `001-churn-prediction-model` | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)

## Summary

Build a logistic regression churn prediction model in Microsoft Fabric that predicts customer churn across tiered inactivity buckets (>30, >60, >90 days + explicit cancellations), identifies top churn drivers with statistical significance, and enables policy efficacy monitoring through Power BI dashboards. Weekly batch scoring with MLflow experiment tracking.

## Technical Context

**Language/Version**: Python 3.11+ (PySpark for distributed processing)  
**Primary Dependencies**: scikit-learn, pandas, numpy, mlflow, scipy (for statistical tests)  
**Platform**: Microsoft Fabric (Data Engineering, Data Science, Lakehouse)  
**Storage**: Fabric Lakehouse (Delta tables for customers, predictions, features, policies)  
**Testing**: pytest for unit tests, Great Expectations for data validation  
**Target Platform**: Microsoft Fabric workspace with Power BI integration  
**Project Type**: Data Science / ML Pipeline  
**Performance Goals**: Model training <4 hours, weekly scoring <2 hours, dashboard refresh <24 hours  
**Constraints**: AUC-ROC ≥0.70, 18+ months historical data, weekly refresh cadence  
**Scale/Scope**: Full customer base scoring, historical data spanning 18+ months

## Constitution Check

*GATE: All principles verified for compliance*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Data-First Development | ✅ PASS | Plan includes EDA notebook, data profiling, feature engineering before modeling |
| II. Reproducibility | ✅ PASS | MLflow tracking, versioned notebooks, logged seeds/hyperparameters, documented splits |
| III. Interpretability Over Complexity | ✅ PASS | Logistic regression baseline with coefficients, odds ratios, confidence intervals |
| IV. Feature Importance as First-Class | ✅ PASS | Dedicated feature importance pipeline with statistical significance |
| V. Policy Monitoring Integration | ✅ PASS | Policy cohort tracking, pre/post comparison, statistical tests |
| VI. Microsoft Fabric Native | ✅ PASS | Lakehouse storage, Fabric notebooks, MLflow registry, Power BI dashboards |

## Project Structure

### Documentation (this feature)

```text
specs/001-churn-prediction-model/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity and table definitions
├── quickstart.md        # Developer onboarding guide
├── contracts/           # API/data contracts
│   ├── prediction-output.json
│   └── feature-importance-output.json
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Task breakdown (from /speckit.tasks)
```

### Source Code (Fabric Notebooks & Scripts)

```text
notebooks/
├── 01_data_exploration.ipynb      # EDA and data profiling
├── 02_feature_engineering.ipynb   # Feature creation and selection
├── 03_model_training.ipynb        # Logistic regression training with MLflow
├── 04_model_evaluation.ipynb      # Performance metrics and validation
├── 05_batch_scoring.ipynb         # Weekly prediction pipeline
├── 06_feature_importance.ipynb    # Coefficient analysis and reporting
└── 07_policy_monitoring.ipynb     # Policy efficacy analysis

src/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── ingestion.py               # Lakehouse data loading
│   ├── preprocessing.py           # Missing value handling, encoding
│   └── validation.py              # Data quality checks
├── features/
│   ├── __init__.py
│   ├── engineering.py             # Feature transformations
│   └── selection.py               # Feature selection utilities
├── models/
│   ├── __init__.py
│   ├── training.py                # Model training pipeline
│   ├── evaluation.py              # Metrics calculation
│   └── registry.py                # MLflow model registration
├── scoring/
│   ├── __init__.py
│   ├── batch.py                   # Weekly scoring logic
│   └── risk_tiers.py              # Risk categorization
├── reporting/
│   ├── __init__.py
│   ├── feature_importance.py      # Coefficient/odds ratio reports
│   └── policy_efficacy.py         # Policy tracking reports
└── utils/
    ├── __init__.py
    ├── config.py                  # Configuration management
    └── logging.py                 # Structured logging

tests/
├── __init__.py
├── unit/
│   ├── test_preprocessing.py
│   ├── test_feature_engineering.py
│   └── test_risk_tiers.py
├── integration/
│   ├── test_data_pipeline.py
│   └── test_scoring_pipeline.py
└── data_quality/
    └── great_expectations/        # Data validation expectations

powerbi/
├── churn_dashboard.pbix           # Main stakeholder dashboard
└── policy_monitoring.pbix         # Policy efficacy dashboard
```

**Structure Decision**: Single project structure with Fabric notebooks for interactive development and Python modules for reusable logic. Notebooks serve as orchestration layer calling into src/ modules.

## Implementation Phases

### Phase 1: Data Foundation (P1 prerequisite)
1. Set up Fabric Lakehouse with customer data tables
2. Create data ingestion pipeline from source systems
3. Implement data quality validation with Great Expectations
4. Build EDA notebook with profiling and baseline statistics

### Phase 2: Feature Engineering (P1 prerequisite)
1. Define churn labels for each bucket (>30, >60, >90 days, explicit)
2. Engineer customer features (tenure, usage patterns, support history, billing)
3. Handle missing values with documented imputation strategy
4. Create feature store in Lakehouse for reproducibility

### Phase 3: Model Development (P1 - User Story 1 & 2)
1. Train logistic regression with stratified k-fold CV
2. Handle class imbalance (class weights or SMOTE)
3. Track experiments in MLflow with hyperparameters and metrics
4. Generate feature importance with coefficients, odds ratios, p-values, CIs
5. Validate AUC-ROC ≥0.70 on holdout set

### Phase 4: Scoring Pipeline (P1 completion)
1. Implement weekly batch scoring notebook
2. Output predictions to Lakehouse with timestamps
3. Calculate risk tiers (Low/Medium/High/Critical)
4. Set up prediction logging for auditability

### Phase 5: Reporting & Dashboards (P2 - User Story 3)
1. Create feature importance report generation
2. Build Power BI churn dashboard with at-risk customer list
3. Implement policy cohort tracking tables
4. Build policy efficacy dashboard with statistical significance

### Phase 6: Automation & Alerts (P3 - User Story 4)
1. Schedule weekly scoring pipeline in Fabric
2. Implement alert logic for risk threshold crossings
3. Configure notification channels (email/Teams)

## Complexity Tracking

> No constitution violations requiring justification.

| Decision | Rationale |
|----------|-----------|
| Logistic Regression only | Constitution Principle III mandates interpretability; complex models would require justification |
| Delta tables in Lakehouse | Constitution Principle VI requires Fabric-native storage |
| Weekly not daily refresh | Per spec requirements to manage pipeline costs |
