"""
Data validation module for quality checks and freshness validation.

Integrates with Great Expectations for comprehensive data validation
and provides custom validation functions for churn-specific requirements.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


def validate_data_freshness(
    df: pd.DataFrame,
    timestamp_column: str = "updated_at",
    max_age_days: Optional[int] = None
) -> ValidationResult:
    """
    Validate that data is recent enough for model training/scoring.
    
    Args:
        df: DataFrame to validate
        timestamp_column: Column containing timestamps
        max_age_days: Maximum allowed age in days (uses config if None)
        
    Returns:
        ValidationResult indicating pass/fail with details
    """
    config = get_config()
    max_age = max_age_days or config.data.MAX_DATA_AGE_DAYS
    
    if timestamp_column not in df.columns:
        return ValidationResult(
            passed=False,
            message=f"Timestamp column '{timestamp_column}' not found in data",
            details={"available_columns": df.columns.tolist()}
        )
    
    # Get most recent timestamp
    df = df.copy()
    df[timestamp_column] = pd.to_datetime(df[timestamp_column])
    most_recent = df[timestamp_column].max()
    
    if pd.isna(most_recent):
        return ValidationResult(
            passed=False,
            message="No valid timestamps found in data",
            details={"column": timestamp_column}
        )
    
    # Calculate age
    age_days = (datetime.now() - most_recent).days
    
    if age_days > max_age:
        return ValidationResult(
            passed=False,
            message=f"Data is {age_days} days old, exceeds maximum of {max_age} days",
            details={
                "most_recent": most_recent.isoformat(),
                "age_days": age_days,
                "max_age_days": max_age
            }
        )
    
    logger.info(f"Data freshness OK: {age_days} days old (max: {max_age})")
    return ValidationResult(
        passed=True,
        message=f"Data is {age_days} days old, within acceptable range",
        details={
            "most_recent": most_recent.isoformat(),
            "age_days": age_days,
            "max_age_days": max_age
        }
    )


def validate_data_quality(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    max_null_ratio: float = 0.3,
    min_rows: int = 100
) -> ValidationResult:
    """
    Perform basic data quality validation.
    
    Args:
        df: DataFrame to validate
        required_columns: List of columns that must be present
        max_null_ratio: Maximum allowed null ratio per column
        min_rows: Minimum number of rows required
        
    Returns:
        ValidationResult with quality check details
    """
    issues = []
    details = {}
    
    # Check minimum rows
    if len(df) < min_rows:
        issues.append(f"Insufficient rows: {len(df)} < {min_rows}")
        details["row_count"] = len(df)
    
    # Check required columns
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing required columns: {missing_cols}")
            details["missing_columns"] = missing_cols
    
    # Check null ratios
    null_ratios = df.isnull().sum() / len(df)
    high_null_cols = null_ratios[null_ratios > max_null_ratio].to_dict()
    if high_null_cols:
        issues.append(f"High null ratio in columns: {list(high_null_cols.keys())}")
        details["high_null_columns"] = high_null_cols
    
    # Check for duplicate rows based on key columns
    if "customer_id" in df.columns:
        dup_count = df["customer_id"].duplicated().sum()
        if dup_count > 0:
            issues.append(f"Found {dup_count} duplicate customer_id values")
            details["duplicate_count"] = dup_count
    
    if issues:
        return ValidationResult(
            passed=False,
            message=f"Data quality issues found: {len(issues)} issues",
            details={"issues": issues, **details}
        )
    
    logger.info(f"Data quality OK: {len(df)} rows, {len(df.columns)} columns")
    return ValidationResult(
        passed=True,
        message="All data quality checks passed",
        details={"row_count": len(df), "column_count": len(df.columns)}
    )


def validate_feature_ranges(
    df: pd.DataFrame,
    feature_ranges: Optional[Dict[str, Tuple[float, float]]] = None
) -> ValidationResult:
    """
    Validate that feature values are within expected ranges.
    
    Args:
        df: DataFrame with features
        feature_ranges: Dict mapping column names to (min, max) tuples
        
    Returns:
        ValidationResult with range check details
    """
    if feature_ranges is None:
        # Default ranges for common features
        feature_ranges = {
            "tenure_days": (0, 10000),
            "days_since_last_activity": (0, 10000),
            "total_activities": (0, 100000),
            "activity_frequency": (0, 1000),
        }
    
    issues = []
    details = {}
    
    for col, (min_val, max_val) in feature_ranges.items():
        if col not in df.columns:
            continue
            
        actual_min = df[col].min()
        actual_max = df[col].max()
        
        if actual_min < min_val or actual_max > max_val:
            issues.append(f"{col}: values [{actual_min:.2f}, {actual_max:.2f}] outside expected [{min_val}, {max_val}]")
            details[col] = {"actual_min": actual_min, "actual_max": actual_max, "expected": (min_val, max_val)}
    
    if issues:
        return ValidationResult(
            passed=False,
            message=f"Feature range issues: {len(issues)} features out of range",
            details={"issues": issues, **details}
        )
    
    return ValidationResult(
        passed=True,
        message="All feature ranges within expected bounds",
        details=details
    )


def validate_label_distribution(
    labels: pd.Series,
    min_positive_ratio: float = 0.01,
    max_positive_ratio: float = 0.50
) -> ValidationResult:
    """
    Validate that label distribution is suitable for model training.
    
    Args:
        labels: Series of binary labels
        min_positive_ratio: Minimum acceptable positive class ratio
        max_positive_ratio: Maximum acceptable positive class ratio
        
    Returns:
        ValidationResult with distribution details
    """
    positive_ratio = labels.mean()
    
    if positive_ratio < min_positive_ratio:
        return ValidationResult(
            passed=False,
            message=f"Positive class ratio {positive_ratio:.2%} below minimum {min_positive_ratio:.2%}",
            details={
                "positive_ratio": positive_ratio,
                "positive_count": labels.sum(),
                "total_count": len(labels)
            }
        )
    
    if positive_ratio > max_positive_ratio:
        return ValidationResult(
            passed=False,
            message=f"Positive class ratio {positive_ratio:.2%} above maximum {max_positive_ratio:.2%}",
            details={
                "positive_ratio": positive_ratio,
                "positive_count": labels.sum(),
                "total_count": len(labels)
            }
        )
    
    return ValidationResult(
        passed=True,
        message=f"Label distribution acceptable: {positive_ratio:.2%} positive",
        details={
            "positive_ratio": positive_ratio,
            "positive_count": int(labels.sum()),
            "negative_count": int(len(labels) - labels.sum())
        }
    )


# Great Expectations Integration

def run_expectations(
    df: pd.DataFrame,
    expectation_suite: str,
    checkpoint_name: Optional[str] = None
) -> ValidationResult:
    """
    Run Great Expectations validation suite on data.
    
    Args:
        df: DataFrame to validate
        expectation_suite: Name of the expectation suite to run
        checkpoint_name: Optional checkpoint name
        
    Returns:
        ValidationResult with Great Expectations results
    """
    try:
        import great_expectations as gx
        from great_expectations.data_context import FileDataContext
        
        # Initialize context (expects great_expectations directory in project root)
        context = FileDataContext(context_root_dir="tests/data_quality")
        
        # Create validator
        validator = context.sources.pandas_default.read_dataframe(df)
        
        # Run validation
        results = validator.validate(expectation_suite_name=expectation_suite)
        
        if results.success:
            logger.info(f"Great Expectations validation passed: {expectation_suite}")
            return ValidationResult(
                passed=True,
                message=f"All {len(results.results)} expectations passed",
                details={"statistics": results.statistics}
            )
        else:
            failed_expectations = [
                r.expectation_config.expectation_type 
                for r in results.results 
                if not r.success
            ]
            logger.warning(f"Great Expectations validation failed: {failed_expectations}")
            return ValidationResult(
                passed=False,
                message=f"{len(failed_expectations)} expectations failed",
                details={
                    "failed_expectations": failed_expectations,
                    "statistics": results.statistics
                }
            )
            
    except ImportError:
        logger.warning("Great Expectations not installed, skipping validation")
        return ValidationResult(
            passed=True,
            message="Great Expectations not available, validation skipped",
            details={"skipped": True}
        )
    except Exception as e:
        logger.error(f"Great Expectations validation error: {e}")
        return ValidationResult(
            passed=False,
            message=f"Validation error: {str(e)}",
            details={"error": str(e)}
        )


def run_all_validations(
    df: pd.DataFrame,
    labels: Optional[pd.Series] = None,
    timestamp_column: str = "updated_at",
    required_columns: Optional[List[str]] = None
) -> Tuple[bool, List[ValidationResult]]:
    """
    Run all validation checks on the dataset.
    
    Args:
        df: DataFrame to validate
        labels: Optional label series for distribution validation
        timestamp_column: Column for freshness check
        required_columns: Required columns for quality check
        
    Returns:
        Tuple of (all_passed, list of ValidationResults)
    """
    results = []
    
    # Data freshness
    if timestamp_column in df.columns:
        results.append(("freshness", validate_data_freshness(df, timestamp_column)))
    
    # Data quality
    results.append(("quality", validate_data_quality(df, required_columns)))
    
    # Feature ranges
    results.append(("ranges", validate_feature_ranges(df)))
    
    # Label distribution
    if labels is not None:
        results.append(("labels", validate_label_distribution(labels)))
    
    # Check overall result
    all_passed = all(r[1].passed for r in results)
    
    if all_passed:
        logger.info("All validations passed")
    else:
        failed = [r[0] for r in results if not r[1].passed]
        logger.warning(f"Validation failures: {failed}")
    
    return all_passed, [r[1] for r in results]
