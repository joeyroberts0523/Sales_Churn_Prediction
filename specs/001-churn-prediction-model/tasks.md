# Tasks: Customer Churn Prediction Model

**Input**: Design documents from `/specs/001-churn-prediction-model/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Notebooks**: `notebooks/` at repository root (Fabric notebooks)
- **Source**: `src/` at repository root (Python modules)
- **Tests**: `tests/` at repository root
- **Power BI**: `powerbi/` at repository root

---

## Phase 1: Setup (Shared Infrastructure) ✅

**Purpose**: Project initialization and Fabric workspace setup

- [x] T001 Create project directory structure per plan.md (src/, notebooks/, tests/, powerbi/)
- [x] T002 [P] Create src/__init__.py with package initialization
- [x] T003 [P] Create src/utils/__init__.py and src/utils/config.py with configuration management
- [x] T004 [P] Create src/utils/logging.py with structured logging setup
- [x] T005 [P] Create requirements.txt with dependencies (scikit-learn, pandas, numpy, scipy, mlflow, great-expectations)
- [x] T006 [P] Create environment.yml for Fabric environment configuration
- [x] T007 Create .gitignore for Python/Jupyter artifacts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Layer

- [x] T008 Create src/data/__init__.py
- [x] T009 [P] Create src/data/ingestion.py with Lakehouse data loading functions
- [x] T010 [P] Create src/data/preprocessing.py with missing value handling and encoding
- [x] T011 [P] Create src/data/validation.py with data quality checks and freshness validation

### Data Model Tables (Delta)

- [x] T012 Create Lakehouse Delta table schema for `customers` per data-model.md
- [x] T013 [P] Create Lakehouse Delta table schema for `customer_activity` per data-model.md
- [x] T014 [P] Create Lakehouse Delta table schema for `churn_events` per data-model.md
- [x] T015 [P] Create Lakehouse Delta table schema for `features` per data-model.md
- [x] T016 [P] Create Lakehouse Delta table schema for `predictions` per data-model.md
- [x] T017 [P] Create Lakehouse Delta table schema for `model_metrics` per data-model.md
- [x] T018 [P] Create Lakehouse Delta table schema for `feature_importance` per data-model.md

### Data Validation Framework

- [x] T019 Create tests/data_quality/great_expectations/ directory structure
- [x] T020 [P] Create Great Expectations expectation suite for customers table
- [x] T021 [P] Create Great Expectations expectation suite for customer_activity table
- [x] T022 [P] Create Great Expectations checkpoint configuration

### Exploration Notebook

- [x] T023 Create notebooks/01_data_exploration.ipynb with EDA and data profiling
- [ ] T024 Document baseline data statistics and quality issues in notebook (pending actual data)

**Checkpoint**: Foundation ready - Lakehouse tables created, data validation configured, EDA complete

---

## Phase 3: User Story 1 & 2 - Predict At-Risk Customers & Identify Churn Drivers (Priority: P1) 🎯 MVP

**Goal**: Train logistic regression model that predicts churn probability and outputs feature importance with statistical significance

**Independent Test**: Run model on holdout dataset, validate AUC-ROC ≥0.70, review top 10 features with coefficients

### Feature Engineering (shared by US1 & US2)

- [x] T025 Create src/features/__init__.py
- [x] T026 [P] [US1] Create src/features/engineering.py with feature transformation functions
- [x] T027 [P] [US1] Create src/features/selection.py with feature selection utilities
- [x] T028 [US1] Create notebooks/02_feature_engineering.ipynb implementing churn labels for buckets (>30d, >60d, >90d, explicit)
- [x] T029 [US1] Add feature calculations to notebook: tenure, days_since_last_activity, purchase metrics, support tickets
- [x] T030 [US1] Implement missing value imputation strategy in notebook (document in markdown cells)
- [ ] T031 [US1] Output features to Lakehouse `features` Delta table (pending data connection)

### Model Development (US1 & US2)

- [x] T032 Create src/models/__init__.py
- [x] T033 [P] [US1] Create src/models/training.py with LogisticRegression training pipeline
- [x] T034 [P] [US1] Create src/models/evaluation.py with metrics calculation (AUC-ROC, precision, recall, F1)
- [x] T035 [P] [US2] Create src/models/registry.py with MLflow model registration functions
- [x] T036 [US1] Create notebooks/03_model_training.ipynb with stratified k-fold CV and class_weight='balanced'
- [x] T037 [US1] Configure MLflow experiment tracking in training notebook (log hyperparameters, metrics, artifacts)
- [x] T038 [US1] Train separate models for each churn bucket (30d, 60d, 90d, explicit) in notebook
- [ ] T039 [US1] Validate AUC-ROC ≥0.70 for each model on holdout test set (pending data connection)

### Feature Importance (US2)

- [x] T040 Create src/reporting/__init__.py
- [x] T041 [P] [US2] Create src/reporting/feature_importance.py with coefficient extraction and odds ratio calculation
- [x] T042 [US2] Create notebooks/06_feature_importance.ipynb extracting coefficients, odds ratios, p-values, confidence intervals
- [x] T043 [US2] Generate feature_importance records per contracts/feature-importance-output.json schema
- [ ] T044 [US2] Output feature importance to Lakehouse `feature_importance` Delta table (pending data connection)

### Model Evaluation

- [x] T045 [US1] Create notebooks/04_model_evaluation.ipynb with comprehensive performance analysis
- [x] T046 [US1] Generate confusion matrices and classification reports per bucket
- [ ] T047 [US1] Output model metrics to Lakehouse `model_metrics` Delta table (pending data connection)
- [ ] T048 [US1] Register best-performing models in MLflow model registry (pending data connection)

**Checkpoint**: User Story 1 & 2 complete - Models trained with AUC-ROC ≥0.70, feature importance report available

---

## Phase 4: Scoring Pipeline (P1 completion)

**Goal**: Weekly batch scoring pipeline that outputs predictions to Lakehouse

**Independent Test**: Run scoring notebook, verify predictions table populated with risk tiers

### Scoring Implementation

- [x] T049 Create src/scoring/__init__.py
- [x] T050 [P] [US1] Create src/scoring/batch.py with batch scoring logic
- [x] T051 [P] [US1] Create src/scoring/risk_tiers.py with risk categorization (Low/Medium/High/Critical)
- [x] T052 [US1] Create notebooks/05_batch_scoring.ipynb loading registered models and scoring all customers
- [x] T053 [US1] Output predictions per contracts/prediction-output.json schema
- [x] T055 [US1] Add data freshness check (fail if data >7 days old)
- [ ] T054 [US1] Save predictions to Lakehouse `predictions` Delta table with timestamps (pending data connection)

**Checkpoint**: Weekly scoring pipeline complete - predictions available in Lakehouse

---

## Phase 5: User Story 3 - Monitor Policy Effectiveness (Priority: P2)

**Goal**: Track retention policy impact on churn rates with statistical significance testing

**Independent Test**: Create test policy cohort, generate efficacy report showing before/after churn rates

### Policy Tables

- [ ] T056 Create Lakehouse Delta table schema for `policies` per data-model.md
- [ ] T057 [P] [US3] Create Lakehouse Delta table schema for `policy_cohorts` per data-model.md

### Policy Reporting

- [x] T058 [P] [US3] Create src/reporting/policy_efficacy.py with cohort comparison and statistical tests
- [x] T059 [US3] Create notebooks/07_policy_monitoring.ipynb with policy efficacy analysis
- [x] T060 [US3] Implement chi-square or t-test for statistical significance between treatment/control groups
- [x] T061 [US3] Generate policy efficacy summary with baseline vs current churn rates

### Power BI Dashboards (US1, US2, US3)

- [ ] T062 [P] [US1] Create powerbi/churn_dashboard.pbix with at-risk customer list (filter by risk_tier)
- [ ] T063 [P] [US2] Add feature importance visualization to churn_dashboard.pbix (bar chart top 10 by odds_ratio)
- [ ] T064 [US3] Create powerbi/policy_monitoring.pbix with before/after churn rate comparison
- [ ] T065 [US3] Configure DirectLake connection to churn_lakehouse for both dashboards

**Checkpoint**: User Story 3 complete - Policy efficacy tracking with statistical significance, dashboards available

---

## Phase 6: User Story 4 - Automated Risk Alerts (Priority: P3)

**Goal**: Automated alerts when customer risk significantly increases

**Independent Test**: Simulate customer crossing risk threshold, verify alert generated

### Alert Implementation

- [ ] T066 [US4] Add alert logic to notebooks/05_batch_scoring.ipynb detecting threshold crossings
- [ ] T067 [US4] Implement alert output table in Lakehouse for threshold crossing events
- [ ] T068 [US4] Configure Power Automate flow to send email/Teams notifications on new alert records

**Checkpoint**: User Story 4 complete - Automated alerts on risk threshold crossings

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Pipeline automation, documentation, and quality improvements

### Automation

- [ ] T069 Schedule weekly data pipeline in Fabric (source → Lakehouse refresh)
- [ ] T070 [P] Schedule weekly batch scoring notebook after data refresh
- [ ] T071 [P] Configure Power BI dataset refresh after predictions table update

### Testing

- [x] T072 [P] Create tests/unit/test_preprocessing.py with unit tests for data preprocessing
- [x] T073 [P] Create tests/unit/test_feature_engineering.py with unit tests for feature calculations
- [x] T074 [P] Create tests/unit/test_risk_tiers.py with unit tests for risk categorization
- [ ] T075 Create tests/integration/test_data_pipeline.py with end-to-end data flow test
- [ ] T076 [P] Create tests/integration/test_scoring_pipeline.py with scoring integration test

### Documentation

- [ ] T077 Update specs/001-churn-prediction-model/quickstart.md with final setup instructions
- [ ] T078 [P] Create model card documentation for each trained model
- [ ] T079 Run full pipeline validation per quickstart.md checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **US1 & US2 (Phase 3)**: Depends on Foundational - Model training and feature importance
- **Scoring (Phase 4)**: Depends on Phase 3 - Requires trained models
- **US3 (Phase 5)**: Depends on Foundational + Scoring infrastructure
- **US4 (Phase 6)**: Depends on Scoring pipeline (Phase 4)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Predict At-Risk Customers - Can start after Phase 2
- **User Story 2 (P1)**: Identify Churn Drivers - Shares Phase 3 with US1 (same model)
- **User Story 3 (P2)**: Policy Monitoring - Can start after Phase 4 (needs predictions)
- **User Story 4 (P3)**: Automated Alerts - Can start after Phase 4 (needs scoring pipeline)

### Within Each Phase

- Tables ([P] tasks) can be created in parallel
- Notebooks must follow dependency order
- Models must be trained before scoring
- Dashboards can parallel after data is available

### Parallel Opportunities

**Phase 2 Parallel Group:**
```
T009, T010, T011 (src/data/ modules)
T013, T014, T015, T016, T017, T018 (Delta tables)
T020, T021 (Great Expectations suites)
```

**Phase 3 Parallel Group:**
```
T026, T027 (src/features/ modules)
T033, T034, T035 (src/models/ modules)
T041 (src/reporting/feature_importance.py)
```

**Phase 4 Parallel Group:**
```
T050, T051 (src/scoring/ modules)
```

**Phase 5 Parallel Group:**
```
T058 (policy_efficacy.py)
T062, T063 (Power BI dashboards)
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - Lakehouse tables, validation)
3. Complete Phase 3: Train models, generate predictions, feature importance
4. Complete Phase 4: Weekly scoring pipeline
5. **STOP and VALIDATE**: Test model performance, review feature importance with stakeholders
6. Deploy dashboards for at-risk customer list and feature importance

### Incremental Delivery

1. **MVP (Phases 1-4)**: Churn predictions + feature importance → Core business value
2. **Add Policy Monitoring (Phase 5)**: Track intervention effectiveness → Close feedback loop
3. **Add Alerts (Phase 6)**: Proactive notifications → Operational efficiency
4. **Polish (Phase 7)**: Automation, testing, documentation → Production readiness

---

## Task Summary

| Phase | Task Range | Count | Focus |
|-------|------------|-------|-------|
| Setup | T001-T007 | 7 | Project structure |
| Foundational | T008-T024 | 17 | Data infrastructure |
| US1 & US2 (P1) | T025-T048 | 24 | Model training & feature importance |
| Scoring | T049-T055 | 7 | Weekly predictions |
| US3 (P2) | T056-T065 | 10 | Policy monitoring |
| US4 (P3) | T066-T068 | 3 | Alerts |
| Polish | T069-T079 | 11 | Automation & quality |
| **Total** | | **79** | |

---

## Notes

- [P] tasks = different files, can run in parallel
- [Story] label maps to US1/US2/US3/US4 from spec.md
- Notebooks are primary execution interface; src/ provides reusable modules
- MLflow tracks all experiments - register only models meeting AUC-ROC ≥0.70
- Great Expectations validates data before each model training/scoring run
- Power BI dashboards connect via DirectLake for real-time data access
