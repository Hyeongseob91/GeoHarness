"""
GeoHarness v2.0: Naver Local Search API Collector

목적:
네이버 검색 API(Open API)를 사용하여 Google에서 추출한 POI 이름으로
네이버 지도에서 동일 장소를 검색, 네이버 좌표(KATECH/TM128)를 수집합니다.

API 신청:
    https://developers.naver.com/apps/#/register?api=search
    - 검색(Search) > 지역(Local) 선택
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

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NaverCollector")

load_dotenv()


async def search_naver_local(session: aiohttp.ClientSession, query: str) -> Dict | None:
    """
    네이버 지역 검색 API (공식 Open API)
    https://developers.naver.com/docs/serviceapi/search/local/local.md
    
    Returns: { n_name, n_mapx (KATECH x), n_mapy (KATECH y), n_address, n_road_address }
    """
    if not settings.NAVER_CLIENT_ID or settings.NAVER_CLIENT_ID.startswith("your-"):
        logger.warning("NAVER_CLIENT_ID is missing. Skipping Naver search.")
        return None
    if not settings.NAVER_CLIENT_SECRET or settings.NAVER_CLIENT_SECRET.startswith("your-"):
        logger.warning("NAVER_CLIENT_SECRET is missing. Skipping Naver search.")
        return None

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": 1,
        "sort": "random",
    }

    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                logger.warning(f"[Naver] API request failed for '{query}' with status: {response.status}")
                return None

            data = await response.json()
            items = data.get("items", [])
            if not items:
                return None

            first = items[0]
            return {
                "n_name": first.get("title", "").replace("<b>", "").replace("</b>", ""),
                "n_mapx": int(first.get("mapx", 0)),  # KATECH x coordinate
                "n_mapy": int(first.get("mapy", 0)),  # KATECH y coordinate
                "n_address": first.get("address", ""),
                "n_road_address": first.get("roadAddress", ""),
            }
    except Exception as e:
        logger.error(f"[Naver] Error searching '{query}': {e}")
        return None


async def build_naver_paired_dataset(
    google_csv_path: str = "data/google_poi_base.csv",
    output_path: str = "data/ml_dataset.csv"
):
    """
    Google POI 기준 데이터를 읽어서 네이버 지역 검색 API로 매칭하여
    최종 ML 학습 데이터셋을 생성합니다.
    
    Output columns:
        poi_name, g_lat, g_lng, n_mapx, n_mapy, n_name, n_address, poi_type, search_region
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

            if naver_result and naver_result["n_mapx"] > 0 and naver_result["n_mapy"] > 0:
                dataset.append({
                    "poi_name": poi["poi_name"],
                    "g_lat": float(poi["g_lat"]),
                    "g_lng": float(poi["g_lng"]),
                    "n_mapx": naver_result["n_mapx"],
                    "n_mapy": naver_result["n_mapy"],
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
