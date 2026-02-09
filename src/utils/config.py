"""
Configuration management for the Churn Prediction project.

Centralizes all configuration values including:
- Lakehouse connection settings
- Model hyperparameters
- Churn bucket definitions
- Data freshness thresholds
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os


@dataclass
class ChurnBucketConfig:
    """Configuration for churn bucket definitions."""
    
    # Inactivity-based churn thresholds (days)
    BUCKET_30_DAYS: int = 30
    BUCKET_60_DAYS: int = 60
    BUCKET_90_DAYS: int = 90
    
    # Bucket names for model identification
    BUCKET_NAMES: List[str] = field(default_factory=lambda: [
        "churn_30d",
        "churn_60d", 
        "churn_90d",
        "churn_explicit"
    ])


@dataclass
class ModelConfig:
    """Configuration for model training."""
    
    # Logistic Regression hyperparameters
    SOLVER: str = "lbfgs"
    MAX_ITER: int = 1000
    CLASS_WEIGHT: str = "balanced"  # Handle class imbalance
    RANDOM_STATE: int = 42
    
    # Cross-validation settings
    CV_FOLDS: int = 5
    
    # Performance thresholds
    MIN_AUC_ROC: float = 0.70  # Minimum acceptable AUC-ROC
    
    # MLflow settings
    EXPERIMENT_NAME: str = "churn-prediction"
    REGISTERED_MODEL_PREFIX: str = "churn_model"


@dataclass
class RiskTierConfig:
    """Configuration for risk tier classification."""
    
    # Probability thresholds for risk tiers
    CRITICAL_THRESHOLD: float = 0.80
    HIGH_THRESHOLD: float = 0.60
    MEDIUM_THRESHOLD: float = 0.40
    # Below MEDIUM_THRESHOLD = Low risk
    
    TIER_NAMES: Dict[str, str] = field(default_factory=lambda: {
        "critical": "Critical",
        "high": "High",
        "medium": "Medium",
        "low": "Low"
    })


@dataclass
class DataConfig:
    """Configuration for data processing."""
    
    # Data freshness threshold (days)
    MAX_DATA_AGE_DAYS: int = 7
    
    # Historical data window (months)
    HISTORY_MONTHS: int = 18
    
    # Refresh frequency
    REFRESH_FREQUENCY: str = "weekly"
    
    # Lakehouse settings
    LAKEHOUSE_NAME: str = "churn_lakehouse"
    
    # Table names
    TABLES: Dict[str, str] = field(default_factory=lambda: {
        "customers": "customers",
        "customer_activity": "customer_activity",
        "churn_events": "churn_events",
        "features": "features",
        "predictions": "predictions",
        "model_metrics": "model_metrics",
        "feature_importance": "feature_importance",
        "policies": "policies",
        "policy_cohorts": "policy_cohorts"
    })


@dataclass
class Config:
    """Main configuration class aggregating all settings."""
    
    churn_buckets: ChurnBucketConfig = field(default_factory=ChurnBucketConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    risk_tiers: RiskTierConfig = field(default_factory=RiskTierConfig)
    data: DataConfig = field(default_factory=DataConfig)
    
    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENV", "development"))
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        Config: The configuration instance (singleton pattern)
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None
