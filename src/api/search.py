"""
GeoHarness v5.0: Place Search API

사용자가 장소명을 검색하면:
1. Google Places Text Search로 WGS84 좌표를 가져오고
2. ML decoder로 보정된 좌표를 계산하고
3. 원본 + 보정 좌표 + 메타데이터를 반환합니다.
"""

import logging
import time
from typing import Dict, Optional
from functools import lru_cache

import aiohttp
from fastapi import APIRouter, Query

from engine.inference import predict_offset
from shared.config import settings

logger = logging.getLogger("SearchAPI")

router = APIRouter(prefix="/api/v1", tags=["search"])

# 간단한 메모리 캐시 (TTL 기반)
_search_cache: Dict[str, dict] = {}
_cache_timestamps: Dict[str, float] = {}
CACHE_TTL = 3600  # 1시간


def _get_cached(key: str) -> Optional[dict]:
    if key in _search_cache:
        if time.time() - _cache_timestamps[key] < CACHE_TTL:
            return _search_cache[key]
        else:
            del _search_cache[key]
            del _cache_timestamps[key]
    return None


def _set_cache(key: str, value: dict):
    _search_cache[key] = value
    _cache_timestamps[key] = time.time()


@router.post("/search")
async def search_place(payload: dict):
    """
    장소 텍스트 검색 → Google Places → ML 보정

    Request: { "query": "하이라인 카페", "region": "성수동" }
    Response: {
        "places": [{
            "name": "하이라인",
            "address": "서울시 성동구...",
            "original": { "lat": 37.5442, "lng": 127.0499 },
            "corrected": { "lat": 37.5443, "lng": 127.0501 },
            "correction_distance_m": 12.3,
            "confidence": 0.92,
            "method": "ml"
        }]
    }
    """
    query = payload.get("query", "")
    region = payload.get("region", "성수동")

    if not query:
        return {"error": "query is required", "places": []}

    full_query = f"{query} {region}" if region else query

    # 캐시 확인
    cached = _get_cached(full_query)
    if cached:
        logger.info(f"Cache hit: {full_query}")
        return cached

    api_key = settings.GOOGLE_MAPS_KEY
    if not api_key:
        return {"error": "GOOGLE_MAPS_KEY not configured", "places": []}

    # Google Places Text Search (New API)
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": full_query,
        "key": api_key,
        "language": "ko",
        "region": "kr",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return {"error": f"Google API error: {resp.status}", "places": []}
                data = await resp.json()

        results = data.get("results", [])
        places = []

        for place in results[:5]:  # 상위 5건만
            geo = place.get("geometry", {}).get("location", {})
            g_lat = geo.get("lat", 0)
            g_lng = geo.get("lng", 0)

            # ML 보정
            correction = predict_offset(g_lat, g_lng)

            # 보정 거리 계산
            import math
            R = 6371000
            dlat = math.radians(correction["corrected_lat"] - g_lat)
            dlng = math.radians(correction["corrected_lng"] - g_lng)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(g_lat)) * math.cos(math.radians(correction["corrected_lat"])) * math.sin(dlng/2)**2
            dist_m = 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

            places.append({
                "name": place.get("name", ""),
                "address": place.get("formatted_address", ""),
                "place_id": place.get("place_id", ""),
                "types": place.get("types", []),
                "rating": place.get("rating"),
                "original": {"lat": g_lat, "lng": g_lng},
                "corrected": {
                    "lat": correction["corrected_lat"],
                    "lng": correction["corrected_lng"],
                },
                "correction_distance_m": round(dist_m, 1),
                "confidence": correction["confidence"],
                "method": correction["method"],
            })

        response = {"places": places, "query": full_query, "total": len(places)}
        _set_cache(full_query, response)
        return response

    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"error": str(e), "places": []}


@router.get("/search/autocomplete")
async def autocomplete(q: str = Query("", min_length=1)):
    """Google Places Autocomplete"""
    api_key = settings.GOOGLE_MAPS_KEY
    if not api_key or not q:
        return {"predictions": []}

    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": q,
        "key": api_key,
        "language": "ko",
        "components": "country:kr",
        "types": "establishment",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return {"predictions": []}
                data = await resp.json()

        predictions = [
            {
                "description": p.get("description", ""),
                "place_id": p.get("place_id", ""),
                "main_text": p.get("structured_formatting", {}).get("main_text", ""),
            }
            for p in data.get("predictions", [])[:5]
        ]
        return {"predictions": predictions}

    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        return {"predictions": []}
