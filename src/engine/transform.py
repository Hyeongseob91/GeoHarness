"""
Coordinate Transformation Utilities relying on pyproj.
MVP Goal: Transform WGS84 (EPSG:4326) to Korean Projection (EPSG:5179) and back.
"""

from typing import Dict, Tuple, Any
from pyproj import Transformer

# Initialize Transformers once to avoid overhead
# always_xy=True forces input/output to be (lon, lat) / (x, y) rather than (lat, lon)
TRANSFORM_FWD = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
TRANSFORM_REV = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)


def transform_4326_to_5179(lat: float, lng: float) -> Tuple[float, float]:
    """
    Transform EPSG:4326 (lat, lng) to EPSG:5179 (x, y).
    always_xy expects (lon, lat) order!
    """
    x, y = TRANSFORM_FWD.transform(xx=lng, yy=lat)
    return x, y


def transform_5179_to_4326(x: float, y: float) -> Tuple[float, float]:
    """
    Transform EPSG:5179 (x, y) back to EPSG:4326 (lat, lng).
    always_xy returns (lon, lat).
    """
    lon, lat = TRANSFORM_REV.transform(xx=x, yy=y)
    return lat, lon


def run_transformation_pipeline(lat: float, lng: float) -> Dict[str, Any]:
    """
    Takes input lat/lng, converts to EPSG:5179, and then converts back
    to 4326 to verify round-trip accuracy.
    """
    x, y = transform_4326_to_5179(lat, lng)
    lat_rt, lng_rt = transform_5179_to_4326(x, y)
    
    return {
        "epsg5179": {"x": x, "y": y},
        "roundtrip": {"lat": lat_rt, "lng": lng_rt}
    }
