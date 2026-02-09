"""
Model training module for logistic regression churn models.

Implements:
- Logistic regression with class_weight='balanced'
- Stratified k-fold cross-validation
- MLflow experiment tracking
- Separate models per churn bucket
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler

from ..utils.config import get_config
from ..utils.logging import get_logger, ModelTrainingLogger

logger = get_logger(__name__)


def train_logistic_regression(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_config: Optional[Dict[str, Any]] = None
) -> Tuple[LogisticRegression, StandardScaler]:
    """
    Train a logistic regression model with balanced class weights.
    
    Args:
        X_train: Training features
        y_train: Training labels  
        model_config: Optional configuration overrides
        
    Returns:
        Tuple of (trained model, fitted scaler)
    """
    config = get_config()
    
    # Merge default config with overrides
    params = {
        'solver': config.model.SOLVER,
        'max_iter': config.model.MAX_ITER,
        'class_weight': config.model.CLASS_WEIGHT,
        'random_state': config.model.RANDOM_STATE,
    }
    if model_config:
        params.update(model_config)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    
    # Train model
    model = LogisticRegression(**params)
    model.fit(X_scaled, y_train)
    
    logger.info(f"Trained LogisticRegression with {len(X_train)} samples, {X_train.shape[1]} features")
    
    return model, scaler


def cross_validate_model(
    X: pd.DataFrame,
    y: pd.Series,
    model: Optional[LogisticRegression] = None,
    n_folds: int = 5,
    scoring: str = 'roc_auc'
) -> Dict[str, float]:
    """
    Perform stratified k-fold cross-validation.
    
    Args:
        X: Feature matrix
        y: Labels
        model: Model to validate (creates default if None)
        n_folds: Number of CV folds
        scoring: Scoring metric ('roc_auc', 'f1', 'precision', 'recall')
        
    Returns:
        Dict with mean and std of CV scores
    """
    config = get_config()
    
    if model is None:
        model = LogisticRegression(
            solver=config.model.SOLVER,
            max_iter=config.model.MAX_ITER,
            class_weight=config.model.CLASS_WEIGHT,
            random_state=config.model.RANDOM_STATE,
        )
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Stratified k-fold
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=config.model.RANDOM_STATE)
    
    # Cross-validate
    scores = cross_val_score(model, X_scaled, y, cv=cv, scoring=scoring)
    
    results = {
        'cv_mean': scores.mean(),
        'cv_std': scores.std(),
        'cv_scores': scores.tolist(),
        'n_folds': n_folds,
        'scoring': scoring
    }
    
    logger.info(f"CV Results: {scoring} = {results['cv_mean']:.4f} (+/- {results['cv_std']:.4f})")
    
    return results


def train_churn_models(
    features_df: pd.DataFrame,
    labels_dict: Dict[str, pd.DataFrame],
    test_size: float = 0.2,
    mlflow_tracking: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Train separate models for each churn bucket.
    
    Args:
        features_df: Feature matrix with customer_id
        labels_dict: Dict mapping bucket names to label DataFrames
        test_size: Proportion for test set
        mlflow_tracking: Whether to log to MLflow
        
    Returns:
        Dict mapping bucket names to trained model info
    """
    from sklearn.model_selection import train_test_split
    from .evaluation import evaluate_model
    
    config = get_config()
    results = {}
    
    for bucket_name, labels_df in labels_dict.items():
        training_logger = ModelTrainingLogger(bucket_name)
        
        # Merge features and labels
        data = features_df.merge(labels_df, on='customer_id', how='inner')
        
        # Separate features and target
        X = data.drop(columns=['customer_id', 'label'])
        y = data['label']
        
        training_logger.start_training(len(X), X.shape[1])
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=config.model.RANDOM_STATE, stratify=y
        )
        
        # Cross-validate
        cv_results = cross_validate_model(X_train, y_train)
        
        # Train final model
        model, scaler = train_logistic_regression(X_train, y_train)
        
        # Evaluate on test set
        X_test_scaled = scaler.transform(X_test)
        metrics = evaluate_model(model, X_test_scaled, y_test)
        
        training_logger.log_metrics(metrics)
        training_logger.end_training(success=metrics['auc_roc'] >= config.model.MIN_AUC_ROC)
        
        # Check performance threshold
        if metrics['auc_roc'] < config.model.MIN_AUC_ROC:
            logger.warning(f"{bucket_name}: AUC-ROC {metrics['auc_roc']:.4f} below threshold {config.model.MIN_AUC_ROC}")
        
        # MLflow tracking
        if mlflow_tracking:
            try:
                import mlflow
                
                with mlflow.start_run(run_name=f"churn_{bucket_name}"):
                    # Log parameters
                    mlflow.log_params({
                        'bucket': bucket_name,
                        'solver': config.model.SOLVER,
                        'class_weight': config.model.CLASS_WEIGHT,
                        'train_samples': len(X_train),
                        'test_samples': len(X_test),
                        'n_features': X.shape[1]
                    })
                    
                    # Log metrics
                    mlflow.log_metrics(metrics)
                    mlflow.log_metrics({
                        'cv_mean_auc': cv_results['cv_mean'],
                        'cv_std_auc': cv_results['cv_std']
                    })
                    
                    # Log model
                    mlflow.sklearn.log_model(model, f"model_{bucket_name}")
                    
                    run_id = mlflow.active_run().info.run_id
                    logger.info(f"Logged to MLflow run: {run_id}")
                    
            except ImportError:
                logger.warning("MLflow not available, skipping tracking")
                run_id = None
            except Exception as e:
                logger.error(f"MLflow error: {e}")
                run_id = None
        else:
            run_id = None
        
        # Store results
        results[bucket_name] = {
            'model': model,
            'scaler': scaler,
            'feature_names': X.columns.tolist(),
            'metrics': metrics,
            'cv_results': cv_results,
            'mlflow_run_id': run_id,
            'training_date': datetime.now().isoformat()
        }
    
    return results


def get_model_hyperparameters(model: LogisticRegression) -> Dict[str, Any]:
    """
    Extract hyperparameters from a fitted model.
    
    Args:
        model: Fitted LogisticRegression model
        
    Returns:
        Dict of hyperparameters
    """
    return {
        'solver': model.solver,
        'max_iter': model.max_iter,
        'class_weight': str(model.class_weight),
        'C': model.C,
        'penalty': model.penalty,
        'n_features': model.n_features_in_,
        'n_classes': len(model.classes_),
        'n_iter': model.n_iter_.tolist() if hasattr(model, 'n_iter_') else None
    }
