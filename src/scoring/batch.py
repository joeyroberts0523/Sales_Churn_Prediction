"""
Batch scoring module for generating predictions at scale.

Implements:
- Loading registered models
- Scoring all customers
- Generating prediction records per contract schema
- Data freshness validation before scoring
"""

import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from ..utils.config import get_config
from ..utils.logging import get_logger, ScoringLogger
from ..data.validation import validate_data_freshness

logger = get_logger(__name__)


def score_customers(
    model,
    scaler,
    features_df: pd.DataFrame,
    feature_names: List[str]
) -> pd.DataFrame:
    """
    Score customers using a trained model.
    
    Args:
        model: Trained sklearn model
        scaler: Fitted scaler for features
        features_df: Feature matrix with customer_id
        feature_names: List of feature columns to use
        
    Returns:
        DataFrame with customer_id and churn_probability
    """
    scoring_logger = ScoringLogger()
    scoring_logger.log_batch_start(len(features_df))
    
    start_time = datetime.now()
    
    # Extract features in correct order
    X = features_df[feature_names].copy()
    
    # Handle missing features
    for col in feature_names:
        if col not in X.columns:
            logger.warning(f"Feature {col} missing, filling with 0")
            X[col] = 0
    
    # Scale features
    X_scaled = scaler.transform(X)
    
    # Generate predictions
    probabilities = model.predict_proba(X_scaled)[:, 1]
    
    # Create result DataFrame
    result = pd.DataFrame({
        'customer_id': features_df['customer_id'],
        'churn_probability': probabilities
    })
    
    duration = (datetime.now() - start_time).total_seconds()
    scoring_logger.log_batch_complete(len(result), duration)
    
    return result


def score_all_buckets(
    model_results: Dict[str, Dict[str, Any]],
    features_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Score customers for all churn buckets.
    
    Args:
        model_results: Dict from train_churn_models output
        features_df: Feature matrix with customer_id
        
    Returns:
        DataFrame with predictions for all buckets
    """
    all_predictions = []
    
    for bucket_name, results in model_results.items():
        model = results['model']
        scaler = results['scaler']
        feature_names = results['feature_names']
        
        predictions = score_customers(model, scaler, features_df, feature_names)
        predictions['churn_bucket'] = bucket_name
        predictions['model_version'] = results.get('mlflow_run_id', 'local')
        
        all_predictions.append(predictions)
        logger.info(f"Scored {len(predictions)} customers for {bucket_name}")
    
    return pd.concat(all_predictions, ignore_index=True)


def create_prediction_records(
    predictions_df: pd.DataFrame,
    previous_predictions_df: Optional[pd.DataFrame] = None,
    prediction_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create prediction records conforming to contract schema.
    
    Args:
        predictions_df: Predictions with customer_id, churn_probability, churn_bucket
        previous_predictions_df: Optional previous predictions for change detection
        prediction_date: Date to use for predictions
        
    Returns:
        DataFrame matching contracts/prediction-output.json schema
    """
    from .risk_tiers import classify_risk_tier, detect_threshold_crossings
    
    if prediction_date is None:
        prediction_date = datetime.now().date()
    
    config = get_config()
    
    # Add risk tier classification
    predictions_df = predictions_df.copy()
    predictions_df['risk_tier'] = predictions_df['churn_probability'].apply(classify_risk_tier)
    
    # Generate unique IDs
    predictions_df['prediction_id'] = [str(uuid.uuid4()) for _ in range(len(predictions_df))]
    
    # Add timestamp columns
    predictions_df['prediction_date'] = prediction_date
    predictions_df['created_at'] = datetime.now()
    
    # Calculate probability change if previous predictions available
    if previous_predictions_df is not None and len(previous_predictions_df) > 0:
        prev = previous_predictions_df[['customer_id', 'churn_bucket', 'churn_probability']].copy()
        prev.columns = ['customer_id', 'churn_bucket', 'previous_probability']
        
        predictions_df = predictions_df.merge(
            prev, on=['customer_id', 'churn_bucket'], how='left'
        )
        predictions_df['probability_change'] = (
            predictions_df['churn_probability'] - predictions_df['previous_probability']
        )
        
        # Detect threshold crossings for alerts
        predictions_df['alert_triggered'] = detect_threshold_crossings(
            predictions_df['churn_probability'],
            predictions_df['previous_probability']
        )
    else:
        predictions_df['previous_probability'] = None
        predictions_df['probability_change'] = None
        predictions_df['alert_triggered'] = False
    
    # Select final columns per contract
    output_columns = [
        'prediction_id',
        'customer_id',
        'prediction_date',
        'model_version',
        'churn_bucket',
        'churn_probability',
        'risk_tier',
        'previous_probability',
        'probability_change',
        'alert_triggered',
        'created_at'
    ]
    
    return predictions_df[output_columns]


def run_batch_scoring_pipeline(
    features_df: pd.DataFrame,
    model_results: Dict[str, Dict[str, Any]],
    previous_predictions_df: Optional[pd.DataFrame] = None,
    validate_freshness: bool = True,
    timestamp_column: str = 'updated_at'
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Run complete batch scoring pipeline with validation.
    
    Args:
        features_df: Feature matrix with customer_id
        model_results: Trained model results
        previous_predictions_df: Previous predictions for change detection
        validate_freshness: Whether to validate data freshness
        timestamp_column: Column for freshness check
        
    Returns:
        Tuple of (predictions DataFrame, pipeline metadata)
    """
    config = get_config()
    pipeline_start = datetime.now()
    metadata = {'start_time': pipeline_start.isoformat()}
    
    # Validate data freshness
    if validate_freshness and timestamp_column in features_df.columns:
        freshness_result = validate_data_freshness(features_df, timestamp_column)
        if not freshness_result.passed:
            raise ValueError(f"Data freshness check failed: {freshness_result.message}")
        metadata['freshness_check'] = freshness_result.details
    
    # Score all buckets
    predictions = score_all_buckets(model_results, features_df)
    metadata['customers_scored'] = predictions['customer_id'].nunique()
    metadata['total_predictions'] = len(predictions)
    
    # Create formatted records
    records = create_prediction_records(predictions, previous_predictions_df)
    
    # Calculate risk distribution per bucket
    risk_dist = records.groupby(['churn_bucket', 'risk_tier']).size().unstack(fill_value=0)
    metadata['risk_distribution'] = risk_dist.to_dict()
    
    # Count alerts
    metadata['alerts_triggered'] = int(records['alert_triggered'].sum())
    
    pipeline_end = datetime.now()
    metadata['end_time'] = pipeline_end.isoformat()
    metadata['duration_seconds'] = (pipeline_end - pipeline_start).total_seconds()
    
    logger.info(f"Pipeline complete: {metadata['total_predictions']} predictions, "
                f"{metadata['alerts_triggered']} alerts, "
                f"{metadata['duration_seconds']:.2f}s")
    
    return records, metadata


def save_predictions_to_lakehouse(
    predictions_df: pd.DataFrame,
    table_name: str = 'predictions',
    mode: str = 'append',
    spark=None
):
    """
    Save predictions to Lakehouse Delta table.
    
    Args:
        predictions_df: Predictions to save
        table_name: Target table name
        mode: Write mode ('append', 'overwrite')
        spark: Optional Spark session
    """
    config = get_config()
    
    if spark is None:
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()
        except ImportError:
            logger.warning("PySpark not available, cannot save to Lakehouse")
            return
    
    try:
        # Convert to Spark DataFrame
        spark_df = spark.createDataFrame(predictions_df)
        
        # Write to Delta table
        table_path = f"Tables/{table_name}"
        spark_df.write.format("delta").mode(mode).save(table_path)
        
        logger.info(f"Saved {len(predictions_df)} predictions to {table_path}")
    except Exception as e:
        logger.error(f"Failed to save predictions: {e}")
        raise
