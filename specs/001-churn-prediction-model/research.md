# Research: Customer Churn Prediction Model

**Feature**: 001-churn-prediction-model  
**Date**: 2026-02-09

## Technology Decisions

### 1. ML Framework: scikit-learn

**Decision**: Use scikit-learn's LogisticRegression for the baseline model.

**Rationale**:
- Native coefficient extraction for interpretability (Constitution Principle III)
- Built-in class_weight parameter for handling imbalance
- Well-documented, production-proven
- Compatible with MLflow for experiment tracking

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| statsmodels | Less integration with MLflow, slower for large datasets |
| PySpark MLlib | Overkill for logistic regression; use scikit-learn with sampled data |
| XGBoost | More accurate but less interpretable; violates Constitution Principle III without justification |

### 2. Class Imbalance Handling: Class Weights

**Decision**: Use class_weight='balanced' in LogisticRegression rather than SMOTE.

**Rationale**:
- Simpler, no synthetic data creation
- No risk of data leakage during cross-validation
- Computationally efficient
- Sufficient for moderate imbalance typical in churn (5-20% churn rate)

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| SMOTE | Adds complexity, risk of leakage if not careful with CV splits |
| Undersampling | Loses valuable information from majority class |
| No adjustment | Would bias model toward majority class |

### 3. Feature Importance: Coefficients + Statistical Testing

**Decision**: Extract logistic regression coefficients, compute odds ratios, and use scipy.stats for confidence intervals and p-values.

**Rationale**:
- Coefficients are directly interpretable for logistic regression
- Odds ratios express impact in business-friendly terms ("2x more likely to churn")
- Confidence intervals quantify uncertainty
- P-values indicate statistical significance (Constitution Principle IV)

**Implementation**:
```python
# Coefficients from model
coefficients = model.coef_[0]
# Odds ratios
odds_ratios = np.exp(coefficients)
# Standard errors via inverse Hessian or bootstrap
# 95% CI: exp(coef ± 1.96 * SE)
```

### 4. Experiment Tracking: MLflow in Fabric

**Decision**: Use MLflow integrated with Microsoft Fabric for experiment tracking and model registry.

**Rationale**:
- Native integration with Fabric Data Science experience
- Tracks hyperparameters, metrics, artifacts automatically
- Model versioning and registry for deployment
- Meets Constitution Principle II (Reproducibility)

**Logged Artifacts**:
- Hyperparameters (C, class_weight, solver, random_state)
- Metrics (AUC-ROC, precision, recall, F1, confusion matrix)
- Feature importance report
- Training/test split seed
- Model binary

### 5. Data Storage: Delta Tables in Lakehouse

**Decision**: Store all data in Delta format within Fabric Lakehouse.

**Rationale**:
- ACID transactions for data integrity
- Time travel for reproducibility (Constitution Principle II)
- Schema enforcement
- Native Fabric integration (Constitution Principle VI)

**Tables**:
| Table | Purpose |
|-------|---------|
| `customers` | Customer attributes and demographics |
| `customer_activity` | Activity history for inactivity calculation |
| `churn_events` | Historical churn labels with bucket classification |
| `features` | Engineered feature store |
| `predictions` | Scored predictions with timestamps |
| `model_metrics` | Performance tracking over time |
| `policies` | Retention policy definitions |
| `policy_cohorts` | Customer-policy assignments |

### 6. Data Validation: Great Expectations

**Decision**: Use Great Expectations for data quality validation.

**Rationale**:
- Declarative expectations for data quality rules
- Integrates with Python/PySpark workflows
- Generates documentation automatically
- Catches data drift and quality issues before model training

**Key Expectations**:
- No nulls in required columns (customer_id, activity_date)
- Value ranges (probability 0-1, tenure ≥0)
- Referential integrity (customer_id exists in customers table)
- Row count thresholds (minimum training data size)

### 7. Multi-Bucket Prediction Approach

**Decision**: Train separate binary classifiers for each churn bucket (>30, >60, >90 days) plus explicit cancellation.

**Rationale**:
- Different intervention windows require different predictions
- Allows independent optimization per bucket
- Business can act on most relevant bucket for their timeline
- Cleaner model cards per bucket

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| Single multi-class | Buckets are cumulative, not mutually exclusive |
| Survival analysis | More complex, harder to interpret coefficients |
| Single 90-day model | Loses early warning capability |

### 8. Dashboard Refresh Strategy

**Decision**: Weekly batch scoring triggers dashboard refresh within 24 hours.

**Rationale**:
- Aligns with weekly data refresh cadence
- Allows time for data validation and scoring completion
- Meets SC-004 success criteria

**Pipeline Schedule**:
1. Weekly data refresh (source systems → Lakehouse)
2. Data validation (Great Expectations)
3. Batch scoring notebook execution
4. Delta table updates (predictions, metrics)
5. Power BI dataset refresh (automatic on table update)

## Open Items Resolved

All NEEDS CLARIFICATION items have been resolved through the above research.
