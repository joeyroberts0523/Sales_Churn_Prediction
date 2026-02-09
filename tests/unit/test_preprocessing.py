"""
Unit tests for data preprocessing functions.

Covers:
- Missing value handling
- Label creation
- Feature matrix generation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestHandleMissingValues:
    """Tests for missing value handling functions."""
    
    def test_numeric_median_imputation(self):
        """Test that numeric columns are imputed with median."""
        from src.data.preprocessing import handle_missing_values
        
        df = pd.DataFrame({
            'numeric_col': [1.0, 2.0, np.nan, 4.0, 5.0],
            'id': [1, 2, 3, 4, 5]
        })
        
        result = handle_missing_values(df, numeric_strategy='median')
        
        assert result['numeric_col'].isna().sum() == 0
        # Median of [1, 2, 4, 5] is 3
        assert result.loc[2, 'numeric_col'] == 3.0
    
    def test_numeric_mean_imputation(self):
        """Test that numeric columns can be imputed with mean."""
        from src.data.preprocessing import handle_missing_values
        
        df = pd.DataFrame({
            'numeric_col': [1.0, 2.0, np.nan, 4.0, 5.0]
        })
        
        result = handle_missing_values(df, numeric_strategy='mean')
        
        assert result['numeric_col'].isna().sum() == 0
        # Mean of [1, 2, 4, 5] is 3
        assert result.loc[2, 'numeric_col'] == 3.0
    
    def test_categorical_mode_imputation(self):
        """Test that categorical columns are imputed with mode."""
        from src.data.preprocessing import handle_missing_values
        
        df = pd.DataFrame({
            'cat_col': ['A', 'B', 'A', np.nan, 'A']
        })
        
        result = handle_missing_values(df, categorical_strategy='most_frequent')
        
        assert result['cat_col'].isna().sum() == 0
        assert result.loc[3, 'cat_col'] == 'A'
    
    def test_column_drop_threshold(self):
        """Test that columns with too many missing values are dropped."""
        from src.data.preprocessing import handle_missing_values
        
        df = pd.DataFrame({
            'col1': [1, 2, 3, 4, 5],
            'col2': [np.nan, np.nan, np.nan, np.nan, 1]  # 80% missing
        })
        
        result = handle_missing_values(df, columns_to_drop_threshold=0.5)
        
        assert 'col1' in result.columns
        assert 'col2' not in result.columns


class TestCreateLabel:
    """Tests for churn label creation."""
    
    def test_label_30d_churn(self):
        """Test 30-day churn label creation."""
        from src.data.preprocessing import create_label
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'created_at': [datetime(2023, 1, 1)] * 3
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'activity_date': [
                datetime(2023, 12, 20),  # 12 days ago - not churned
                datetime(2023, 11, 1),   # 61 days ago - churned
                datetime(2023, 12, 5),   # 27 days ago - not churned
            ]
        })
        
        churn_events = pd.DataFrame(columns=['customer_id', 'event_date', 'event_type'])
        
        result = create_label(customers, activity, churn_events, 
                             reference_date=reference_date, bucket_type='churn_30d')
        
        labels = dict(zip(result['customer_id'], result['label']))
        
        assert labels['C1'] == 0  # Active within 30 days
        assert labels['C2'] == 1  # Inactive > 30 days
        assert labels['C3'] == 0  # Active within 30 days
    
    def test_label_explicit_churn(self):
        """Test explicit churn label creation."""
        from src.data.preprocessing import create_label
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2'],
            'created_at': [datetime(2023, 1, 1)] * 2
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C2'],
            'activity_date': [datetime(2023, 12, 1)] * 2
        })
        
        churn_events = pd.DataFrame({
            'customer_id': ['C1'],
            'event_date': [datetime(2023, 12, 15)],
            'event_type': ['cancellation']
        })
        
        result = create_label(customers, activity, churn_events,
                             reference_date=reference_date, bucket_type='churn_explicit')
        
        labels = dict(zip(result['customer_id'], result['label']))
        
        assert labels['C1'] == 1  # Has cancellation event
        assert labels['C2'] == 0  # No cancellation event


class TestCreateFeatureMatrix:
    """Tests for feature matrix creation."""
    
    def test_feature_matrix_shape(self):
        """Test that feature matrix has correct shape."""
        from src.data.preprocessing import create_feature_matrix
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'created_at': [datetime(2023, 1, 1)] * 3,
            'segment': ['A', 'B', 'A']
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C2', 'C3'],
            'activity_date': [datetime(2023, 12, 1)] * 4,
            'activity_type': ['purchase', 'login', 'purchase', 'login']
        })
        
        result = create_feature_matrix(customers, activity)
        
        # Should have one row per customer
        assert len(result) == 3
        # Should have customer_id column
        assert 'customer_id' in result.columns
    
    def test_feature_matrix_numeric_columns(self):
        """Test that feature matrix contains numeric features."""
        from src.data.preprocessing import create_feature_matrix
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2'],
            'created_at': [datetime(2023, 1, 1)] * 2,
            'revenue': [100.0, 200.0]
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C2'],
            'activity_date': [datetime(2023, 12, 1)] * 2,
            'activity_type': ['purchase', 'purchase']
        })
        
        result = create_feature_matrix(customers, activity)
        
        # Should preserve numeric columns
        assert 'revenue' in result.columns or any('revenue' in c for c in result.columns)


class TestEncodeCategorical:
    """Tests for categorical encoding."""
    
    def test_onehot_encoding(self):
        """Test one-hot encoding of categorical columns."""
        from src.data.preprocessing import encode_categorical
        
        df = pd.DataFrame({
            'segment': ['A', 'B', 'A', 'C'],
            'numeric': [1, 2, 3, 4]
        })
        
        result = encode_categorical(df, columns=['segment'], method='onehot')
        
        # Should create binary columns for each category
        assert 'segment_A' in result.columns or 'segment_B' in result.columns
        assert 'numeric' in result.columns
    
    def test_label_encoding(self):
        """Test label encoding of categorical columns."""
        from src.data.preprocessing import encode_categorical
        
        df = pd.DataFrame({
            'segment': ['A', 'B', 'A', 'C']
        })
        
        result = encode_categorical(df, columns=['segment'], method='label')
        
        # Should convert to numeric
        assert result['segment'].dtype in [np.int64, np.int32, int]


class TestScaleFeatures:
    """Tests for feature scaling."""
    
    def test_standard_scaling(self):
        """Test standard scaling (z-score normalization)."""
        from src.data.preprocessing import scale_features
        
        df = pd.DataFrame({
            'feature': [10, 20, 30, 40, 50]
        })
        
        result, scaler = scale_features(df, columns=['feature'], method='standard')
        
        # Mean should be approximately 0, std approximately 1
        assert abs(result['feature'].mean()) < 0.01
        assert abs(result['feature'].std() - 1.0) < 0.1
    
    def test_minmax_scaling(self):
        """Test min-max scaling."""
        from src.data.preprocessing import scale_features
        
        df = pd.DataFrame({
            'feature': [10, 20, 30, 40, 50]
        })
        
        result, scaler = scale_features(df, columns=['feature'], method='minmax')
        
        # Values should be between 0 and 1
        assert result['feature'].min() >= 0
        assert result['feature'].max() <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
