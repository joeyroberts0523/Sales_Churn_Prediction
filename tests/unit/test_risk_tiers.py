"""
Unit tests for risk tier classification.

Covers:
- Risk tier boundary conditions
- Threshold crossing detection
- Risk distribution calculations
"""

import pytest
import pandas as pd
import numpy as np


class TestClassifyRiskTier:
    """Tests for risk tier classification function."""
    
    def test_critical_tier(self):
        """Test Critical tier classification (probability >= 0.80)."""
        from src.scoring.risk_tiers import classify_risk_tier
        
        assert classify_risk_tier(0.80) == 'Critical'
        assert classify_risk_tier(0.85) == 'Critical'
        assert classify_risk_tier(0.99) == 'Critical'
        assert classify_risk_tier(1.0) == 'Critical'
    
    def test_high_tier(self):
        """Test High tier classification (0.60 <= probability < 0.80)."""
        from src.scoring.risk_tiers import classify_risk_tier
        
        assert classify_risk_tier(0.60) == 'High'
        assert classify_risk_tier(0.70) == 'High'
        assert classify_risk_tier(0.79) == 'High'
    
    def test_medium_tier(self):
        """Test Medium tier classification (0.40 <= probability < 0.60)."""
        from src.scoring.risk_tiers import classify_risk_tier
        
        assert classify_risk_tier(0.40) == 'Medium'
        assert classify_risk_tier(0.50) == 'Medium'
        assert classify_risk_tier(0.59) == 'Medium'
    
    def test_low_tier(self):
        """Test Low tier classification (probability < 0.40)."""
        from src.scoring.risk_tiers import classify_risk_tier
        
        assert classify_risk_tier(0.0) == 'Low'
        assert classify_risk_tier(0.20) == 'Low'
        assert classify_risk_tier(0.39) == 'Low'
    
    def test_boundary_values(self):
        """Test exact boundary values."""
        from src.scoring.risk_tiers import classify_risk_tier
        
        # Test exact boundaries
        assert classify_risk_tier(0.40) == 'Medium'  # Not Low
        assert classify_risk_tier(0.60) == 'High'    # Not Medium
        assert classify_risk_tier(0.80) == 'Critical'  # Not High
    
    def test_invalid_probability(self):
        """Test handling of invalid probability values."""
        from src.scoring.risk_tiers import classify_risk_tier
        
        # Should handle edge cases gracefully
        assert classify_risk_tier(0.0) == 'Low'
        
        # Negative probabilities should raise or be handled
        with pytest.raises((ValueError, AssertionError)):
            classify_risk_tier(-0.1)
        
        # Probabilities > 1 should raise or be handled
        with pytest.raises((ValueError, AssertionError)):
            classify_risk_tier(1.1)
    
    def test_vectorized_classification(self):
        """Test classification on arrays/series."""
        from src.scoring.risk_tiers import classify_risk_tier
        
        probabilities = pd.Series([0.10, 0.45, 0.65, 0.90])
        
        # Should work with apply
        tiers = probabilities.apply(classify_risk_tier)
        
        assert tiers.iloc[0] == 'Low'
        assert tiers.iloc[1] == 'Medium'
        assert tiers.iloc[2] == 'High'
        assert tiers.iloc[3] == 'Critical'


class TestDetectThresholdCrossings:
    """Tests for threshold crossing detection."""
    
    def test_crossing_into_high(self):
        """Test detection of crossing into High risk."""
        from src.scoring.risk_tiers import detect_threshold_crossings
        
        # Previous: 0.55 (Medium), Current: 0.65 (High)
        current = pd.Series([0.65])
        previous = pd.Series([0.55])
        
        crossings = detect_threshold_crossings(current, previous, threshold=0.60)
        
        assert crossings.iloc[0] == True
    
    def test_no_crossing(self):
        """Test when there's no threshold crossing."""
        from src.scoring.risk_tiers import detect_threshold_crossings
        
        # Both in same tier
        current = pd.Series([0.70])
        previous = pd.Series([0.65])
        
        crossings = detect_threshold_crossings(current, previous, threshold=0.60)
        
        assert crossings.iloc[0] == False
    
    def test_crossing_downward(self):
        """Test that downward crossings are not flagged (by default)."""
        from src.scoring.risk_tiers import detect_threshold_crossings
        
        # Previous: High, Current: Medium
        current = pd.Series([0.55])
        previous = pd.Series([0.65])
        
        crossings = detect_threshold_crossings(current, previous, threshold=0.60)
        
        # By default, only upward crossings should be flagged
        assert crossings.iloc[0] == False
    
    def test_missing_previous(self):
        """Test handling of missing previous predictions."""
        from src.scoring.risk_tiers import detect_threshold_crossings
        
        current = pd.Series([0.65])
        previous = pd.Series([np.nan])
        
        crossings = detect_threshold_crossings(current, previous, threshold=0.60)
        
        # Can't determine crossing without previous value
        assert crossings.iloc[0] == False
    
    def test_multiple_customers(self):
        """Test batch detection for multiple customers."""
        from src.scoring.risk_tiers import detect_threshold_crossings
        
        current = pd.Series([0.65, 0.55, 0.85, 0.70])
        previous = pd.Series([0.55, 0.55, 0.75, 0.75])
        
        crossings = detect_threshold_crossings(current, previous, threshold=0.60)
        
        assert crossings.iloc[0] == True   # Crossed into High
        assert crossings.iloc[1] == False  # No crossing
        assert crossings.iloc[2] == True   # Crossed into Critical
        assert crossings.iloc[3] == False  # Already in High


class TestGetRiskDistribution:
    """Tests for risk distribution calculations."""
    
    def test_distribution_calculation(self):
        """Test basic distribution calculation."""
        from src.scoring.risk_tiers import get_risk_distribution
        
        risk_tiers = pd.Series(['Low', 'Low', 'Medium', 'High', 'Critical'])
        
        dist = get_risk_distribution(risk_tiers)
        
        assert dist['Low'] == 2
        assert dist['Medium'] == 1
        assert dist['High'] == 1
        assert dist['Critical'] == 1
    
    def test_distribution_percentages(self):
        """Test distribution as percentages."""
        from src.scoring.risk_tiers import get_risk_distribution
        
        risk_tiers = pd.Series(['Low'] * 40 + ['Medium'] * 30 + ['High'] * 20 + ['Critical'] * 10)
        
        dist = get_risk_distribution(risk_tiers, as_percentage=True)
        
        assert dist['Low'] == 40.0
        assert dist['Medium'] == 30.0
        assert dist['High'] == 20.0
        assert dist['Critical'] == 10.0
    
    def test_empty_tiers(self):
        """Test handling when some tiers have no customers."""
        from src.scoring.risk_tiers import get_risk_distribution
        
        risk_tiers = pd.Series(['Low', 'Low', 'Critical'])  # No Medium or High
        
        dist = get_risk_distribution(risk_tiers)
        
        assert dist['Low'] == 2
        assert dist.get('Medium', 0) == 0
        assert dist.get('High', 0) == 0
        assert dist['Critical'] == 1


class TestRiskTierOrderConsistency:
    """Tests to ensure risk tier ordering is consistent."""
    
    def test_tier_order(self):
        """Test that tiers are ordered by increasing risk."""
        from src.scoring.risk_tiers import RISK_TIER_ORDER
        
        # RISK_TIER_ORDER should be defined in the module
        expected_order = ['Low', 'Medium', 'High', 'Critical']
        assert RISK_TIER_ORDER == expected_order
    
    def test_threshold_ordering(self):
        """Test that thresholds create non-overlapping ranges."""
        from src.utils.config import get_config
        
        config = get_config()
        
        # Thresholds should be strictly increasing
        assert config.risk_tiers.MEDIUM_THRESHOLD < config.risk_tiers.HIGH_THRESHOLD
        assert config.risk_tiers.HIGH_THRESHOLD < config.risk_tiers.CRITICAL_THRESHOLD


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
