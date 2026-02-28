"""
GeoHarness v2.0: Local Verifier API

보정된 좌표를 받아 네이버 역지오코딩을 수행하고,
"구글에서 X번지인데 실제로는 Y상점 옆 Z번지" 라는 정보를 반환합니다.

엔드포인트:
    POST /api/v1/predict-offset
    POST /api/v1/verify-location
"""

import logging
from typing import Dict, Optional

import aiohttp
from fastapi import APIRouter

from engine.inference import predict_offset, get_model_status
from shared.config import settings

logger = logging.getLogger("LocalVerifier")

router = APIRouter(prefix="/api/v1", tags=["offset-correction"])


@router.get("/model-status")
async def model_status():
    """ML 모델 상태 조회"""
    return get_model_status()


@router.post("/predict-offset")
async def api_predict_offset(payload: dict):
    """
    Google WGS84 좌표 → ML 보정 좌표 반환

    Request:
        { "lat": 37.5442, "lng": 127.0499 }

    Response:
        {
            "original": { "lat": 37.5442, "lng": 127.0499 },
            "corrected": { "lat": 37.5443, "lng": 127.0501 },
            "method": "ml",
            "confidence": 0.92,
            "details": { ... }
        }
    """
    lat = payload.get("lat")
    lng = payload.get("lng")

    if lat is None or lng is None:
        return {"error": "lat/lng required"}

    result = predict_offset(float(lat), float(lng))

    return {
        "original": {"lat": lat, "lng": lng},
        "corrected": {
            "lat": result["corrected_lat"],
            "lng": result["corrected_lng"],
        },
        "method": result["method"],
        "confidence": result["confidence"],
        "details": result["details"],
    }


@router.post("/verify-location")
async def verify_location(payload: dict):
    """
    Google 좌표 → ML 보정 → 네이버 역지오코딩 → 실제 상호 반환

    Request:
        { "lat": 37.5442, "lng": 127.0499, "poi_name": "하이라인 성수" }

    Response:
        {
            "google_poi": "하이라인 성수",
            "original": { "lat": 37.5442, "lng": 127.0499 },
            "corrected": { "lat": 37.5443, "lng": 127.0501 },
            "naver_result": { "name": "하이라인", "address": "서울시 성동구..." },
            "offset_distance_m": 12.3,
            "harness_score": 88
        }
    """
    lat = payload.get("lat")
    lng = payload.get("lng")
    poi_name = payload.get("poi_name", "")

    if lat is None or lng is None:
        return {"error": "lat/lng required"}

    # Step 1: ML 보정
    correction = predict_offset(float(lat), float(lng))

    # Step 2: 네이버 역지오코딩 (API 키 있으면)
    naver_result = None
    if settings.NAVER_CLIENT_ID and not settings.NAVER_CLIENT_ID.startswith("your-"):
        naver_result = await _search_naver_at_coords(
            correction["corrected_lat"],
            correction["corrected_lng"],
            poi_name,
        )

    # Step 3: Harness Score 계산
    from engine.metrics import haversine_m, calculate_harness_score
    offset_dist = haversine_m(
        float(lat), float(lng),
        correction["corrected_lat"], correction["corrected_lng"]
    )
    harness = calculate_harness_score(offset_dist)

    return {
        "google_poi": poi_name,
        "original": {"lat": lat, "lng": lng},
        "corrected": {
            "lat": correction["corrected_lat"],
            "lng": correction["corrected_lng"],
        },
        "method": correction["method"],
        "naver_result": naver_result,
        "offset_distance_m": round(offset_dist, 2),
        "harness_score": harness,
    }


async def _search_naver_at_coords(lat: float, lng: float, query: str) -> Optional[Dict]:
    """네이버 지역 검색 API로 보정된 좌표 근처의 상호 검색"""
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": query or f"{lat},{lng}", "display": 1}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                items = data.get("items", [])
                if not items:
                    return None
                first = items[0]
                return {
                    "name": first.get("title", "").replace("<b>", "").replace("</b>", ""),
                    "address": first.get("address", ""),
                    "road_address": first.get("roadAddress", ""),
                }
    except Exception as e:
        logger.error(f"Naver search error: {e}")
        return None
