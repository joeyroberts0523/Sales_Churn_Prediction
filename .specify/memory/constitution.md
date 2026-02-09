<!--
Sync Impact Report
==================
Version change: 0.0.0 → 1.0.0
Modified principles: Initial creation
Added sections: Core Principles (6), Technology Stack, Model Quality Standards, Governance
Removed sections: None (initial)
Templates requiring updates: ✅ N/A (initial constitution)
Follow-up TODOs: None
-->

# Sales Churn Prediction Constitution

## Core Principles

### I. Data-First Development
All features and model improvements MUST begin with understanding the data. Data exploration, quality assessment, and feature engineering precede any model training. Every data transformation MUST be documented with clear rationale. No model shall be built on data that has not been profiled and validated.

### II. Reproducibility (NON-NEGOTIABLE)
Every experiment, model training run, and analysis MUST be fully reproducible. This requires:
- Version-controlled notebooks and scripts
- Pinned dependencies and environment specifications
- Logged hyperparameters, random seeds, and data versions
- Clear documentation of data splits (train/validation/test)

### III. Interpretability Over Complexity
Given the business goal of identifying churn drivers and monitoring policy efficacy, model interpretability is paramount. Logistic regression is the baseline model. Any more complex model MUST demonstrate significant improvement AND provide equivalent interpretability through feature importance, SHAP values, or similar techniques.

### IV. Feature Importance as First-Class Output
The primary deliverable is not just predictions but actionable insights. Feature importance analysis MUST:
- Identify top correlates of churn with statistical significance
- Distinguish between correlation and actionable drivers
- Support business decisions on policy interventions
- Be updated and validated with each model refresh

### V. Policy Monitoring Integration
The model MUST support ongoing policy efficacy tracking:
- Baseline churn rates before policy implementation
- Segmented analysis for policy-targeted customers
- Time-series tracking of churn rates post-intervention
- A/B testing framework support where applicable

### VI. Microsoft Fabric Native
All data pipelines, transformations, and model training MUST leverage Microsoft Fabric capabilities:
- Data stored in Fabric Lakehouse or Warehouse
- Notebooks for exploration and model development
- MLflow for experiment tracking and model registry
- Power BI integration for stakeholder dashboards

## Technology Stack

- **Platform**: Microsoft Fabric (Lakehouse, Data Engineering, Data Science)
- **Languages**: Python 3.11+ (PySpark for distributed processing)
- **ML Framework**: scikit-learn for logistic regression, MLflow for tracking
- **Visualization**: matplotlib, seaborn for analysis; Power BI for dashboards
- **Version Control**: Git with GitHub for code and notebook versioning

## Model Quality Standards

- **Minimum Metrics**: AUC-ROC ≥ 0.70, Precision and Recall balanced for business needs
- **Validation**: Stratified k-fold cross-validation (k=5 minimum)
- **Drift Monitoring**: Monthly model performance review against holdout data
- **Documentation**: Every model version MUST have a model card documenting training data, features, performance metrics, and known limitations

## Governance

This constitution supersedes all other development practices for the Sales Churn Prediction project. Amendments require:
1. Documented justification for the change
2. Review of impact on existing models and pipelines
3. Version increment following semantic versioning
4. Update to all dependent documentation

All pull requests MUST verify compliance with these principles. Model deployments require sign-off confirming adherence to reproducibility and interpretability standards.

**Version**: 1.0.0 | **Ratified**: 2026-02-09 | **Last Amended**: 2026-02-09
