"""
Feature importance extraction and analysis module.

Provides:
- Logistic regression coefficient extraction
- Odds ratio calculation
- Statistical significance testing
- Confidence intervals
"""

import uuid
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def extract_feature_importance(
    model,
    feature_names: List[str],
    X_train: Optional[np.ndarray] = None
) -> pd.DataFrame:
    """
    Extract feature importance from a trained logistic regression model.
    
    Args:
        model: Trained LogisticRegression model
        feature_names: List of feature names
        X_train: Optional training data for significance calculation
        
    Returns:
        DataFrame with feature importance metrics
    """
    if not hasattr(model, 'coef_'):
        raise ValueError("Model must have coef_ attribute (trained LogisticRegression)")
    
    # Extract coefficients
    coefficients = model.coef_.flatten()
    
    if len(coefficients) != len(feature_names):
        raise ValueError(f"Coefficient count ({len(coefficients)}) doesn't match feature count ({len(feature_names)})")
    
    # Create base DataFrame
    importance_df = pd.DataFrame({
        'feature_name': feature_names,
        'coefficient': coefficients,
        'abs_coefficient': np.abs(coefficients),
    })
    
    # Calculate odds ratios
    importance_df['odds_ratio'] = np.exp(importance_df['coefficient'])
    
    # Rank by absolute coefficient
    importance_df = importance_df.sort_values('abs_coefficient', ascending=False)
    importance_df['importance_rank'] = range(1, len(importance_df) + 1)
    
    logger.info(f"Extracted importance for {len(feature_names)} features")
    
    return importance_df


def calculate_statistical_significance(
    model,
    X: np.ndarray,
    y: np.ndarray,
    feature_names: List[str],
    alpha: float = 0.05
) -> pd.DataFrame:
    """
    Calculate statistical significance for logistic regression coefficients.
    
    Uses the covariance matrix of the coefficient estimates to calculate
    standard errors, z-scores, and p-values.
    
    Args:
        model: Trained LogisticRegression model
        X: Feature matrix (scaled)
        y: Target labels
        feature_names: List of feature names
        alpha: Significance level (default 0.05 for 95% CI)
        
    Returns:
        DataFrame with statistical significance metrics
    """
    # Get predictions
    y_prob = model.predict_proba(X)[:, 1]
    
    # Calculate the diagonal of the weight matrix W (variance of binomial)
    W_diag = y_prob * (1 - y_prob)
    W_diag = np.clip(W_diag, 1e-10, 1 - 1e-10)  # Avoid numerical issues
    
    # Calculate covariance matrix: (X'WX)^-1
    # This is an approximation using the Hessian
    try:
        XtWX = np.dot(X.T * W_diag, X)
        cov_matrix = np.linalg.inv(XtWX)
        
        # Standard errors are sqrt of diagonal
        std_errors = np.sqrt(np.diag(cov_matrix))
    except np.linalg.LinAlgError:
        logger.warning("Could not compute covariance matrix, using bootstrap estimation")
        std_errors = _bootstrap_std_errors(model, X, y, n_bootstrap=100)
    
    # Get coefficients
    coefficients = model.coef_.flatten()
    
    # Calculate z-scores and p-values
    z_scores = coefficients / std_errors
    p_values = 2 * (1 - stats.norm.cdf(np.abs(z_scores)))
    
    # Calculate confidence intervals
    z_critical = stats.norm.ppf(1 - alpha / 2)
    ci_lower = coefficients - z_critical * std_errors
    ci_upper = coefficients + z_critical * std_errors
    
    # Create result DataFrame
    result_df = pd.DataFrame({
        'feature_name': feature_names,
        'coefficient': coefficients,
        'std_error': std_errors,
        'z_score': z_scores,
        'p_value': p_values,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'odds_ratio': np.exp(coefficients),
        'is_significant': p_values < alpha
    })
    
    significant_count = result_df['is_significant'].sum()
    logger.info(f"Statistical significance: {significant_count}/{len(feature_names)} features significant at alpha={alpha}")
    
    return result_df


def _bootstrap_std_errors(
    model,
    X: np.ndarray,
    y: np.ndarray,
    n_bootstrap: int = 100
) -> np.ndarray:
    """
    Estimate standard errors using bootstrap resampling.
    
    Args:
        model: Model class to fit
        X: Feature matrix
        y: Target labels
        n_bootstrap: Number of bootstrap samples
        
    Returns:
        Array of standard error estimates
    """
    from sklearn.linear_model import LogisticRegression
    
    n_samples = len(y)
    n_features = X.shape[1]
    coef_samples = np.zeros((n_bootstrap, n_features))
    
    for i in range(n_bootstrap):
        # Bootstrap sample
        indices = np.random.choice(n_samples, size=n_samples, replace=True)
        X_boot = X[indices]
        y_boot = y.iloc[indices] if hasattr(y, 'iloc') else y[indices]
        
        # Fit model
        boot_model = LogisticRegression(
            solver=model.solver,
            max_iter=model.max_iter,
            class_weight=model.class_weight,
            random_state=i
        )
        boot_model.fit(X_boot, y_boot)
        coef_samples[i] = boot_model.coef_.flatten()
    
    return coef_samples.std(axis=0)


def create_feature_importance_records(
    model,
    feature_names: List[str],
    X: np.ndarray,
    y: np.ndarray,
    model_version: str,
    churn_bucket: str
) -> pd.DataFrame:
    """
    Create feature importance records conforming to contract schema.
    
    Args:
        model: Trained LogisticRegression model
        feature_names: List of feature names
        X: Feature matrix (scaled)
        y: Target labels
        model_version: Model version identifier
        churn_bucket: Churn bucket name
        
    Returns:
        DataFrame matching contracts/feature-importance-output.json schema
    """
    # Get base importance
    importance_df = extract_feature_importance(model, feature_names)
    
    # Calculate statistical significance
    sig_df = calculate_statistical_significance(model, X, y, feature_names)
    
    # Merge
    result = importance_df.merge(
        sig_df[['feature_name', 'std_error', 'z_score', 'p_value', 'ci_lower', 'ci_upper', 'is_significant']],
        on='feature_name',
        how='left'
    )
    
    # Add metadata columns
    result['importance_id'] = [str(uuid.uuid4()) for _ in range(len(result))]
    result['model_version'] = model_version
    result['churn_bucket'] = churn_bucket
    result['created_at'] = datetime.now()
    
    # Select columns per contract
    output_columns = [
        'importance_id',
        'model_version',
        'churn_bucket',
        'feature_name',
        'coefficient',
        'odds_ratio',
        'std_error',
        'z_score',
        'p_value',
        'ci_lower',
        'ci_upper',
        'importance_rank',
        'is_significant',
        'created_at'
    ]
    
    return result[output_columns]


def get_top_features(
    importance_df: pd.DataFrame,
    n: int = 10,
    significant_only: bool = False
) -> pd.DataFrame:
    """
    Get top N features by importance.
    
    Args:
        importance_df: Feature importance DataFrame
        n: Number of top features
        significant_only: Only include statistically significant features
        
    Returns:
        Top N features sorted by absolute coefficient
    """
    df = importance_df.copy()
    
    if significant_only and 'is_significant' in df.columns:
        df = df[df['is_significant']]
    
    return df.head(n)


def interpret_coefficient(
    feature_name: str,
    coefficient: float,
    odds_ratio: float,
    is_significant: bool
) -> str:
    """
    Generate human-readable interpretation of a feature coefficient.
    
    Args:
        feature_name: Name of the feature
        coefficient: Coefficient value
        odds_ratio: Odds ratio
        is_significant: Whether statistically significant
        
    Returns:
        Interpretation string
    """
    significance_str = "statistically significant" if is_significant else "not statistically significant"
    
    if odds_ratio > 1:
        change_pct = (odds_ratio - 1) * 100
        direction = "increases"
    else:
        change_pct = (1 - odds_ratio) * 100
        direction = "decreases"
    
    interpretation = (
        f"{feature_name}: A one-unit increase {direction} the odds of churn by "
        f"{change_pct:.1f}% (OR={odds_ratio:.3f}). This relationship is {significance_str}."
    )
    
    return interpretation


def generate_importance_report(
    importance_df: pd.DataFrame,
    model_version: str,
    churn_bucket: str,
    top_n: int = 10
) -> str:
    """
    Generate a markdown report of feature importance analysis.
    
    Args:
        importance_df: Feature importance DataFrame
        model_version: Model version identifier
        churn_bucket: Churn bucket name
        top_n: Number of top features to highlight
        
    Returns:
        Markdown report string
    """
    report = f"""# Feature Importance Report

**Model Version**: {model_version}  
**Churn Bucket**: {churn_bucket}  
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Top {top_n} Features by Importance

| Rank | Feature | Coefficient | Odds Ratio | p-value | Significant |
|------|---------|-------------|------------|---------|-------------|
"""
    
    top_features = importance_df.head(top_n)
    for _, row in top_features.iterrows():
        sig_marker = "✓" if row.get('is_significant', False) else ""
        p_val = f"{row.get('p_value', 'N/A'):.4f}" if pd.notna(row.get('p_value')) else "N/A"
        report += f"| {row['importance_rank']} | {row['feature_name']} | {row['coefficient']:.4f} | {row['odds_ratio']:.3f} | {p_val} | {sig_marker} |\n"
    
    # Summary statistics
    total_features = len(importance_df)
    sig_count = importance_df.get('is_significant', pd.Series([False])).sum()
    
    report += f"""
## Summary

- **Total Features**: {total_features}
- **Statistically Significant (p<0.05)**: {sig_count}
- **Non-Significant**: {total_features - sig_count}

## Key Interpretations

"""
    
    # Add interpretations for top 3 features
    for _, row in top_features.head(3).iterrows():
        if 'is_significant' in row:
            interp = interpret_coefficient(
                row['feature_name'],
                row['coefficient'],
                row['odds_ratio'],
                row['is_significant']
            )
            report += f"- {interp}\n"
    
    return report
