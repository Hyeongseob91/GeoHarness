"""
GeoHarness v3.0: Naver NCP Geocoding Collector

목적:
NCP Geocoding API를 사용하여 Google에서 추출한 POI 이름으로
네이버 지도의 WGS84 좌표를 수집합니다.

API 신청:
    https://console.ncloud.com → Maps > Geocoding 활성화
    - Client ID와 Client Secret 발급받아 .env에 설정

사용법:
    1. data/google_poi_base.csv 가 먼저 존재해야 합니다.
    2. .env에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET을 설정합니다.
    3. python src/ml/naver_collector.py 실행
"""

import asyncio
import csv
import logging
import random
from pathlib import Path
from typing import List, Dict

import aiohttp
from dotenv import load_dotenv

from shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NaverCollector")

load_dotenv()


async def search_naver_local(session: aiohttp.ClientSession, query: str) -> Dict | None:
    """
    NCP Geocoding API로 장소명 → WGS84 좌표 조회

    Returns: { n_name, n_lng (WGS84), n_lat (WGS84), n_address, n_road_address }
    """
    if not settings.NAVER_CLIENT_ID or settings.NAVER_CLIENT_ID.startswith("your-"):
        logger.warning("NAVER_CLIENT_ID is missing. Skipping Naver geocoding.")
        return None
    if not settings.NAVER_CLIENT_SECRET or settings.NAVER_CLIENT_SECRET.startswith("your-"):
        logger.warning("NAVER_CLIENT_SECRET is missing. Skipping Naver geocoding.")
        return None

    url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": settings.NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": query}

    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                logger.warning(f"[NCP] Geocoding failed for '{query}' with status: {response.status}")
                return None

            data = await response.json()
            addresses = data.get("addresses", [])
            if not addresses:
                return None

            first = addresses[0]
            n_lng = float(first["x"])
            n_lat = float(first["y"])
            return {
                "n_name": query,
                "n_lng": n_lng,
                "n_lat": n_lat,
                "n_address": first.get("jibunAddress", ""),
                "n_road_address": first.get("roadAddress", ""),
            }
    except Exception as e:
        logger.error(f"[NCP] Error geocoding '{query}': {e}")
        return None


async def build_naver_paired_dataset(
    google_csv_path: str = "data/google_poi_base.csv",
    output_path: str = "data/ml_dataset.csv"
):
    """
    Google POI 기준 데이터를 읽어서 NCP Geocoding API로 매칭하여
    최종 ML 학습 데이터셋을 생성합니다.

    Output columns:
        poi_name, g_lat, g_lng, n_lat, n_lng, n_name, n_address, poi_type, search_region
    """
    logger.info("Building Naver-paired ML Dataset...")

    if not Path(google_csv_path).exists():
        logger.error(f"Google base CSV not found: {google_csv_path}. Run dataset_generator.py first.")
        return

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Read Google base data
    with open(google_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        google_pois = list(reader)

    logger.info(f"Loaded {len(google_pois)} Google POIs from {google_csv_path}")

    dataset = []
    matched_count = 0

    async with aiohttp.ClientSession() as session:
        for i, poi in enumerate(google_pois):
            # Use the POI name + region context for better matching
            region_prefix = poi["search_region"].split(" ")[0]
            search_query = f"{region_prefix} {poi['poi_name']}"

            naver_result = await search_naver_local(session, search_query)

            if naver_result and naver_result["n_lat"] and naver_result["n_lng"]:
                dataset.append({
                    "poi_name": poi["poi_name"],
                    "g_lat": float(poi["g_lat"]),
                    "g_lng": float(poi["g_lng"]),
                    "n_lat": naver_result["n_lat"],
                    "n_lng": naver_result["n_lng"],
                    "n_name": naver_result["n_name"],
                    "n_address": naver_result["n_address"],
                    "poi_type": poi["poi_type"],
                    "search_region": poi["search_region"],
                })
                matched_count += 1

            # Rate limiting (Naver API: 25,000 calls/day)
            await asyncio.sleep(random.uniform(0.3, 0.8))

            if (i + 1) % 20 == 0:
                logger.info(f"  Processed {i + 1}/{len(google_pois)} — matched: {matched_count}")

    if dataset:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
            writer.writeheader()
            writer.writerows(dataset)

        logger.info(
            f"[ML Dataset Complete] 총 {len(dataset)}개 매칭 성공 "
            f"(전체 {len(google_pois)}개 중 {matched_count}개): {output_path}"
        )
    else:
        logger.warning("No Naver matches found! Make sure NAVER_CLIENT_ID/SECRET are set in .env")


if __name__ == "__main__":
    asyncio.run(build_naver_paired_dataset())
