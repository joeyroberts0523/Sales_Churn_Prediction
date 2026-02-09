"""
Data processing modules for the Churn Prediction project.

Modules:
    - ingestion: Load data from Lakehouse and external sources
    - preprocessing: Clean, transform, and prepare data for modeling
    - validation: Data quality checks and freshness validation
"""

from .ingestion import (
    load_customers,
    load_customer_activity,
    load_churn_events,
    load_features,
    load_predictions,
)
from .preprocessing import (
    handle_missing_values,
    encode_categorical,
    scale_numeric,
    create_label,
)
from .validation import (
    validate_data_freshness,
    validate_data_quality,
    run_expectations,
)
