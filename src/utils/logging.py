"""
Structured logging setup for the Churn Prediction project.

Provides consistent logging across all modules with:
- Structured log format for parsing
- Configurable log levels
- Integration with Fabric notebooks
"""

import logging
import sys
from datetime import datetime
from typing import Optional


# Default log format with timestamp, level, module, and message
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (default: structured format)
        date_format: Custom date format (default: ISO-like format)
        log_file: Optional file path for logging to file
    """
    fmt = format_string or DEFAULT_FORMAT
    datefmt = date_format or DEFAULT_DATE_FORMAT
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("mlflow").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


class ModelTrainingLogger:
    """
    Specialized logger for model training operations.
    
    Provides structured logging for:
    - Training progress
    - Metric tracking
    - Model registration events
    """
    
    def __init__(self, model_name: str):
        self.logger = get_logger(f"training.{model_name}")
        self.model_name = model_name
        self.start_time: Optional[datetime] = None
    
    def start_training(self, n_samples: int, n_features: int) -> None:
        """Log training start with dataset info."""
        self.start_time = datetime.now()
        self.logger.info(
            f"Starting training | model={self.model_name} | "
            f"samples={n_samples} | features={n_features}"
        )
    
    def log_fold(self, fold: int, train_score: float, val_score: float) -> None:
        """Log cross-validation fold results."""
        self.logger.info(
            f"CV Fold {fold} | model={self.model_name} | "
            f"train_auc={train_score:.4f} | val_auc={val_score:.4f}"
        )
    
    def log_metrics(self, metrics: dict) -> None:
        """Log final model metrics."""
        metrics_str = " | ".join(f"{k}={v:.4f}" for k, v in metrics.items())
        self.logger.info(f"Final metrics | model={self.model_name} | {metrics_str}")
    
    def end_training(self, success: bool = True) -> None:
        """Log training completion with duration."""
        if self.start_time:
            duration = datetime.now() - self.start_time
            status = "SUCCESS" if success else "FAILED"
            self.logger.info(
                f"Training {status} | model={self.model_name} | "
                f"duration={duration.total_seconds():.2f}s"
            )


class ScoringLogger:
    """
    Specialized logger for batch scoring operations.
    """
    
    def __init__(self):
        self.logger = get_logger("scoring")
    
    def log_batch_start(self, n_customers: int) -> None:
        """Log batch scoring start."""
        self.logger.info(f"Starting batch scoring | customers={n_customers}")
    
    def log_batch_complete(self, n_scored: int, duration_seconds: float) -> None:
        """Log batch scoring completion."""
        rate = n_scored / duration_seconds if duration_seconds > 0 else 0
        self.logger.info(
            f"Batch scoring complete | scored={n_scored} | "
            f"duration={duration_seconds:.2f}s | rate={rate:.1f}/sec"
        )
    
    def log_risk_distribution(self, distribution: dict) -> None:
        """Log distribution of risk tiers."""
        dist_str = " | ".join(f"{k}={v}" for k, v in distribution.items())
        self.logger.info(f"Risk distribution | {dist_str}")
