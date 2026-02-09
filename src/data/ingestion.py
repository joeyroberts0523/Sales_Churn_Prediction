"""
Data ingestion module for loading data from Microsoft Fabric Lakehouse.

This module provides functions to load data from Delta tables in the Lakehouse
with support for incremental loading and data freshness validation.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _get_spark_session():
    """
    Get or create Spark session for Fabric environment.
    
    In Fabric notebooks, spark session is available globally.
    For local testing, creates a local session.
    """
    try:
        # In Fabric notebooks, spark is available globally
        from pyspark.sql import SparkSession
        return SparkSession.builder.getOrCreate()
    except ImportError:
        logger.warning("PySpark not available - running in local mode")
        return None


def _load_delta_table(table_name: str, spark=None) -> pd.DataFrame:
    """
    Load a Delta table from Lakehouse as pandas DataFrame.
    
    Args:
        table_name: Name of the table to load
        spark: Optional Spark session (uses global if not provided)
        
    Returns:
        pandas DataFrame with table contents
    """
    config = get_config()
    lakehouse = config.data.LAKEHOUSE_NAME
    
    if spark is None:
        spark = _get_spark_session()
    
    if spark is not None:
        # Fabric Lakehouse path format
        table_path = f"Tables/{table_name}"
        logger.info(f"Loading table: {table_path}")
        
        try:
            df = spark.read.format("delta").load(table_path)
            return df.toPandas()
        except Exception as e:
            logger.error(f"Failed to load {table_name}: {e}")
            raise
    else:
        # Local fallback - read from parquet if available
        logger.warning(f"Loading {table_name} from local parquet fallback")
        return pd.DataFrame()


def load_customers(
    spark=None,
    active_only: bool = True
) -> pd.DataFrame:
    """
    Load customer master data from Lakehouse.
    
    Args:
        spark: Optional Spark session
        active_only: If True, filter to active customers only
        
    Returns:
        DataFrame with customer records
    """
    config = get_config()
    table_name = config.data.TABLES["customers"]
    
    df = _load_delta_table(table_name, spark)
    
    if active_only and "is_active" in df.columns:
        df = df[df["is_active"] == True]
        logger.info(f"Filtered to {len(df)} active customers")
    
    return df


def load_customer_activity(
    spark=None,
    customer_ids: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Load customer activity data from Lakehouse.
    
    Args:
        spark: Optional Spark session
        customer_ids: Optional list to filter specific customers
        start_date: Optional start date for activity window
        end_date: Optional end date for activity window
        
    Returns:
        DataFrame with activity records
    """
    config = get_config()
    table_name = config.data.TABLES["customer_activity"]
    
    df = _load_delta_table(table_name, spark)
    
    # Apply filters
    if customer_ids is not None and "customer_id" in df.columns:
        df = df[df["customer_id"].isin(customer_ids)]
    
    if start_date is not None and "activity_date" in df.columns:
        df = df[df["activity_date"] >= start_date]
    
    if end_date is not None and "activity_date" in df.columns:
        df = df[df["activity_date"] <= end_date]
    
    logger.info(f"Loaded {len(df)} activity records")
    return df


def load_churn_events(
    spark=None,
    include_explicit_only: bool = False
) -> pd.DataFrame:
    """
    Load churn event data from Lakehouse.
    
    Args:
        spark: Optional Spark session
        include_explicit_only: If True, only return explicit cancellations
        
    Returns:
        DataFrame with churn events
    """
    config = get_config()
    table_name = config.data.TABLES["churn_events"]
    
    df = _load_delta_table(table_name, spark)
    
    if include_explicit_only and "churn_type" in df.columns:
        df = df[df["churn_type"] == "explicit"]
    
    logger.info(f"Loaded {len(df)} churn events")
    return df


def load_features(
    spark=None,
    feature_set_id: Optional[str] = None
) -> pd.DataFrame:
    """
    Load pre-computed features from Lakehouse.
    
    Args:
        spark: Optional Spark session
        feature_set_id: Optional specific feature set version to load
        
    Returns:
        DataFrame with feature vectors
    """
    config = get_config()
    table_name = config.data.TABLES["features"]
    
    df = _load_delta_table(table_name, spark)
    
    if feature_set_id is not None and "feature_set_id" in df.columns:
        df = df[df["feature_set_id"] == feature_set_id]
    
    logger.info(f"Loaded {len(df)} feature records with {len(df.columns)} columns")
    return df


def load_predictions(
    spark=None,
    model_version: Optional[str] = None,
    prediction_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Load model predictions from Lakehouse.
    
    Args:
        spark: Optional Spark session
        model_version: Optional specific model version
        prediction_date: Optional specific prediction date
        
    Returns:
        DataFrame with prediction records
    """
    config = get_config()
    table_name = config.data.TABLES["predictions"]
    
    df = _load_delta_table(table_name, spark)
    
    if model_version is not None and "model_version" in df.columns:
        df = df[df["model_version"] == model_version]
    
    if prediction_date is not None and "prediction_date" in df.columns:
        df = df[df["prediction_date"] == prediction_date]
    
    logger.info(f"Loaded {len(df)} prediction records")
    return df


def load_model_metrics(spark=None) -> pd.DataFrame:
    """Load model performance metrics from Lakehouse."""
    config = get_config()
    return _load_delta_table(config.data.TABLES["model_metrics"], spark)


def load_feature_importance(
    spark=None,
    model_version: Optional[str] = None
) -> pd.DataFrame:
    """Load feature importance scores from Lakehouse."""
    config = get_config()
    table_name = config.data.TABLES["feature_importance"]
    
    df = _load_delta_table(table_name, spark)
    
    if model_version is not None and "model_version" in df.columns:
        df = df[df["model_version"] == model_version]
    
    return df


def load_policies(spark=None) -> pd.DataFrame:
    """Load retention policies from Lakehouse."""
    config = get_config()
    return _load_delta_table(config.data.TABLES["policies"], spark)


def load_policy_cohorts(
    spark=None,
    policy_id: Optional[str] = None
) -> pd.DataFrame:
    """Load policy cohort assignments from Lakehouse."""
    config = get_config()
    table_name = config.data.TABLES["policy_cohorts"]
    
    df = _load_delta_table(table_name, spark)
    
    if policy_id is not None and "policy_id" in df.columns:
        df = df[df["policy_id"] == policy_id]
    
    return df


def get_data_freshness(table_name: str, spark=None) -> Optional[datetime]:
    """
    Get the most recent data timestamp for a table.
    
    Args:
        table_name: Name of the table to check
        spark: Optional Spark session
        
    Returns:
        Most recent timestamp or None if table is empty
    """
    df = _load_delta_table(table_name, spark)
    
    # Common timestamp columns to check
    timestamp_cols = ["updated_at", "created_at", "activity_date", "prediction_date"]
    
    for col in timestamp_cols:
        if col in df.columns:
            max_date = df[col].max()
            if pd.notna(max_date):
                return pd.to_datetime(max_date)
    
    return None
