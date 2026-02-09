"""
Model evaluation module for performance metrics and analysis.

Calculates:
- AUC-ROC and AUC-PR
- Classification metrics (accuracy, precision, recall, F1)
- Confusion matrix
- Probability calibration
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report as sklearn_classification_report,
    roc_curve,
    precision_recall_curve
)

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Calculate comprehensive classification metrics.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        y_prob: Predicted probabilities for positive class
        
    Returns:
        Dict with metric names and values
    """
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0),
    }
    
    if y_prob is not None:
        metrics['auc_roc'] = roc_auc_score(y_true, y_prob)
        metrics['auc_pr'] = average_precision_score(y_true, y_prob)
    
    return metrics


def evaluate_model(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    threshold: float = 0.5
) -> Dict[str, float]:
    """
    Evaluate a trained model on test data.
    
    Args:
        model: Trained sklearn model
        X_test: Test features (scaled if necessary)
        y_test: Test labels
        threshold: Classification threshold
        
    Returns:
        Dict with evaluation metrics
    """
    # Get predictions
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)
    
    # Calculate metrics
    metrics = calculate_metrics(y_test, y_pred, y_prob)
    
    logger.info(f"Evaluation: AUC-ROC={metrics['auc_roc']:.4f}, F1={metrics['f1']:.4f}")
    
    return metrics


def generate_classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Optional[list] = None
) -> str:
    """
    Generate detailed classification report.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        labels: Optional label names
        
    Returns:
        Formatted classification report string
    """
    if labels is None:
        labels = ['Retained', 'Churned']
    
    return sklearn_classification_report(y_true, y_pred, target_names=labels)


def get_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    normalize: bool = False
) -> Tuple[np.ndarray, Dict[str, int]]:
    """
    Calculate confusion matrix with labeled components.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        normalize: Whether to normalize values
        
    Returns:
        Tuple of (matrix, dict with TN/FP/FN/TP counts)
    """
    cm = confusion_matrix(y_true, y_pred)
    
    if normalize:
        cm = cm.astype('float') / cm.sum()
    
    tn, fp, fn, tp = cm.ravel()
    
    components = {
        'true_negative': int(tn) if not normalize else float(tn),
        'false_positive': int(fp) if not normalize else float(fp),
        'false_negative': int(fn) if not normalize else float(fn),
        'true_positive': int(tp) if not normalize else float(tp),
    }
    
    return cm, components


def get_roc_curve_data(
    y_true: np.ndarray,
    y_prob: np.ndarray
) -> Dict[str, np.ndarray]:
    """
    Get ROC curve data for plotting.
    
    Args:
        y_true: True labels
        y_prob: Predicted probabilities
        
    Returns:
        Dict with fpr, tpr, and thresholds arrays
    """
    fpr, tpr, thresholds = roc_curve(y_true, y_prob)
    auc = roc_auc_score(y_true, y_prob)
    
    return {
        'fpr': fpr,
        'tpr': tpr,
        'thresholds': thresholds,
        'auc': auc
    }


def get_precision_recall_curve_data(
    y_true: np.ndarray,
    y_prob: np.ndarray
) -> Dict[str, np.ndarray]:
    """
    Get precision-recall curve data for plotting.
    
    Args:
        y_true: True labels
        y_prob: Predicted probabilities
        
    Returns:
        Dict with precision, recall, and thresholds arrays
    """
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    auc = average_precision_score(y_true, y_prob)
    
    return {
        'precision': precision,
        'recall': recall,
        'thresholds': thresholds,
        'auc': auc
    }


def find_optimal_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    metric: str = 'f1'
) -> Tuple[float, float]:
    """
    Find optimal classification threshold for a given metric.
    
    Args:
        y_true: True labels
        y_prob: Predicted probabilities
        metric: Metric to optimize ('f1', 'youden', 'precision', 'recall')
        
    Returns:
        Tuple of (optimal threshold, metric value at threshold)
    """
    thresholds = np.arange(0.1, 0.9, 0.01)
    scores = []
    
    for thresh in thresholds:
        y_pred = (y_prob >= thresh).astype(int)
        
        if metric == 'f1':
            score = f1_score(y_true, y_pred, zero_division=0)
        elif metric == 'youden':
            # Youden's J statistic = sensitivity + specificity - 1
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            score = sensitivity + specificity - 1
        elif metric == 'precision':
            score = precision_score(y_true, y_pred, zero_division=0)
        elif metric == 'recall':
            score = recall_score(y_true, y_pred, zero_division=0)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        scores.append(score)
    
    best_idx = np.argmax(scores)
    optimal_threshold = thresholds[best_idx]
    best_score = scores[best_idx]
    
    logger.info(f"Optimal threshold for {metric}: {optimal_threshold:.2f} (score: {best_score:.4f})")
    
    return optimal_threshold, best_score


def compare_models(
    model_results: Dict[str, Dict[str, Any]]
) -> pd.DataFrame:
    """
    Compare metrics across multiple trained models.
    
    Args:
        model_results: Dict from train_churn_models output
        
    Returns:
        DataFrame with models as rows and metrics as columns
    """
    config = get_config()
    
    comparison_data = []
    for bucket_name, results in model_results.items():
        row = {
            'model': bucket_name,
            'auc_roc': results['metrics']['auc_roc'],
            'auc_pr': results['metrics']['auc_pr'],
            'precision': results['metrics']['precision'],
            'recall': results['metrics']['recall'],
            'f1': results['metrics']['f1'],
            'cv_mean': results['cv_results']['cv_mean'],
            'cv_std': results['cv_results']['cv_std'],
            'meets_threshold': results['metrics']['auc_roc'] >= config.model.MIN_AUC_ROC
        }
        comparison_data.append(row)
    
    df = pd.DataFrame(comparison_data)
    df = df.sort_values('auc_roc', ascending=False)
    
    return df
