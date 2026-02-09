"""
Risk tier classification module.

Classifies customers into risk tiers based on churn probability:
- Critical: >= 80%
- High: >= 60%
- Medium: >= 40%
- Low: < 40%

Also handles threshold crossing detection for alerts.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def classify_risk_tier(probability: float) -> str:
    """
    Classify a churn probability into a risk tier.
    
    Args:
        probability: Churn probability (0-1)
        
    Returns:
        Risk tier string ('Critical', 'High', 'Medium', 'Low')
    """
    config = get_config()
    
    if probability >= config.risk_tiers.CRITICAL_THRESHOLD:
        return config.risk_tiers.TIER_NAMES['critical']
    elif probability >= config.risk_tiers.HIGH_THRESHOLD:
        return config.risk_tiers.TIER_NAMES['high']
    elif probability >= config.risk_tiers.MEDIUM_THRESHOLD:
        return config.risk_tiers.TIER_NAMES['medium']
    else:
        return config.risk_tiers.TIER_NAMES['low']


def classify_risk_tiers_batch(probabilities: pd.Series) -> pd.Series:
    """
    Classify a series of probabilities into risk tiers.
    
    Args:
        probabilities: Series of churn probabilities
        
    Returns:
        Series of risk tier classifications
    """
    return probabilities.apply(classify_risk_tier)


def get_risk_distribution(predictions_df: pd.DataFrame) -> Dict[str, int]:
    """
    Calculate distribution of risk tiers.
    
    Args:
        predictions_df: DataFrame with risk_tier column
        
    Returns:
        Dict mapping tier names to counts
    """
    if 'risk_tier' not in predictions_df.columns:
        raise ValueError("predictions_df must have 'risk_tier' column")
    
    config = get_config()
    
    # Initialize with all tiers at 0
    distribution = {name: 0 for name in config.risk_tiers.TIER_NAMES.values()}
    
    # Update with actual counts
    actual_dist = predictions_df['risk_tier'].value_counts().to_dict()
    distribution.update(actual_dist)
    
    return distribution


def detect_threshold_crossings(
    current_probabilities: pd.Series,
    previous_probabilities: pd.Series,
    threshold: float = 0.6
) -> pd.Series:
    """
    Detect customers who crossed a risk threshold.
    
    Default threshold is 0.6 (High risk), meaning customers who
    moved from below 0.6 to at or above 0.6 trigger an alert.
    
    Args:
        current_probabilities: Current churn probabilities
        previous_probabilities: Previous churn probabilities
        threshold: Threshold for crossing detection
        
    Returns:
        Boolean Series indicating threshold crossings
    """
    # Handle null previous probabilities (new customers or first run)
    previous = previous_probabilities.fillna(0)
    
    # Crossed threshold: was below, now at or above
    crossed_up = (previous < threshold) & (current_probabilities >= threshold)
    
    return crossed_up


def detect_significant_increase(
    current_probabilities: pd.Series,
    previous_probabilities: pd.Series,
    min_increase: float = 0.15
) -> pd.Series:
    """
    Detect significant probability increases.
    
    Args:
        current_probabilities: Current churn probabilities
        previous_probabilities: Previous churn probabilities
        min_increase: Minimum increase to flag (default 15 percentage points)
        
    Returns:
        Boolean Series indicating significant increases
    """
    previous = previous_probabilities.fillna(current_probabilities)
    increase = current_probabilities - previous
    
    return increase >= min_increase


def get_tier_thresholds() -> Dict[str, float]:
    """
    Get current tier threshold configuration.
    
    Returns:
        Dict mapping tier names to minimum thresholds
    """
    config = get_config()
    
    return {
        'Critical': config.risk_tiers.CRITICAL_THRESHOLD,
        'High': config.risk_tiers.HIGH_THRESHOLD,
        'Medium': config.risk_tiers.MEDIUM_THRESHOLD,
        'Low': 0.0
    }


def summarize_risk_changes(
    current_predictions: pd.DataFrame,
    previous_predictions: pd.DataFrame
) -> Dict[str, any]:
    """
    Summarize changes in risk distribution between two prediction runs.
    
    Args:
        current_predictions: Current predictions with risk_tier
        previous_predictions: Previous predictions with risk_tier
        
    Returns:
        Dict with change summary
    """
    current_dist = get_risk_distribution(current_predictions)
    previous_dist = get_risk_distribution(previous_predictions)
    
    changes = {}
    for tier in current_dist.keys():
        current_count = current_dist[tier]
        previous_count = previous_dist.get(tier, 0)
        changes[tier] = {
            'current': current_count,
            'previous': previous_count,
            'change': current_count - previous_count,
            'percent_change': ((current_count - previous_count) / max(previous_count, 1)) * 100
        }
    
    # Calculate total moving to higher risk
    merged = current_predictions.merge(
        previous_predictions[['customer_id', 'churn_bucket', 'risk_tier']],
        on=['customer_id', 'churn_bucket'],
        suffixes=('', '_prev'),
        how='inner'
    )
    
    tier_order = {'Low': 0, 'Medium': 1, 'High': 2, 'Critical': 3}
    
    if len(merged) > 0 and 'risk_tier_prev' in merged.columns:
        merged['tier_rank'] = merged['risk_tier'].map(tier_order)
        merged['tier_rank_prev'] = merged['risk_tier_prev'].map(tier_order)
        
        moved_up = (merged['tier_rank'] > merged['tier_rank_prev']).sum()
        moved_down = (merged['tier_rank'] < merged['tier_rank_prev']).sum()
        unchanged = (merged['tier_rank'] == merged['tier_rank_prev']).sum()
    else:
        moved_up = 0
        moved_down = 0
        unchanged = len(current_predictions)
    
    return {
        'tier_distribution': changes,
        'customers_moved_to_higher_risk': int(moved_up),
        'customers_moved_to_lower_risk': int(moved_down),
        'customers_unchanged': int(unchanged),
        'total_customers': len(current_predictions)
    }


def filter_by_risk_tier(
    predictions_df: pd.DataFrame,
    tiers: List[str]
) -> pd.DataFrame:
    """
    Filter predictions to specific risk tiers.
    
    Args:
        predictions_df: DataFrame with risk_tier column
        tiers: List of tier names to include
        
    Returns:
        Filtered DataFrame
    """
    if 'risk_tier' not in predictions_df.columns:
        raise ValueError("predictions_df must have 'risk_tier' column")
    
    return predictions_df[predictions_df['risk_tier'].isin(tiers)]


def get_high_risk_customers(predictions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get customers in High or Critical risk tiers.
    
    Args:
        predictions_df: DataFrame with risk_tier column
        
    Returns:
        Filtered DataFrame sorted by probability descending
    """
    high_risk = filter_by_risk_tier(predictions_df, ['High', 'Critical'])
    return high_risk.sort_values('churn_probability', ascending=False)
