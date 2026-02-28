"""
Unit tests for GeoHarness Spatial-Sync Phase 3 & 4 (API and Error Handling).
Focuses on 5 scenarios including Try/Except resilience and fallbacks.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
from api.server import app

client = TestClient(app)

# -----------------------------------------------------------------------------
# Scenario 1: Happy Path (Valid Coordinates + Gemini Success)
# -----------------------------------------------------------------------------
@patch("api.server.execute_gemini_correction_loop")
@patch("api.server.run_transformation_pipeline")
def test_api_transform_success(mock_transform, mock_gemini):
    """
    Test 1: Valid WGS84 coordinates inside Korea should return 200 OK 
    and output Harness metrics gracefully.
    """
    # Mock PyProj
    mock_transform.return_value = {
        "epsg5179": {"x": 1000000.0, "y": 2000000.0},
        "roundtrip": {"lat": 37.4979, "lng": 127.0276}
    }
    
    # Mock Gemini (Initial RMSE, Final RMSE, Score, Corrections, Reasoning, Status)
    mock_gemini.side_effect = [
        (1.5, 0, [], "", "skipped"), # First call (max_iterations=0)
        (0.2, 98, [{"lat_offset":0.0001, "lng_offset":-0.0001}], "Mock Reasoning", "success") # Second call
    ]

    response = client.post("/api/v1/transform", json={
        "latitude": 37.4979,
        "longitude": 127.0276,
        "run_harness": True
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["harness"]["gemini_status"] == "success"
    assert data["data"]["harness"]["harness_score"] == 98

# -----------------------------------------------------------------------------
# Scenario 2: Error Handle - Invalid Data Types (400 Bad Request)
# -----------------------------------------------------------------------------
def test_api_transform_invalid_types():
    """
    Test 2: Sending strings or nulls instead of floats should trigger 
    a 400 Bad Request error cleanly caught by our validation.
    """
    response = client.post("/api/v1/transform", json={
        "latitude": "invalid_string", 
        "longitude": None
    })
    
    # Wait, FastAPI automatically handles type coercion for floats if it's a string representation of a float.
    # But for arbitrary text or None, it will fail our manual type check or Pydantic (though we used manual typing in server.py).
    assert response.status_code == 400
    assert "INVALID_COORDINATES" in response.json()["detail"]

# -----------------------------------------------------------------------------
# Scenario 3: Error Handle - Out of Coverage (422 Unprocessable Entity)
# -----------------------------------------------------------------------------
def test_api_transform_out_of_bounds():
    """
    Test 3: Coordinates outside the Korean Bounding Box (e.g. Tokyo or NY)
    should trigger a 422 OUT_OF_COVERAGE exception.
    """
    # Tokyo coordinates
    response = client.post("/api/v1/transform", json={
        "latitude": 35.6895,
        "longitude": 139.6917
    })
    
    assert response.status_code == 422
    assert "OUT_OF_COVERAGE" in response.json()["detail"]

# -----------------------------------------------------------------------------
# Scenario 4: Error Handle & Fallback - Gemini API Timeout 
# -----------------------------------------------------------------------------
@patch("api.server.execute_gemini_correction_loop")
@patch("api.server.run_transformation_pipeline")
def test_api_transform_gemini_fallback(mock_transform, mock_gemini):
    """
    Test 4: If the LLM call times out or throws an error, the system must NOT crash 
    (500), but instead fallback to displaying RMSE heavily and setting status to timeout.
    """
    # Mock PyProj
    mock_transform.return_value = {
        "epsg5179": {"x": 1000000.0, "y": 2000000.0},
        "roundtrip": {"lat": 37.4979, "lng": 127.0276}
    }
    
    # Mock Gemini simulating a failure (returns status 'timeout_or_error')
    # Because our execute_gemini_correction_loop already has the try/except block 
    # to handle the failure and return gracefully.
    mock_gemini.side_effect = [
        (3.5, 0, [], "", "skipped"), # Init
        (3.5, 65, [], None, "timeout_or_error") # Fallback loop execution
    ]

    response = client.post("/api/v1/transform", json={
        "latitude": 37.4979,
        "longitude": 127.0276,
        "run_harness": True
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # The API didn't crash, it gracefully fell back!
    assert data["data"]["harness"]["gemini_status"] == "timeout_or_error"
    assert data["data"]["harness"]["rmse_after_m"] == 3.5

# -----------------------------------------------------------------------------
# Scenario 5: Try/Except Core Pipeline Failure (500 Internal Server Error)
# -----------------------------------------------------------------------------
@patch("api.server.run_transformation_pipeline")
def test_api_transform_internal_error(mock_transform):
    """
    Test 5: If the core PyProj pipeline completely explodes, the outer Try/Except 
    in server.py should catch it and return a structural 500 TRANSFORM_ERROR.
    """
    mock_transform.side_effect = Exception("Critical PyProj C-Binding Crash!")
    
    response = client.post("/api/v1/transform", json={
        "latitude": 37.4979,
        "longitude": 127.0276
    })

    assert response.status_code == 500
    assert "TRANSFORM_ERROR" in response.json()["detail"]
    assert "Critical PyProj" in response.json()["detail"]
