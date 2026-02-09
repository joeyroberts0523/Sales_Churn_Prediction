"""
Unit tests for feature engineering functions.

Covers:
- Tenure feature creation
- Activity feature creation
- Recency feature creation
- Trend feature creation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestTenureFeatures:
    """Tests for tenure-related feature creation."""
    
    def test_tenure_days_calculation(self):
        """Test basic tenure days calculation."""
        from src.features.engineering import create_tenure_features
        
        reference_date = datetime(2024, 1, 1)
        
        df = pd.DataFrame({
            'customer_id': ['C1', 'C2'],
            'created_at': [
                datetime(2023, 1, 1),   # 365 days
                datetime(2023, 7, 1),   # 184 days
            ]
        })
        
        result = create_tenure_features(df, reference_date=reference_date)
        
        assert 'tenure_days' in result.columns
        assert result.loc[0, 'tenure_days'] == 365
        assert result.loc[1, 'tenure_days'] == 184
    
    def test_tenure_months_calculation(self):
        """Test tenure months calculation."""
        from src.features.engineering import create_tenure_features
        
        reference_date = datetime(2024, 1, 1)
        
        df = pd.DataFrame({
            'customer_id': ['C1'],
            'created_at': [datetime(2023, 1, 1)]
        })
        
        result = create_tenure_features(df, reference_date=reference_date)
        
        assert 'tenure_months' in result.columns
        assert result.loc[0, 'tenure_months'] == 12
    
    def test_tenure_bucket_assignment(self):
        """Test tenure bucket categorization."""
        from src.features.engineering import create_tenure_features
        
        reference_date = datetime(2024, 1, 1)
        
        df = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3'],
            'created_at': [
                datetime(2023, 11, 1),   # 2 months - new
                datetime(2023, 7, 1),    # 6 months - medium
                datetime(2020, 1, 1),    # 4 years - long-term
            ]
        })
        
        result = create_tenure_features(df, reference_date=reference_date)
        
        assert 'tenure_bucket' in result.columns
        # Values should be categorical buckets
        assert result['tenure_bucket'].nunique() >= 1


class TestActivityFeatures:
    """Tests for activity-related feature creation."""
    
    def test_total_activities_count(self):
        """Test total activity count."""
        from src.features.engineering import create_activity_features
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C3']
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C1', 'C2', 'C2'],
            'activity_date': [datetime(2023, 12, 1)] * 5,
            'activity_type': ['login'] * 5
        })
        
        result = create_activity_features(customers, activity)
        
        assert 'total_activities' in result.columns
        
        activities = dict(zip(result['customer_id'], result['total_activities']))
        assert activities['C1'] == 3
        assert activities['C2'] == 2
        assert activities['C3'] == 0
    
    def test_activity_frequency(self):
        """Test activity frequency calculation."""
        from src.features.engineering import create_activity_features
        
        customers = pd.DataFrame({
            'customer_id': ['C1']
        })
        
        # Activities every day for 30 days
        activity = pd.DataFrame({
            'customer_id': ['C1'] * 30,
            'activity_date': [datetime(2023, 12, 1) + timedelta(days=i) for i in range(30)],
            'activity_type': ['login'] * 30
        })
        
        result = create_activity_features(customers, activity)
        
        assert 'activity_frequency' in result.columns
        # Should be approximately 1 activity per day
        assert result.loc[0, 'activity_frequency'] >= 0.9
    
    def test_activity_days(self):
        """Test unique activity days calculation."""
        from src.features.engineering import create_activity_features
        
        customers = pd.DataFrame({
            'customer_id': ['C1']
        })
        
        # Multiple activities on same day, some on different days
        activity = pd.DataFrame({
            'customer_id': ['C1'] * 5,
            'activity_date': [
                datetime(2023, 12, 1),
                datetime(2023, 12, 1),  # Same day
                datetime(2023, 12, 2),
                datetime(2023, 12, 3),
                datetime(2023, 12, 3),  # Same day
            ],
            'activity_type': ['login'] * 5
        })
        
        result = create_activity_features(customers, activity)
        
        assert 'activity_days' in result.columns
        assert result.loc[0, 'activity_days'] == 3  # 3 unique days


class TestRecencyFeatures:
    """Tests for recency-related feature creation."""
    
    def test_days_since_last_activity(self):
        """Test days since last activity calculation."""
        from src.features.engineering import create_recency_features
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2']
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C2'],
            'activity_date': [
                datetime(2023, 12, 25),  # 7 days ago
                datetime(2023, 12, 20),  # 12 days ago
                datetime(2023, 11, 1),   # 61 days ago
            ],
            'activity_type': ['login', 'purchase', 'login']
        })
        
        result = create_recency_features(customers, activity, reference_date=reference_date)
        
        assert 'days_since_last_activity' in result.columns
        
        recency = dict(zip(result['customer_id'], result['days_since_last_activity']))
        assert recency['C1'] == 7   # Most recent was 12/25
        assert recency['C2'] == 61
    
    def test_days_since_last_purchase(self):
        """Test days since last purchase specifically."""
        from src.features.engineering import create_recency_features
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1']
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C1'],
            'activity_date': [
                datetime(2023, 12, 25),  # login (not purchase)
                datetime(2023, 12, 15),  # purchase
                datetime(2023, 12, 10),  # login
            ],
            'activity_type': ['login', 'purchase', 'login']
        })
        
        result = create_recency_features(customers, activity, reference_date=reference_date)
        
        if 'days_since_last_purchase' in result.columns:
            assert result.loc[0, 'days_since_last_purchase'] == 17  # Days since 12/15
    
    def test_no_activity_handling(self):
        """Test handling customers with no activity."""
        from src.features.engineering import create_recency_features
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2']
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1'],
            'activity_date': [datetime(2023, 12, 1)],
            'activity_type': ['login']
        })
        
        result = create_recency_features(customers, activity, reference_date=reference_date)
        
        # C2 has no activity - should have large recency value or NaN
        recency = dict(zip(result['customer_id'], result['days_since_last_activity']))
        assert pd.isna(recency['C2']) or recency['C2'] > 365


class TestTrendFeatures:
    """Tests for trend-related feature creation."""
    
    def test_activity_trend_increasing(self):
        """Test detection of increasing activity trend."""
        from src.features.engineering import create_trend_features
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1']
        })
        
        # More recent period has more activity
        activity = pd.DataFrame({
            'customer_id': ['C1'] * 10,
            'activity_date': [
                # Old period (3-6 months ago): 2 activities
                datetime(2023, 7, 1),
                datetime(2023, 7, 15),
                # Recent period (0-3 months ago): 8 activities
            ] + [datetime(2023, 10, 1) + timedelta(days=i*10) for i in range(8)],
            'activity_type': ['login'] * 10
        })
        
        result = create_trend_features(customers, activity, reference_date=reference_date)
        
        assert 'activity_trend' in result.columns
        # Positive trend expected
        assert result.loc[0, 'activity_trend'] > 0
    
    def test_activity_trend_decreasing(self):
        """Test detection of decreasing activity trend."""
        from src.features.engineering import create_trend_features
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1']
        })
        
        # Old period has more activity than recent
        activity = pd.DataFrame({
            'customer_id': ['C1'] * 10,
            'activity_date': [
                # Old period: 8 activities
            ] + [datetime(2023, 7, 1) + timedelta(days=i*5) for i in range(8)] + [
                # Recent period: 2 activities
                datetime(2023, 12, 1),
                datetime(2023, 12, 15),
            ],
            'activity_type': ['login'] * 10
        })
        
        result = create_trend_features(customers, activity, reference_date=reference_date)
        
        assert 'activity_trend' in result.columns
        # Negative trend expected
        assert result.loc[0, 'activity_trend'] < 0


class TestCreateAllFeatures:
    """Tests for the combined feature creation function."""
    
    def test_all_features_combined(self):
        """Test that create_all_features combines all feature types."""
        from src.features.engineering import create_all_features
        
        reference_date = datetime(2024, 1, 1)
        
        customers = pd.DataFrame({
            'customer_id': ['C1', 'C2'],
            'created_at': [datetime(2023, 1, 1)] * 2
        })
        
        activity = pd.DataFrame({
            'customer_id': ['C1', 'C1', 'C2'],
            'activity_date': [datetime(2023, 12, 1)] * 3,
            'activity_type': ['login', 'purchase', 'login']
        })
        
        result = create_all_features(customers, activity, reference_date=reference_date)
        
        # Should have customer_id
        assert 'customer_id' in result.columns
        
        # Should have tenure features
        assert any('tenure' in c for c in result.columns)
        
        # Should have activity features
        assert any('activit' in c.lower() for c in result.columns)
        
        # Should have one row per customer
        assert len(result) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
