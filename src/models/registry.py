"""
MLflow model registry integration for version management.

Provides:
- Model registration and versioning
- Model loading from registry
- Model promotion (staging -> production)
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _get_mlflow_client():
    """Get MLflow tracking client."""
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        return mlflow, MlflowClient()
    except ImportError:
        logger.warning("MLflow not installed")
        return None, None


def register_model(
    model,
    model_name: str,
    scaler=None,
    feature_names: list = None,
    metrics: dict = None,
    tags: dict = None
) -> Optional[str]:
    """
    Register a trained model in MLflow registry.
    
    Args:
        model: Trained sklearn model
        model_name: Name for the registered model
        scaler: Optional fitted scaler
        feature_names: List of feature names
        metrics: Model performance metrics
        tags: Optional tags to attach
        
    Returns:
        Model version string or None if registration failed
    """
    mlflow, client = _get_mlflow_client()
    if mlflow is None:
        return None
    
    config = get_config()
    
    try:
        with mlflow.start_run() as run:
            # Log model
            mlflow.sklearn.log_model(
                model,
                "model",
                registered_model_name=model_name
            )
            
            # Log scaler as artifact if provided
            if scaler is not None:
                import joblib
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
                    joblib.dump(scaler, f.name)
                    mlflow.log_artifact(f.name, "scaler")
                os.unlink(f.name)
            
            # Log metrics
            if metrics:
                mlflow.log_metrics(metrics)
            
            # Log feature names
            if feature_names:
                mlflow.log_dict({'features': feature_names}, 'feature_names.json')
            
            # Log tags
            default_tags = {
                'training_date': datetime.now().isoformat(),
                'framework': 'sklearn',
                'model_type': 'LogisticRegression'
            }
            if tags:
                default_tags.update(tags)
            mlflow.set_tags(default_tags)
            
            # Get registered version
            model_uri = f"runs:/{run.info.run_id}/model"
            model_details = mlflow.register_model(model_uri, model_name)
            version = model_details.version
            
            logger.info(f"Registered model '{model_name}' version {version}")
            return version
            
    except Exception as e:
        logger.error(f"Failed to register model: {e}")
        return None


def load_model(
    model_name: str,
    version: Optional[str] = None,
    stage: Optional[str] = None
) -> Tuple[Any, Optional[Any]]:
    """
    Load a model from MLflow registry.
    
    Args:
        model_name: Name of the registered model
        version: Specific version to load (optional)
        stage: Stage to load from ('Production', 'Staging', etc.)
        
    Returns:
        Tuple of (model, scaler) - scaler may be None
    """
    mlflow, client = _get_mlflow_client()
    if mlflow is None:
        raise ImportError("MLflow not available")
    
    try:
        if version:
            model_uri = f"models:/{model_name}/{version}"
        elif stage:
            model_uri = f"models:/{model_name}/{stage}"
        else:
            # Load latest version
            model_uri = f"models:/{model_name}/latest"
        
        model = mlflow.sklearn.load_model(model_uri)
        
        # Try to load scaler artifact
        scaler = None
        try:
            # Get run ID from model version
            if version:
                mv = client.get_model_version(model_name, version)
                run_id = mv.run_id
            else:
                # Get latest version
                versions = client.search_model_versions(f"name='{model_name}'")
                if versions:
                    run_id = versions[0].run_id
                else:
                    run_id = None
            
            if run_id:
                import joblib
                scaler_path = client.download_artifacts(run_id, "scaler")
                scaler_file = os.path.join(scaler_path, os.listdir(scaler_path)[0])
                scaler = joblib.load(scaler_file)
                
        except Exception as e:
            logger.warning(f"Could not load scaler: {e}")
        
        logger.info(f"Loaded model '{model_name}' from {model_uri}")
        return model, scaler
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


def get_latest_model_version(model_name: str) -> Optional[str]:
    """
    Get the latest version number for a model.
    
    Args:
        model_name: Name of the registered model
        
    Returns:
        Version string or None
    """
    mlflow, client = _get_mlflow_client()
    if client is None:
        return None
    
    try:
        versions = client.search_model_versions(f"name='{model_name}'")
        if versions:
            latest = max(versions, key=lambda v: int(v.version))
            return latest.version
        return None
    except Exception as e:
        logger.error(f"Failed to get model version: {e}")
        return None


def transition_model_stage(
    model_name: str,
    version: str,
    stage: str,
    archive_existing: bool = True
) -> bool:
    """
    Transition a model version to a new stage.
    
    Args:
        model_name: Name of the registered model
        version: Version to transition
        stage: Target stage ('Staging', 'Production', 'Archived')
        archive_existing: Whether to archive existing models in target stage
        
    Returns:
        True if successful
    """
    mlflow, client = _get_mlflow_client()
    if client is None:
        return False
    
    try:
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing
        )
        logger.info(f"Transitioned {model_name} v{version} to {stage}")
        return True
    except Exception as e:
        logger.error(f"Failed to transition model: {e}")
        return False


def get_model_metrics(model_name: str, version: str) -> Optional[Dict[str, float]]:
    """
    Get metrics for a specific model version.
    
    Args:
        model_name: Name of the registered model
        version: Model version
        
    Returns:
        Dict of metrics or None
    """
    mlflow, client = _get_mlflow_client()
    if client is None:
        return None
    
    try:
        mv = client.get_model_version(model_name, version)
        run = client.get_run(mv.run_id)
        return run.data.metrics
    except Exception as e:
        logger.error(f"Failed to get model metrics: {e}")
        return None


def list_model_versions(
    model_name: str,
    stage: Optional[str] = None
) -> list:
    """
    List all versions of a model.
    
    Args:
        model_name: Name of the registered model
        stage: Optional stage filter
        
    Returns:
        List of version info dicts
    """
    mlflow, client = _get_mlflow_client()
    if client is None:
        return []
    
    try:
        filter_str = f"name='{model_name}'"
        versions = client.search_model_versions(filter_str)
        
        results = []
        for v in versions:
            if stage is None or v.current_stage == stage:
                results.append({
                    'version': v.version,
                    'stage': v.current_stage,
                    'status': v.status,
                    'creation_time': v.creation_timestamp,
                    'run_id': v.run_id
                })
        
        return sorted(results, key=lambda x: int(x['version']), reverse=True)
    except Exception as e:
        logger.error(f"Failed to list model versions: {e}")
        return []
