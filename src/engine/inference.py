"""
GeoHarness v2.0: ML Inference Engine

보정 함수: Google WGS84 좌표 → 보정된 좌표 반환
- decoder.pkl 모델이 있으면 ML 추론으로 오프셋 보정
- 없으면 PyProj 기본 변환으로 fallback

사용법:
    from engine.inference import predict_offset

    result = predict_offset(37.5442, 127.0499)
    # → { "corrected_lat": ..., "corrected_lng": ..., "method": "ml", "confidence": 0.95 }
"""

import logging
import math
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("Inference")

# 모델 캐시 + 핫리로드 (파일 수정 시 자동 갱신)
_model_cache: Optional[Dict] = None
_model_mtime: float = 0.0
_MODEL_PATH = "src/models/decoder.pkl"


def _load_model() -> Optional[Dict]:
    """
    decoder.pkl 모델 번들 로드 (lazy loading + hot-reload)
    형섭님이 새 pkl을 갈아끼우면 서버 재시작 없이 자동 반영됩니다.
    """
    global _model_cache, _model_mtime

    model_path = Path(_MODEL_PATH)
    if not model_path.exists():
        if _model_cache is not None:
            logger.warning("decoder.pkl deleted — clearing cache, falling back to PyProj")
            _model_cache = None
        return None

    # 핫리로드: 파일 수정 시간이 바뀌었으면 다시 로드
    current_mtime = model_path.stat().st_mtime
    if _model_cache is not None and current_mtime == _model_mtime:
        return _model_cache

    try:
        import joblib
        _model_cache = joblib.load(str(model_path))
        _model_mtime = current_mtime
        n_samples = _model_cache.get('n_samples', '?')
        logger.info(f"✅ Model loaded from {_MODEL_PATH} (samples: {n_samples})")
        logger.info(f"   Features: {_model_cache.get('feature_cols', [])}")
        logger.info(f"   RMSE: x={_model_cache.get('rmse_x', '?'):.6f}, y={_model_cache.get('rmse_y', '?'):.6f}")
        return _model_cache
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None


def _haversine_m(lat1, lng1, lat2, lng2):
    """두 WGS84 좌표 간 거리 (미터)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 방위각 (degrees)"""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lng2 - lng1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _compute_anchor_features(g_lat: float, g_lng: float, anchors: List[Dict]) -> tuple:
    """가장 가까운 기준점 3개까지의 (거리, 방향각) 계산"""
    if not anchors or len(anchors) < 3:
        return (0.0, 0.0) * 3

    relations = []
    for a in anchors:
        d = _haversine_m(g_lat, g_lng, a["lat"], a["lng"])
        b = _bearing(g_lat, g_lng, a["lat"], a["lng"])
        relations.append((d, b))
    
    relations.sort(key=lambda x: x[0])
    
    r1, r2, r3 = relations[0], relations[1], relations[2]
    return r1[0], r1[1], r2[0], r2[1], r3[0], r3[1]


def _fallback_pyproj(g_lat: float, g_lng: float) -> Dict:
    """PyProj 기본 변환 fallback (ML 모델 없을 때)"""
    try:
        from pyproj import Transformer
        wgs_to_tm = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
        tm_to_wgs = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

        tm_x, tm_y = wgs_to_tm.transform(g_lng, g_lat)
        back_lng, back_lat = tm_to_wgs.transform(tm_x, tm_y)

        return {
            "corrected_lat": back_lat,
            "corrected_lng": back_lng,
            "method": "pyproj_fallback",
            "confidence": 0.6,
            "details": {
                "tm_x": round(tm_x, 4),
                "tm_y": round(tm_y, 4),
                "note": "ML 모델 미로드 — PyProj 순수 투영 사용",
            },
        }
    except Exception as e:
        logger.error(f"PyProj fallback failed: {e}")
        return {
            "corrected_lat": g_lat,
            "corrected_lng": g_lng,
            "method": "identity",
            "confidence": 0.0,
            "details": {"error": str(e)},
        }


def predict_offset(g_lat: float, g_lng: float) -> Dict:
    """
    Google WGS84 좌표를 보정된 좌표로 변환.

    Returns:
        {
            "corrected_lat": float,
            "corrected_lng": float,
            "method": "ml" | "pyproj_fallback" | "identity",
            "confidence": float (0-1),
            "details": { ... }
        }
    """
    model = _load_model()

    if model is None:
        return _fallback_pyproj(g_lat, g_lng)

    try:
        import numpy as np

        feature_cols = model["feature_cols"]
        anchors = model.get("anchors", [])

        # Feature 구성
        features = [g_lat, g_lng]
        if "anchor1_dist" in feature_cols and anchors:
            a_features = _compute_anchor_features(g_lat, g_lng, anchors)
            features.extend(a_features)

        X = np.array([features])

        # 추론
        delta_x = float(model["model_x"].predict(X)[0])
        delta_y = float(model["model_y"].predict(X)[0])

        corrected_lng = g_lng + delta_x
        corrected_lat = g_lat + delta_y

        return {
            "corrected_lat": corrected_lat,
            "corrected_lng": corrected_lng,
            "method": "ml",
            "confidence": max(0.5, 1.0 - (model.get("rmse_x", 1.0) + model.get("rmse_y", 1.0)) / 2),
            "details": {
                "delta_x": round(delta_x, 8),
                "delta_y": round(delta_y, 8),
                "model_rmse_x": model.get("rmse_x"),
                "model_rmse_y": model.get("rmse_y"),
                "n_training_samples": model.get("n_samples"),
                "gpu_trained": model.get("gpu_trained"),
            },
        }
    except Exception as e:
        logger.error(f"ML inference failed: {e}")
        return _fallback_pyproj(g_lat, g_lng)


def get_model_status() -> Dict:
    """현재 모델 상태 조회 (API 헬스체크용)"""
    model = _load_model()
    if model is None:
        return {
            "loaded": False,
            "path": _MODEL_PATH,
            "fallback": "pyproj",
        }
    return {
        "loaded": True,
        "path": _MODEL_PATH,
        "features": model.get("feature_cols", []),
        "rmse_x": model.get("rmse_x"),
        "rmse_y": model.get("rmse_y"),
        "n_samples": model.get("n_samples"),
        "gpu_trained": model.get("gpu_trained"),
    }
