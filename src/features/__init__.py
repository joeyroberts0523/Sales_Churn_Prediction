"""
Feature engineering and transformation modules.

Modules:
    - engineering: Feature transformation and creation
    - selection: Feature selection utilities
"""

from .engineering import (
    create_tenure_features,
    create_activity_features,
    create_recency_features,
    create_all_features,
)
from .selection import (
    select_by_variance,
    select_by_correlation,
    get_feature_importances,
)
