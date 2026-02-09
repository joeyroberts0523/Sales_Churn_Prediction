"""
Model training, evaluation, and registry modules.

Modules:
    - training: Logistic regression training with cross-validation
    - evaluation: Model performance metrics and analysis
    - registry: MLflow model registration and management
"""

from .training import (
    train_logistic_regression,
    train_churn_models,
    cross_validate_model,
)
from .evaluation import (
    evaluate_model,
    calculate_metrics,
    generate_classification_report,
)
from .registry import (
    register_model,
    load_model,
    get_latest_model_version,
)
