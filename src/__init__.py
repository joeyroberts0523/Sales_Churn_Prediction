"""
Sales Churn Prediction Package

A Microsoft Fabric-based logistic regression solution for predicting customer churn
and identifying key churn drivers.

Modules:
    - data: Data ingestion, preprocessing, and validation
    - features: Feature engineering and selection
    - models: Model training, evaluation, and registry
    - scoring: Batch scoring and risk tier classification
    - reporting: Feature importance and policy efficacy reporting
    - utils: Configuration and logging utilities
"""

__version__ = "0.1.0"
__author__ = "Sales Analytics Team"

from . import utils
