"""
Feature engineering module for creating predictive features.

Creates features from raw customer and activity data including:
- Tenure and lifecycle features
- Activity and engagement features
- Recency and frequency features
- Trend and change features
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def create_tenure_features(
    customers_df: pd.DataFrame,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create tenure-related features from customer data.
    
    Features created:
    - tenure_days: Days since start_date
    - tenure_months: Months since start_date
    - tenure_bucket: Categorical tenure bucket
    
    Args:
        customers_df: Customer master data with start_date
        reference_date: Date to calculate tenure from
        
    Returns:
        DataFrame with customer_id and tenure features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    df = customers_df[["customer_id"]].copy()
    
    if "start_date" in customers_df.columns:
        customers_df = customers_df.copy()
        customers_df["start_date"] = pd.to_datetime(customers_df["start_date"])
        
        # Tenure in days
        df["tenure_days"] = (reference_date - customers_df["start_date"]).dt.days
        df["tenure_days"] = df["tenure_days"].clip(lower=0)
        
        # Tenure in months
        df["tenure_months"] = df["tenure_days"] / 30.44  # Average days per month
        
        # Tenure bucket
        df["tenure_bucket"] = pd.cut(
            df["tenure_months"],
            bins=[0, 3, 6, 12, 24, float('inf')],
            labels=["0-3mo", "3-6mo", "6-12mo", "1-2yr", "2yr+"]
        )
    else:
        logger.warning("start_date not found in customers_df, setting tenure to 0")
        df["tenure_days"] = 0
        df["tenure_months"] = 0
        df["tenure_bucket"] = "unknown"
    
    logger.info(f"Created tenure features for {len(df)} customers")
    return df


def create_activity_features(
    activity_df: pd.DataFrame,
    customer_ids: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create activity-based features from activity data.
    
    Features created:
    - total_activities: Total activity count
    - activity_frequency: Activities per month
    - purchase_count: Number of purchase activities
    - support_ticket_count: Number of support tickets
    - login_count: Number of logins
    - activity_days: Unique days with activity
    
    Args:
        activity_df: Activity data with customer_id, activity_date, activity_type
        customer_ids: List of customer IDs to process (all if None)
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_id and activity features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    config = get_config()
    history_cutoff = reference_date - timedelta(days=config.data.HISTORY_MONTHS * 30)
    
    # Filter to history window
    activity_df = activity_df.copy()
    activity_df["activity_date"] = pd.to_datetime(activity_df["activity_date"])
    activity_df = activity_df[activity_df["activity_date"] >= history_cutoff]
    
    if customer_ids is not None:
        activity_df = activity_df[activity_df["customer_id"].isin(customer_ids)]
    
    # Aggregate by customer
    agg_funcs = {
        "activity_date": ["count", "nunique", "min", "max"]
    }
    
    activity_agg = activity_df.groupby("customer_id").agg(agg_funcs)
    activity_agg.columns = ["total_activities", "activity_days", "first_activity", "last_activity"]
    activity_agg = activity_agg.reset_index()
    
    # Activity frequency (per month)
    activity_span = (activity_agg["last_activity"] - activity_agg["first_activity"]).dt.days
    activity_span = activity_span.clip(lower=1)  # Avoid division by zero
    activity_agg["activity_frequency"] = activity_agg["total_activities"] / (activity_span / 30.44)
    
    # Activity type counts
    if "activity_type" in activity_df.columns:
        type_counts = activity_df.groupby(["customer_id", "activity_type"]).size().unstack(fill_value=0)
        
        # Extract common activity types
        if "purchase" in type_counts.columns:
            activity_agg = activity_agg.merge(
                type_counts[["purchase"]].rename(columns={"purchase": "purchase_count"}).reset_index(),
                on="customer_id", how="left"
            )
        else:
            activity_agg["purchase_count"] = 0
            
        if "support_ticket" in type_counts.columns:
            activity_agg = activity_agg.merge(
                type_counts[["support_ticket"]].rename(columns={"support_ticket": "support_ticket_count"}).reset_index(),
                on="customer_id", how="left"
            )
        else:
            activity_agg["support_ticket_count"] = 0
            
        if "login" in type_counts.columns:
            activity_agg = activity_agg.merge(
                type_counts[["login"]].rename(columns={"login": "login_count"}).reset_index(),
                on="customer_id", how="left"
            )
        else:
            activity_agg["login_count"] = 0
    
    # Select final features
    feature_cols = ["customer_id", "total_activities", "activity_days", "activity_frequency",
                    "purchase_count", "support_ticket_count", "login_count"]
    feature_cols = [c for c in feature_cols if c in activity_agg.columns]
    
    df = activity_agg[feature_cols].copy()
    df = df.fillna(0)
    
    logger.info(f"Created activity features for {len(df)} customers")
    return df


def create_recency_features(
    activity_df: pd.DataFrame,
    customer_ids: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create recency-based features from activity data.
    
    Features created:
    - days_since_last_activity: Days since most recent activity
    - days_since_last_purchase: Days since most recent purchase
    - days_since_last_login: Days since most recent login
    - login_count_30d: Logins in last 30 days
    - login_count_60d: Logins in last 60 days
    - login_count_90d: Logins in last 90 days
    
    Args:
        activity_df: Activity data
        customer_ids: List of customer IDs to process
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_id and recency features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    activity_df = activity_df.copy()
    activity_df["activity_date"] = pd.to_datetime(activity_df["activity_date"])
    
    if customer_ids is not None:
        activity_df = activity_df[activity_df["customer_id"].isin(customer_ids)]
    
    # Days since last activity (any type)
    last_activity = activity_df.groupby("customer_id")["activity_date"].max().reset_index()
    last_activity.columns = ["customer_id", "last_activity_date"]
    last_activity["days_since_last_activity"] = (
        reference_date - last_activity["last_activity_date"]
    ).dt.days
    
    df = last_activity[["customer_id", "days_since_last_activity"]].copy()
    
    # Days since last purchase
    if "activity_type" in activity_df.columns:
        purchases = activity_df[activity_df["activity_type"] == "purchase"]
        if len(purchases) > 0:
            last_purchase = purchases.groupby("customer_id")["activity_date"].max().reset_index()
            last_purchase.columns = ["customer_id", "last_purchase_date"]
            last_purchase["days_since_last_purchase"] = (
                reference_date - last_purchase["last_purchase_date"]
            ).dt.days
            df = df.merge(last_purchase[["customer_id", "days_since_last_purchase"]], 
                         on="customer_id", how="left")
        
        # Days since last login
        logins = activity_df[activity_df["activity_type"] == "login"]
        if len(logins) > 0:
            last_login = logins.groupby("customer_id")["activity_date"].max().reset_index()
            last_login.columns = ["customer_id", "last_login_date"]
            last_login["days_since_last_login"] = (
                reference_date - last_login["last_login_date"]
            ).dt.days
            df = df.merge(last_login[["customer_id", "days_since_last_login"]], 
                         on="customer_id", how="left")
            
            # Login counts by time window
            for days in [30, 60, 90]:
                cutoff = reference_date - timedelta(days=days)
                recent_logins = logins[logins["activity_date"] >= cutoff]
                login_counts = recent_logins.groupby("customer_id").size().reset_index()
                login_counts.columns = ["customer_id", f"login_count_{days}d"]
                df = df.merge(login_counts, on="customer_id", how="left")
    
    # Fill missing values
    df = df.fillna({
        "days_since_last_activity": 9999,
        "days_since_last_purchase": 9999,
        "days_since_last_login": 9999,
        "login_count_30d": 0,
        "login_count_60d": 0,
        "login_count_90d": 0
    })
    
    logger.info(f"Created recency features for {len(df)} customers")
    return df


def create_trend_features(
    activity_df: pd.DataFrame,
    customer_ids: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create trend-based features comparing recent vs historical activity.
    
    Features created:
    - activity_trend: Ratio of last 30d activity to previous 30d
    - engagement_change: Change in engagement score
    
    Args:
        activity_df: Activity data
        customer_ids: List of customer IDs to process
        reference_date: Reference date for calculations
        
    Returns:
        DataFrame with customer_id and trend features
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    activity_df = activity_df.copy()
    activity_df["activity_date"] = pd.to_datetime(activity_df["activity_date"])
    
    if customer_ids is not None:
        activity_df = activity_df[activity_df["customer_id"].isin(customer_ids)]
    
    # Define time windows
    cutoff_30d = reference_date - timedelta(days=30)
    cutoff_60d = reference_date - timedelta(days=60)
    
    # Recent period (last 30 days)
    recent = activity_df[(activity_df["activity_date"] >= cutoff_30d) & 
                         (activity_df["activity_date"] < reference_date)]
    recent_counts = recent.groupby("customer_id").size().reset_index()
    recent_counts.columns = ["customer_id", "recent_activity"]
    
    # Previous period (30-60 days ago)
    previous = activity_df[(activity_df["activity_date"] >= cutoff_60d) & 
                          (activity_df["activity_date"] < cutoff_30d)]
    previous_counts = previous.groupby("customer_id").size().reset_index()
    previous_counts.columns = ["customer_id", "previous_activity"]
    
    # Merge and calculate trend
    df = recent_counts.merge(previous_counts, on="customer_id", how="outer").fillna(0)
    
    # Activity trend (ratio, with smoothing to avoid division by zero)
    df["activity_trend"] = (df["recent_activity"] + 1) / (df["previous_activity"] + 1)
    
    # Engagement change (difference)
    df["activity_change"] = df["recent_activity"] - df["previous_activity"]
    
    # Select final features
    df = df[["customer_id", "activity_trend", "activity_change"]]
    
    logger.info(f"Created trend features for {len(df)} customers")
    return df


def create_all_features(
    customers_df: pd.DataFrame,
    activity_df: pd.DataFrame,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Create all features by combining feature creation functions.
    
    Args:
        customers_df: Customer master data
        activity_df: Activity data
        reference_date: Reference date for calculations
        
    Returns:
        Complete feature matrix with customer_id
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    logger.info(f"Creating all features as of {reference_date.date()}")
    
    # Start with customer IDs
    customer_ids = customers_df["customer_id"].tolist()
    features = customers_df[["customer_id"]].copy()
    
    # Add tenure features
    tenure_features = create_tenure_features(customers_df, reference_date)
    features = features.merge(tenure_features, on="customer_id", how="left")
    
    # Add activity features
    activity_features = create_activity_features(activity_df, customer_ids, reference_date)
    features = features.merge(activity_features, on="customer_id", how="left")
    
    # Add recency features
    recency_features = create_recency_features(activity_df, customer_ids, reference_date)
    features = features.merge(recency_features, on="customer_id", how="left")
    
    # Add trend features
    trend_features = create_trend_features(activity_df, customer_ids, reference_date)
    features = features.merge(trend_features, on="customer_id", how="left")
    
    # Fill missing values for customers with no activity
    numeric_cols = features.select_dtypes(include=[np.number]).columns
    features[numeric_cols] = features[numeric_cols].fillna(0)
    
    # Special handling for days_since columns (no activity = very long time)
    for col in features.columns:
        if col.startswith("days_since"):
            features[col] = features[col].replace(0, 9999)
    
    logger.info(f"Created {len(features.columns)-1} features for {len(features)} customers")
    
    return features
