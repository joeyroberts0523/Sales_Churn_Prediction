"""
Feature selection utilities for identifying important features.

Provides methods for:
- Variance-based filtering
- Correlation-based filtering  
- Feature importance from models
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict
from sklearn.feature_selection import VarianceThreshold

from ..utils.logging import get_logger

logger = get_logger(__name__)


def select_by_variance(
    X: pd.DataFrame,
    threshold: float = 0.01
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Remove features with variance below threshold.
    
    Args:
        X: Feature matrix
        threshold: Minimum variance to keep feature
        
    Returns:
        Tuple of (filtered DataFrame, list of removed columns)
    """
    selector = VarianceThreshold(threshold=threshold)
    
    # Get numeric columns only
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    X_numeric = X[numeric_cols]
    
    # Fit selector
    selector.fit(X_numeric)
    
    # Get mask of selected features
    mask = selector.get_support()
    selected_cols = [col for col, keep in zip(numeric_cols, mask) if keep]
    removed_cols = [col for col, keep in zip(numeric_cols, mask) if not keep]
    
    if removed_cols:
        logger.info(f"Removed {len(removed_cols)} low-variance features: {removed_cols}")
    
    # Keep selected numeric columns plus any non-numeric columns
    non_numeric_cols = [col for col in X.columns if col not in numeric_cols]
    final_cols = non_numeric_cols + selected_cols
    
    return X[final_cols], removed_cols


def select_by_correlation(
    X: pd.DataFrame,
    threshold: float = 0.95,
    method: str = "pearson"
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Remove highly correlated features (keep one of each correlated pair).
    
    Args:
        X: Feature matrix
        threshold: Correlation threshold above which to remove
        method: Correlation method ('pearson', 'spearman')
        
    Returns:
        Tuple of (filtered DataFrame, list of removed columns)
    """
    # Get numeric columns only
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    X_numeric = X[numeric_cols]
    
    # Calculate correlation matrix
    corr_matrix = X_numeric.corr(method=method).abs()
    
    # Create upper triangle mask
    upper_tri = np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    upper_corr = corr_matrix.where(upper_tri)
    
    # Find columns with correlation above threshold
    to_drop = [col for col in upper_corr.columns if any(upper_corr[col] > threshold)]
    
    if to_drop:
        logger.info(f"Removed {len(to_drop)} highly correlated features: {to_drop}")
    
    # Keep non-dropped columns
    non_numeric_cols = [col for col in X.columns if col not in numeric_cols]
    kept_numeric = [col for col in numeric_cols if col not in to_drop]
    
    return X[non_numeric_cols + kept_numeric], to_drop


def get_feature_importances(
    model,
    feature_names: List[str],
    importance_type: str = "coefficient"
) -> pd.DataFrame:
    """
    Extract feature importances from a fitted model.
    
    Args:
        model: Fitted sklearn model (LogisticRegression, etc.)
        feature_names: List of feature names
        importance_type: Type of importance ('coefficient', 'abs_coefficient')
        
    Returns:
        DataFrame with feature_name, importance, and rank columns
    """
    # Get coefficients from logistic regression
    if hasattr(model, 'coef_'):
        coefficients = model.coef_.flatten()
    else:
        raise ValueError("Model does not have coef_ attribute")
    
    # Create importance DataFrame
    importance_df = pd.DataFrame({
        'feature_name': feature_names,
        'coefficient': coefficients,
        'abs_coefficient': np.abs(coefficients)
    })
    
    # Calculate odds ratio
    importance_df['odds_ratio'] = np.exp(importance_df['coefficient'])
    
    # Rank by absolute coefficient
    importance_df = importance_df.sort_values('abs_coefficient', ascending=False)
    importance_df['importance_rank'] = range(1, len(importance_df) + 1)
    
    logger.info(f"Extracted importances for {len(feature_names)} features")
    
    return importance_df


def select_top_features(
    importance_df: pd.DataFrame,
    n_features: int = 20,
    min_abs_coefficient: float = 0.0
) -> List[str]:
    """
    Select top N features by importance.
    
    Args:
        importance_df: DataFrame from get_feature_importances
        n_features: Number of top features to select
        min_abs_coefficient: Minimum absolute coefficient to include
        
    Returns:
        List of selected feature names
    """
    # Filter by minimum coefficient
    filtered = importance_df[importance_df['abs_coefficient'] >= min_abs_coefficient]
    
    # Select top N
    top_features = filtered.head(n_features)['feature_name'].tolist()
    
    logger.info(f"Selected top {len(top_features)} features from {len(importance_df)} total")
    
    return top_features


def calculate_vif(X: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Variance Inflation Factor for features.
    
    High VIF (>5-10) indicates multicollinearity.
    
    Args:
        X: Feature matrix (numeric columns only)
        
    Returns:
        DataFrame with feature_name and vif columns
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    
    # Get numeric columns
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    X_numeric = X[numeric_cols].dropna()
    
    # Calculate VIF for each feature
    vif_data = []
    for i, col in enumerate(X_numeric.columns):
        try:
            vif = variance_inflation_factor(X_numeric.values, i)
            vif_data.append({'feature_name': col, 'vif': vif})
        except Exception as e:
            logger.warning(f"Could not calculate VIF for {col}: {e}")
            vif_data.append({'feature_name': col, 'vif': np.nan})
    
    vif_df = pd.DataFrame(vif_data)
    vif_df = vif_df.sort_values('vif', ascending=False)
    
    # Flag high VIF features
    vif_df['high_vif'] = vif_df['vif'] > 5
    
    high_vif_count = vif_df['high_vif'].sum()
    if high_vif_count > 0:
        logger.warning(f"{high_vif_count} features have VIF > 5 (potential multicollinearity)")
    
    return vif_df
