"""
Core RMSE and Harness Score calculation utilities.
"""

from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Any, List

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the distance in meters between two WGS84 coordinates.
    """
    R = 6371000  # Radius of Earth in meters
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

def calculate_harness_score(rmse_m: float) -> int:
    """
    Convert the RMSE in meters into a Harness Quality Score (0-100).
    
    Formula: max(0, 100 - (RMSE_m * 10))
    - RMSE 0.0m -> 100
    - RMSE 0.3m -> 97
    - RMSE 1.0m -> 90
    - RMSE 5.0m -> 50
    - RMSE 10m+ -> 0
    """
    score = 100 - (rmse_m * 10)
    return int(max(0, min(100, score)))

def calculate_rmse(coords_list: List[Dict[str, float]], ground_truth_list: List[Dict[str, float]]) -> float:
    """
    Calculate the Root Mean Square Error (RMSE) in meters across a list of coordinate pairs.
    """
    if len(coords_list) != len(ground_truth_list) or len(coords_list) == 0:
        raise ValueError("Coordinate lists must have the same non-zero length")

    errors_sq = [
        haversine_m(c["lat"], c["lng"], g["lat"], g["lng"])**2
        for c, g in zip(coords_list, ground_truth_list)
    ]
    return sqrt(sum(errors_sq) / len(errors_sq))
