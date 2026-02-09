"""
Data preprocessing module for cleaning and transforming data.

Provides functions for:
- Missing value handling
- Categorical encoding
- Numeric scaling
- Label creation for churn buckets
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime, timedelta

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def handle_missing_values(
    df: pd.DataFrame,
    numeric_strategy: str = "median",
    categorical_strategy: str = "most_frequent",
    columns_to_drop_threshold: float = 0.5
) -> pd.DataFrame:
    """
    Handle missing values in the dataset.
    
    Args:
        df: Input DataFrame
        numeric_strategy: Strategy for numeric columns ('median', 'mean', 'constant')
        categorical_strategy: Strategy for categorical columns ('most_frequent', 'constant')
        columns_to_drop_threshold: Drop columns with missing ratio above this threshold
        
    Returns:
        DataFrame with missing values handled
    """
    df = df.copy()
    
    # Drop columns with too many missing values
    missing_ratio = df.isnull().sum() / len(df)
    cols_to_drop = missing_ratio[missing_ratio > columns_to_drop_threshold].index.tolist()
    
    if cols_to_drop:
        logger.warning(f"Dropping columns with >{columns_to_drop_threshold*100}% missing: {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)
    
    # Separate numeric and categorical columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    # Impute numeric columns
    if numeric_cols:
        numeric_imputer = SimpleImputer(strategy=numeric_strategy)
        df[numeric_cols] = numeric_imputer.fit_transform(df[numeric_cols])
        logger.info(f"Imputed {len(numeric_cols)} numeric columns with {numeric_strategy}")
    
    # Impute categorical columns
    if categorical_cols:
        categorical_imputer = SimpleImputer(strategy=categorical_strategy, fill_value="Unknown")
        df[categorical_cols] = categorical_imputer.fit_transform(df[categorical_cols])
        logger.info(f"Imputed {len(categorical_cols)} categorical columns with {categorical_strategy}")
    
    return df


def encode_categorical(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = "onehot",
    drop_first: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Union[LabelEncoder, List[str]]]]:
    """
    Encode categorical variables.
    
    Args:
        df: Input DataFrame
        columns: List of columns to encode (auto-detect if None)
        method: Encoding method ('onehot', 'label')
        drop_first: For one-hot, drop first category to avoid multicollinearity
        
    Returns:
        Tuple of (encoded DataFrame, encoding info for inverse transform)
    """
    df = df.copy()
    encoding_info = {}
    
    if columns is None:
        columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if not columns:
        logger.info("No categorical columns to encode")
        return df, encoding_info
    
    if method == "onehot":
        # One-hot encoding
        df = pd.get_dummies(df, columns=columns, drop_first=drop_first)
        encoding_info["method"] = "onehot"
        encoding_info["columns"] = columns
        encoding_info["drop_first"] = drop_first
        logger.info(f"One-hot encoded {len(columns)} columns, resulting in {len(df.columns)} total columns")
        
    elif method == "label":
        # Label encoding
        for col in columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoding_info[col] = le
        logger.info(f"Label encoded {len(columns)} columns")
    
    return df, encoding_info


def scale_numeric(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = "standard",
    fit_scaler: Optional[StandardScaler] = None
) -> Tuple[pd.DataFrame, StandardScaler]:
    """
    Scale numeric features.
    
    Args:
        df: Input DataFrame
        columns: List of columns to scale (auto-detect if None)
        method: Scaling method ('standard', 'minmax')
        fit_scaler: Pre-fitted scaler for inference (fits new if None)
        
    Returns:
        Tuple of (scaled DataFrame, fitted scaler)
    """
    df = df.copy()
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if not columns:
        logger.info("No numeric columns to scale")
        return df, StandardScaler()
    
    if fit_scaler is None:
        scaler = StandardScaler()
        df[columns] = scaler.fit_transform(df[columns])
        logger.info(f"Fitted and applied StandardScaler to {len(columns)} columns")
    else:
        scaler = fit_scaler
        df[columns] = scaler.transform(df[columns])
        logger.info(f"Applied pre-fitted scaler to {len(columns)} columns")
    
    return df, scaler


def create_label(
    customers_df: pd.DataFrame,
    activity_df: pd.DataFrame,
    churn_events_df: pd.DataFrame,
    reference_date: Optional[datetime] = None,
    bucket_type: str = "churn_30d"
) -> pd.DataFrame:
    """
    Create churn labels based on bucket definitions.
    
    Churn Buckets:
    - churn_30d: No activity in >30 days
    - churn_60d: No activity in >60 days  
    - churn_90d: No activity in >90 days
    - churn_explicit: Explicit cancellation/churn event
    
    Args:
        customers_df: Customer master data
        activity_df: Customer activity data with activity_date column
        churn_events_df: Explicit churn events
        reference_date: Date to calculate inactivity from (default: today)
        bucket_type: Which churn bucket to create labels for
        
    Returns:
        DataFrame with customer_id and label columns
    """
    config = get_config()
    
    if reference_date is None:
        reference_date = datetime.now()
    
    logger.info(f"Creating labels for bucket: {bucket_type} as of {reference_date.date()}")
    
    # Start with all customers
    labels_df = customers_df[["customer_id"]].copy()
    labels_df["label"] = 0  # Default: not churned
    
    if bucket_type == "churn_explicit":
        # Explicit churn: customer has an explicit cancellation event
        if "customer_id" in churn_events_df.columns:
            churned_ids = churn_events_df[
                churn_events_df["churn_type"] == "explicit"
            ]["customer_id"].unique()
            labels_df.loc[labels_df["customer_id"].isin(churned_ids), "label"] = 1
    else:
        # Inactivity-based churn
        threshold_map = {
            "churn_30d": config.churn_buckets.BUCKET_30_DAYS,
            "churn_60d": config.churn_buckets.BUCKET_60_DAYS,
            "churn_90d": config.churn_buckets.BUCKET_90_DAYS,
        }
        threshold_days = threshold_map.get(bucket_type, 30)
        
        # Calculate last activity date per customer
        if "activity_date" in activity_df.columns and "customer_id" in activity_df.columns:
            activity_df = activity_df.copy()
            activity_df["activity_date"] = pd.to_datetime(activity_df["activity_date"])
            
            last_activity = activity_df.groupby("customer_id")["activity_date"].max().reset_index()
            last_activity.columns = ["customer_id", "last_activity_date"]
            
            # Calculate days since last activity
            last_activity["days_inactive"] = (reference_date - last_activity["last_activity_date"]).dt.days
            
            # Merge with labels
            labels_df = labels_df.merge(last_activity, on="customer_id", how="left")
            
            # Mark as churned if inactive for longer than threshold
            labels_df.loc[labels_df["days_inactive"] > threshold_days, "label"] = 1
            
            # Customers with no activity record are considered churned
            labels_df.loc[labels_df["days_inactive"].isna(), "label"] = 1
            
            labels_df = labels_df[["customer_id", "label"]]
    
    churn_rate = labels_df["label"].mean() * 100
    logger.info(f"Label distribution: {churn_rate:.2f}% churned, {100-churn_rate:.2f}% retained")
    
    return labels_df


def create_feature_matrix(
    customers_df: pd.DataFrame,
    activity_df: pd.DataFrame,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create feature matrix from raw data.
    
    Features created:
    - tenure_days: Days since customer start date
    - days_since_last_activity: Days since most recent activity
    - total_activities: Total number of activity events
    - activity_frequency: Activities per month
    - purchase_count: Number of purchases (if available)
    - support_ticket_count: Number of support tickets (if available)
    
    Args:
        customers_df: Customer master data
        activity_df: Customer activity data
        reference_date: Reference date for calculations
        
    Returns:
        Feature matrix DataFrame
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    logger.info(f"Creating feature matrix as of {reference_date.date()}")
    
    # Start with customer base
    features = customers_df[["customer_id"]].copy()
    
    # Tenure
    if "start_date" in customers_df.columns:
        customers_df = customers_df.copy()
        customers_df["start_date"] = pd.to_datetime(customers_df["start_date"])
        features["tenure_days"] = (reference_date - customers_df["start_date"]).dt.days
    
    # Activity-based features
    if "customer_id" in activity_df.columns and "activity_date" in activity_df.columns:
        activity_df = activity_df.copy()
        activity_df["activity_date"] = pd.to_datetime(activity_df["activity_date"])
        
        # Aggregate activity metrics
        activity_agg = activity_df.groupby("customer_id").agg(
            last_activity_date=("activity_date", "max"),
            total_activities=("activity_date", "count"),
            first_activity_date=("activity_date", "min")
        ).reset_index()
        
        # Days since last activity
        activity_agg["days_since_last_activity"] = (
            reference_date - activity_agg["last_activity_date"]
        ).dt.days
        
        # Activity frequency (per month)
        activity_agg["activity_span_days"] = (
            activity_agg["last_activity_date"] - activity_agg["first_activity_date"]
        ).dt.days
        activity_agg["activity_span_days"] = activity_agg["activity_span_days"].clip(lower=1)
        activity_agg["activity_frequency"] = (
            activity_agg["total_activities"] / (activity_agg["activity_span_days"] / 30)
        )
        
        # Merge with features
        features = features.merge(
            activity_agg[["customer_id", "days_since_last_activity", "total_activities", "activity_frequency"]],
            on="customer_id",
            how="left"
        )
    
    # Activity type counts (if available)
    if "activity_type" in activity_df.columns:
        activity_pivot = activity_df.groupby(
            ["customer_id", "activity_type"]
        ).size().unstack(fill_value=0)
        activity_pivot.columns = [f"activity_{col}_count" for col in activity_pivot.columns]
        activity_pivot = activity_pivot.reset_index()
        
        features = features.merge(activity_pivot, on="customer_id", how="left")
    
    # Fill missing values for customers with no activity
    features = features.fillna({
        "days_since_last_activity": 9999,  # Large number indicating no activity
        "total_activities": 0,
        "activity_frequency": 0
    })
    
    logger.info(f"Created feature matrix with {len(features)} rows and {len(features.columns)-1} features")
    
    return features


def prepare_training_data(
    features_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Prepare final training and test datasets.
    
    Args:
        features_df: Feature matrix with customer_id
        labels_df: Labels with customer_id and label
        test_size: Proportion for test set
        random_state: Random seed for reproducibility
        
    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    from sklearn.model_selection import train_test_split
    
    # Merge features and labels
    df = features_df.merge(labels_df, on="customer_id", how="inner")
    
    # Separate features and target
    X = df.drop(columns=["customer_id", "label"])
    y = df["label"]
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    logger.info(f"Training set: {len(X_train)} samples, Test set: {len(X_test)} samples")
    logger.info(f"Class balance - Train: {y_train.mean():.2%} positive, Test: {y_test.mean():.2%} positive")
    
    return X_train, X_test, y_train, y_test
