"""
Unit tests for GeoHarness Spatial-Sync Core Engines.
"""

import pytest
import sys
from unittest.mock import MagicMock

# --- Mock pyproj so tests run without the heavy binary ---
mock_pyproj = MagicMock()
mock_transformer = MagicMock()

# When we call 'transform' on the MOCK forward transformer
# lat 37.4, lng 127.0 => (1000000, 2000000) roughly
mock_transformer.transform.side_effect = lambda xx, yy: (1000000.0, 2000000.0) if hasattr(xx, 'conjugate') else (yy, xx)
mock_pyproj.Transformer.from_crs.return_value = mock_transformer

sys.modules['pyproj'] = mock_pyproj
# --------------------------------------------------------

from engine.metrics import haversine_m, calculate_rmse, calculate_harness_score
from engine.transform import transform_4326_to_5179, transform_5179_to_4326, run_transformation_pipeline

def test_haversine_distance():
    # Test distance between two known points (e.g., Gangnam Station to roughly 100m away)
    lat1, lng1 = 37.49794, 127.02764
    # Roughly a 111-meter offset north
    lat2, lng2 = 37.49894, 127.02764
    
    distance = haversine_m(lat1, lng1, lat2, lng2)
    # 0.001 degree of latitude is roughly 111.32 meters
    assert 110 < distance < 112

def test_calculate_harness_score():
    assert calculate_harness_score(0.0) == 100
    assert calculate_harness_score(0.3) == 97
    assert calculate_harness_score(1.0) == 90
    assert calculate_harness_score(5.0) == 50
    assert calculate_harness_score(10.0) == 0
    assert calculate_harness_score(12.0) == 0  # Should not go below 0

def test_calculate_rmse():
    coords = [{"lat": 37.0, "lng": 127.0}, {"lat": 37.1, "lng": 127.1}]
    # same coords should have 0 RMSE
    assert calculate_rmse(coords, coords) == 0.0

def test_pyproj_transformation_roundtrip():
    lat, lng = 37.49794, 127.02764
    
    # We mock the return logic inside Python directly 
    # Mocking Transformer.from_crs outputs
    mock_transformer.transform.side_effect = [
        (1000000.0, 2000000.0), # Forward x, y
        (127.02764, 37.49794)   # Reverse lon, lat
    ]

    result = run_transformation_pipeline(lat, lng)
    
    assert "x" in result["epsg5179"]
    assert "y" in result["epsg5179"]
    assert result["epsg5179"]["x"] == 1000000.0
    
    rt_lat = result["roundtrip"]["lat"]
    rt_lng = result["roundtrip"]["lng"]
    
    assert abs(lat - rt_lat) < 0.000001
    assert abs(lng - rt_lng) < 0.000001
