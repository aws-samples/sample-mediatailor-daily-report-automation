#!/usr/bin/env python3
"""
Unit tests for derived metrics calculation.
Tests that fill rates are only calculated when explicitly requested.
"""

import sys
import os
import logging

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from lambda_function import calculate_derived_metrics

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_fill_rate_not_calculated_when_not_requested():
    """Test that Avail.FillRate is NOT calculated when not in requested_metrics"""

    # Mock metric data with duration components present
    metric_data = {
        'Avail.Duration': {'average': 30000, 'sum': 3000000},
        'Avail.FilledDuration': {'average': 15000, 'sum': 1500000}
    }

    # Request list WITHOUT Avail.FillRate
    requested_metrics = ['Avail.Duration', 'Avail.FilledDuration']

    # Call function
    derived = calculate_derived_metrics(metric_data, requested_metrics, logger, 'test-config')

    # Assert Avail.FillRate was NOT calculated
    assert 'Avail.FillRate' not in derived, "FAIL: Avail.FillRate should NOT be calculated"
    print("✓ PASS: Avail.FillRate not calculated when not requested")

def test_fill_rate_calculated_when_requested():
    """Test that Avail.FillRate IS calculated when in requested_metrics"""

    # Mock metric data with duration components present
    metric_data = {
        'Avail.Duration': {'average': 30000, 'sum': 3000000},
        'Avail.FilledDuration': {'average': 15000, 'sum': 1500000}
    }

    # Request list WITH Avail.FillRate
    requested_metrics = ['Avail.Duration', 'Avail.FilledDuration', 'Avail.FillRate']

    # Call function
    derived = calculate_derived_metrics(metric_data, requested_metrics, logger, 'test-config')

    # Assert Avail.FillRate WAS calculated
    assert 'Avail.FillRate' in derived, "FAIL: Avail.FillRate should be calculated"

    # Verify weighted calculation: (1500000 / 3000000) * 100 = 50%
    expected_rate = 50.0
    actual_rate = derived['Avail.FillRate']['average']
    assert actual_rate == expected_rate, f"FAIL: Expected {expected_rate}%, got {actual_rate}%"

    print(f"✓ PASS: Avail.FillRate calculated correctly: {actual_rate}%")

def test_ads_fill_rate_not_calculated_when_not_requested():
    """Test that AdDecisionServer.FillRate is NOT calculated when not requested"""

    metric_data = {
        'Avail.Duration': {'average': 30000, 'sum': 3000000},
        'AdDecisionServer.Duration': {'average': 20000, 'sum': 2000000}
    }

    requested_metrics = ['Avail.Duration', 'AdDecisionServer.Duration']

    derived = calculate_derived_metrics(metric_data, requested_metrics, logger, 'test-config')

    assert 'AdDecisionServer.FillRate' not in derived, "FAIL: AdDecisionServer.FillRate should NOT be calculated"
    print("✓ PASS: AdDecisionServer.FillRate not calculated when not requested")

def test_ads_fill_rate_calculated_when_requested():
    """Test that AdDecisionServer.FillRate IS calculated when requested"""

    metric_data = {
        'Avail.Duration': {'average': 30000, 'sum': 3000000},
        'AdDecisionServer.Duration': {'average': 20000, 'sum': 2000000}
    }

    requested_metrics = ['Avail.Duration', 'AdDecisionServer.Duration', 'AdDecisionServer.FillRate']

    derived = calculate_derived_metrics(metric_data, requested_metrics, logger, 'test-config')

    assert 'AdDecisionServer.FillRate' in derived, "FAIL: AdDecisionServer.FillRate should be calculated"

    # Verify: (2000000 / 3000000) * 100 = 66.7%
    expected_rate = 66.7
    actual_rate = derived['AdDecisionServer.FillRate']['average']
    assert abs(actual_rate - expected_rate) < 0.1, f"FAIL: Expected ~{expected_rate}%, got {actual_rate}%"

    print(f"✓ PASS: AdDecisionServer.FillRate calculated correctly: {actual_rate}%")

def test_observed_fill_rate_not_calculated_when_not_requested():
    """Test that Avail.ObservedFillRate is NOT calculated when not requested"""

    metric_data = {
        'Avail.ObservedDuration': {'average': 25000, 'sum': 2500000},
        'Avail.ObservedFilledDuration': {'average': 20000, 'sum': 2000000}
    }

    requested_metrics = ['Avail.ObservedDuration', 'Avail.ObservedFilledDuration']

    derived = calculate_derived_metrics(metric_data, requested_metrics, logger, 'test-config')

    assert 'Avail.ObservedFillRate' not in derived, "FAIL: Avail.ObservedFillRate should NOT be calculated"
    print("✓ PASS: Avail.ObservedFillRate not calculated when not requested")

def test_observed_fill_rate_calculated_when_requested():
    """Test that Avail.ObservedFillRate IS calculated when requested"""

    metric_data = {
        'Avail.ObservedDuration': {'average': 25000, 'sum': 2500000},
        'Avail.ObservedFilledDuration': {'average': 20000, 'sum': 2000000}
    }

    requested_metrics = ['Avail.ObservedDuration', 'Avail.ObservedFilledDuration', 'Avail.ObservedFillRate']

    derived = calculate_derived_metrics(metric_data, requested_metrics, logger, 'test-config')

    assert 'Avail.ObservedFillRate' in derived, "FAIL: Avail.ObservedFillRate should be calculated"

    # Verify: (2000000 / 2500000) * 100 = 80%
    expected_rate = 80.0
    actual_rate = derived['Avail.ObservedFillRate']['average']
    assert actual_rate == expected_rate, f"FAIL: Expected {expected_rate}%, got {actual_rate}%"

    print(f"✓ PASS: Avail.ObservedFillRate calculated correctly: {actual_rate}%")

def test_direct_campaign_workflow_simulation():
    """Simulate direct-sold campaign workflow - no fill rates should be calculated"""

    # Direct campaign config has duration metrics but NOT fill rates
    metric_data = {
        'Avail.Duration': {'average': 30000, 'sum': 3800000},  # 3.8M ms total
        'Avail.FilledDuration': {'average': 5000, 'sum': 500000},  # 500K ms filled (13% - low but normal)
        'AdDecisionServer.Ads': {'average': 10, 'sum': 1000},
        'AdDecisionServer.Latency': {'average': 250, 'sum': 25000},
        'AdDecisionServer.Errors': {'average': 0, 'sum': 0}
    }

    # Direct campaign requested metrics (no fill rates)
    requested_metrics = [
        'AdDecisionServer.Ads',
        'AdDecisionServer.Latency',
        'AdDecisionServer.Errors',
        'Avail.Duration',
        'Avail.FilledDuration',
        'Avail.Impression'
    ]

    derived = calculate_derived_metrics(metric_data, requested_metrics, logger, 'direct-campaign-config')

    # Should be empty - no derived metrics requested
    assert 'Avail.FillRate' not in derived, "FAIL: Should not calculate Avail.FillRate"
    assert 'AdDecisionServer.FillRate' not in derived, "FAIL: Should not calculate AdDecisionServer.FillRate"

    print("✓ PASS: Direct campaign workflow simulation - no fill rates calculated despite low 13% fill")

if __name__ == '__main__':
    print("\n=== Testing Derived Metrics Configuration ===\n")

    try:
        test_fill_rate_not_calculated_when_not_requested()
        test_fill_rate_calculated_when_requested()
        test_ads_fill_rate_not_calculated_when_not_requested()
        test_ads_fill_rate_calculated_when_requested()
        test_observed_fill_rate_not_calculated_when_not_requested()
        test_observed_fill_rate_calculated_when_requested()
        test_direct_campaign_workflow_simulation()

        print("\n✅ ALL TESTS PASSED\n")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
