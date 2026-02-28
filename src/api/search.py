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
from engine.metrics import haversine_m
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
        
    # API keys
    naver_search_id = settings.NAVER_SEARCH_CLIENT_ID
    naver_search_secret = settings.NAVER_SEARCH_CLIENT_SECRET
    ncp_id = settings.NAVER_CLIENT_ID
    ncp_secret = settings.NAVER_CLIENT_SECRET

    # Prepare Tasks
    google_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    google_params = {
        "query": full_query,
        "key": api_key,
        "language": "ko",
        "region": "kr",
    }

    # 1차: Naver Search Local API (장소명 검색에 최적)
    naver_search_url = "https://openapi.naver.com/v1/search/local.json"
    naver_search_headers = {
        "X-Naver-Client-Id": naver_search_id,
        "X-Naver-Client-Secret": naver_search_secret,
    }
    naver_search_params = {"query": full_query, "display": 1}
    use_naver_search = bool(naver_search_id and naver_search_secret)

    try:
        import asyncio
        async with aiohttp.ClientSession() as session:
            g_task = session.get(google_url, params=google_params)

            if use_naver_search:
                n_task = session.get(
                    naver_search_url,
                    headers=naver_search_headers,
                    params=naver_search_params,
                )
                g_resp, n_resp = await asyncio.gather(g_task, n_task)
            else:
                g_resp = await g_task
                n_resp = None

            if g_resp.status != 200:
                return {"error": f"Google API error: {g_resp.status}", "places": []}
            data = await g_resp.json()

            naver_search_data = None
            if n_resp and n_resp.status == 200:
                naver_search_data = await n_resp.json()

        results = data.get("results", [])
        places = []

        # 1차: Naver Search Local API 좌표 파싱 (mapx/mapy = WGS84 × 10^7)
        n_lat, n_lng = None, None
        if naver_search_data:
            items = naver_search_data.get("items", [])
            if items:
                try:
                    raw_x = int(items[0].get("mapx", 0))
                    raw_y = int(items[0].get("mapy", 0))
                    if raw_x and raw_y:
                        n_lng = raw_x / 10_000_000.0
                        n_lat = raw_y / 10_000_000.0
                        if not (33.0 <= n_lat <= 43.0 and 124.0 <= n_lng <= 132.0):
                            n_lat, n_lng = None, None
                except (ValueError, TypeError):
                    pass

        # 2차 폴백: NCP Geocoding (Naver Search 실패 시, formatted_address로 재시도)
        if n_lat is None and ncp_id and ncp_secret and results:
            address_str = results[0].get("formatted_address", "")
            if address_str:
                ncp_url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
                ncp_headers = {
                    "X-NCP-APIGW-API-KEY-ID": ncp_id,
                    "X-NCP-APIGW-API-KEY": ncp_secret,
                }
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            ncp_url,
                            headers=ncp_headers,
                            params={"query": address_str},
                        ) as ncp_resp:
                            if ncp_resp.status == 200:
                                ncp_data = await ncp_resp.json()
                                addrs = ncp_data.get("addresses", [])
                                if addrs:
                                    n_lng = float(addrs[0]["x"])
                                    n_lat = float(addrs[0]["y"])
                                    if not (33.0 <= n_lat <= 43.0 and 124.0 <= n_lng <= 132.0):
                                        n_lat, n_lng = None, None
                except Exception as e:
                    logger.warning(f"NCP Geocoding fallback failed: {e}")

        for place in results[:5]:  # 상위 5건만
            geo = place.get("geometry", {}).get("location", {})
            g_lat = geo.get("lat", 0)
            g_lng = geo.get("lng", 0)

            # ML 보정
            correction = predict_offset(g_lat, g_lng)

            # 보정 거리 계산
            dist_m = haversine_m(g_lat, g_lng, correction["corrected_lat"], correction["corrected_lng"])

            # Sync 거리 및 점수 계산 (Naver 좌표가 있을 경우)
            sync_score = None
            naver_location = None
            if n_lat is not None and n_lng is not None:
                naver_location = {"lat": n_lat, "lng": n_lng}
                sync_dist_m = haversine_m(correction["corrected_lat"], correction["corrected_lng"], n_lat, n_lng)
                # 0m = 100%, 5m = 95%, 10m = 90%
                sync_score = max(0, 100 - sync_dist_m)

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
                "naver_location": naver_location,
                "sync_score": round(sync_score, 1) if sync_score is not None else None,
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
