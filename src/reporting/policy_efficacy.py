"""
Policy efficacy analysis module.

Compares churn rates between treatment and control cohorts
with statistical significance testing (chi-square, t-test).
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats

from ..utils.logging import get_logger

logger = get_logger(__name__)


def calculate_policy_efficacy(
    policy_cohorts_df: pd.DataFrame,
    policy_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate policy efficacy metrics.
    
    Args:
        policy_cohorts_df: DataFrame with cohort_type, did_churn columns
        policy_name: Optional policy name for reporting
        
    Returns:
        Dict with efficacy metrics
    """
    if 'cohort_type' not in policy_cohorts_df.columns:
        raise ValueError("policy_cohorts_df must have 'cohort_type' column")
    if 'did_churn' not in policy_cohorts_df.columns:
        raise ValueError("policy_cohorts_df must have 'did_churn' column")
    
    # Filter to measured outcomes only
    df = policy_cohorts_df[policy_cohorts_df['outcome_measured'] == True].copy()
    
    # Separate treatment and control
    treatment = df[df['cohort_type'] == 'treatment']
    control = df[df['cohort_type'] == 'control']
    
    # Calculate churn rates
    treatment_churn_rate = treatment['did_churn'].mean() if len(treatment) > 0 else 0
    control_churn_rate = control['did_churn'].mean() if len(control) > 0 else 0
    
    # Calculate reduction
    if control_churn_rate > 0:
        absolute_reduction = control_churn_rate - treatment_churn_rate
        relative_reduction = absolute_reduction / control_churn_rate
    else:
        absolute_reduction = 0
        relative_reduction = 0
    
    # Run significance test
    sig_result = run_significance_test(
        treatment['did_churn'].values,
        control['did_churn'].values,
        test_type='chi_square'
    )
    
    result = {
        'policy_name': policy_name,
        'treatment_count': len(treatment),
        'control_count': len(control),
        'treatment_churn_rate': treatment_churn_rate,
        'control_churn_rate': control_churn_rate,
        'absolute_reduction': absolute_reduction,
        'relative_reduction': relative_reduction,
        'is_significant': sig_result['is_significant'],
        'p_value': sig_result['p_value'],
        'test_statistic': sig_result['test_statistic'],
        'test_type': sig_result['test_type'],
        'sample_size_adequate': len(treatment) >= 30 and len(control) >= 30,
        'calculated_at': datetime.now().isoformat()
    }
    
    logger.info(
        f"Policy efficacy: treatment={treatment_churn_rate:.2%}, "
        f"control={control_churn_rate:.2%}, "
        f"reduction={relative_reduction:.2%} "
        f"(p={result['p_value']:.4f}, significant={result['is_significant']})"
    )
    
    return result


def compare_cohorts(
    treatment_outcomes: np.ndarray,
    control_outcomes: np.ndarray
) -> Dict[str, float]:
    """
    Compare outcomes between treatment and control cohorts.
    
    Args:
        treatment_outcomes: Array of binary outcomes (0/1) for treatment
        control_outcomes: Array of binary outcomes (0/1) for control
        
    Returns:
        Dict with comparison metrics
    """
    treatment_rate = np.mean(treatment_outcomes)
    control_rate = np.mean(control_outcomes)
    
    # Risk difference (absolute reduction)
    risk_difference = control_rate - treatment_rate
    
    # Risk ratio (relative risk)
    risk_ratio = treatment_rate / control_rate if control_rate > 0 else np.nan
    
    # Odds ratio
    treatment_odds = treatment_rate / (1 - treatment_rate) if treatment_rate < 1 else np.inf
    control_odds = control_rate / (1 - control_rate) if control_rate < 1 else np.inf
    odds_ratio = treatment_odds / control_odds if control_odds > 0 else np.nan
    
    # Number needed to treat (NNT)
    nnt = 1 / risk_difference if risk_difference > 0 else np.inf
    
    return {
        'treatment_rate': treatment_rate,
        'control_rate': control_rate,
        'risk_difference': risk_difference,
        'risk_ratio': risk_ratio,
        'odds_ratio': odds_ratio,
        'number_needed_to_treat': nnt
    }


def run_significance_test(
    treatment_outcomes: np.ndarray,
    control_outcomes: np.ndarray,
    test_type: str = 'chi_square',
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Run statistical significance test between cohorts.
    
    Args:
        treatment_outcomes: Binary outcomes for treatment group
        control_outcomes: Binary outcomes for control group
        test_type: 'chi_square' or 't_test'
        alpha: Significance level
        
    Returns:
        Dict with test results
    """
    if test_type == 'chi_square':
        # Create contingency table
        # Rows: treatment/control, Columns: churned/retained
        treatment_churn = np.sum(treatment_outcomes)
        treatment_retain = len(treatment_outcomes) - treatment_churn
        control_churn = np.sum(control_outcomes)
        control_retain = len(control_outcomes) - control_churn
        
        contingency = np.array([
            [treatment_churn, treatment_retain],
            [control_churn, control_retain]
        ])
        
        # Chi-square test
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
        
        # Check expected frequencies (chi-square assumption)
        min_expected = expected.min()
        assumption_met = min_expected >= 5
        
        return {
            'test_type': 'chi_square',
            'test_statistic': chi2,
            'p_value': p_value,
            'degrees_of_freedom': dof,
            'is_significant': p_value < alpha,
            'assumption_met': assumption_met,
            'min_expected_frequency': min_expected
        }
        
    elif test_type == 't_test':
        # Two-sample t-test
        # Note: For binary outcomes, chi-square is typically preferred
        t_stat, p_value = stats.ttest_ind(treatment_outcomes, control_outcomes)
        
        return {
            'test_type': 't_test',
            'test_statistic': t_stat,
            'p_value': p_value,
            'is_significant': p_value < alpha
        }
    
    else:
        raise ValueError(f"Unknown test type: {test_type}")


def calculate_confidence_interval(
    rate: float,
    n: int,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate confidence interval for a proportion.
    
    Uses Wilson score interval for better coverage with small samples.
    
    Args:
        rate: Observed proportion
        n: Sample size
        confidence: Confidence level (default 0.95)
        
    Returns:
        Tuple of (lower, upper) bounds
    """
    if n == 0:
        return (0.0, 1.0)
    
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    
    # Wilson score interval
    denominator = 1 + z**2 / n
    center = (rate + z**2 / (2 * n)) / denominator
    margin = z * np.sqrt((rate * (1 - rate) + z**2 / (4 * n)) / n) / denominator
    
    lower = max(0, center - margin)
    upper = min(1, center + margin)
    
    return (lower, upper)


def generate_efficacy_report(
    efficacy_results: Dict[str, Any],
    policy_details: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate markdown report of policy efficacy analysis.
    
    Args:
        efficacy_results: Results from calculate_policy_efficacy
        policy_details: Optional additional policy information
        
    Returns:
        Markdown report string
    """
    report = f"""# Policy Efficacy Report

**Policy**: {efficacy_results.get('policy_name', 'Unknown')}  
**Analysis Date**: {efficacy_results.get('calculated_at', datetime.now().isoformat())}

## Cohort Summary

| Metric | Treatment | Control |
|--------|-----------|---------|
| Sample Size | {efficacy_results['treatment_count']} | {efficacy_results['control_count']} |
| Churn Rate | {efficacy_results['treatment_churn_rate']:.2%} | {efficacy_results['control_churn_rate']:.2%} |

## Efficacy Metrics

- **Absolute Reduction**: {efficacy_results['absolute_reduction']:.2%}
- **Relative Reduction**: {efficacy_results['relative_reduction']:.2%}

## Statistical Significance

- **Test Type**: {efficacy_results['test_type']}
- **Test Statistic**: {efficacy_results['test_statistic']:.4f}
- **p-value**: {efficacy_results['p_value']:.4f}
- **Statistically Significant**: {'Yes ✓' if efficacy_results['is_significant'] else 'No'}

## Data Quality Notes

- **Sample Size Adequate**: {'Yes ✓' if efficacy_results['sample_size_adequate'] else 'No - Results may be unreliable'}

"""
    
    if efficacy_results['is_significant'] and efficacy_results['relative_reduction'] > 0:
        report += f"""
## Interpretation

The policy shows a **statistically significant reduction** in churn rates.
Customers in the treatment group had a {efficacy_results['relative_reduction']:.1%} lower
churn rate compared to the control group.

**Recommendation**: Consider expanding this policy to additional customer segments.
"""
    elif not efficacy_results['is_significant']:
        report += """
## Interpretation

The difference in churn rates between treatment and control groups is 
**not statistically significant**. This could indicate:
- The policy has no effect
- Sample size is too small to detect an effect
- More time is needed to observe outcomes

**Recommendation**: Continue monitoring or increase sample size.
"""
    
    return report


def analyze_multiple_policies(
    policy_cohorts_df: pd.DataFrame,
    policies_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Analyze efficacy across multiple policies.
    
    Args:
        policy_cohorts_df: Cohort data with policy_id
        policies_df: Policy definitions with policy_id, policy_name
        
    Returns:
        DataFrame with efficacy metrics for each policy
    """
    results = []
    
    for policy_id in policy_cohorts_df['policy_id'].unique():
        cohorts = policy_cohorts_df[policy_cohorts_df['policy_id'] == policy_id]
        
        # Get policy name
        policy_info = policies_df[policies_df['policy_id'] == policy_id]
        policy_name = policy_info['policy_name'].iloc[0] if len(policy_info) > 0 else policy_id
        
        # Calculate efficacy
        efficacy = calculate_policy_efficacy(cohorts, policy_name)
        efficacy['policy_id'] = policy_id
        results.append(efficacy)
    
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values('relative_reduction', ascending=False)
    
    return result_df
