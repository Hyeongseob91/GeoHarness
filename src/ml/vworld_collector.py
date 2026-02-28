"""
GeoHarness v2.0: VWorld Ground Truth Anchor Collector

목적:
VWorld(국가공간정보포털)의 Geocoder API를 사용하여 
성수동/연무장길 일대의 **고정 기준점(Geometric Anchor)**을 수집합니다.

기준점의 역할:
    - 도로 교차로, 지하철역 출구, 공공건물 등 물리적으로 움직이지 않는 좌표
    - 이 좌표를 "정답(Ground Truth)"으로 삼고
    - 구글이 같은 지점을 어디로 찍었는지 / 네이버가 어디로 찍었는지 비교
    - → 각 지도 소스별 오프셋 벡터(ΔLat, ΔLng) 산출

사용법:
    1. .env에 VWORLD_API_KEY를 설정합니다.
    2. python src/ml/vworld_collector.py 실행
    3. data/vworld_anchors.csv 생성됨
"""

import asyncio
import csv
import logging
from pathlib import Path
from typing import List, Dict

import aiohttp
from dotenv import load_dotenv
from pyproj import Transformer

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VWorldCollector")

load_dotenv()

# PyProj transformer: WGS84 (EPSG:4326) <-> Korea TM (EPSG:5179)
wgs84_to_tm = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)


# ─────────────────────────────────────────────────────
# 성수동/연무장길 일대 고정 기준점 (Geometric Anchors)
# 도로 교차로, 지하철역 출구, 공공시설 등
# ─────────────────────────────────────────────────────
SEONGSU_ANCHORS = [
    # 지하철역 출구 (절대 움직이지 않는 좌표)
    {"name": "성수역 1번출구", "address": "서울특별시 성동구 성수이로 지하 51"},
    {"name": "성수역 2번출구", "address": "서울특별시 성동구 성수이로 지하 51"},
    {"name": "성수역 3번출구", "address": "서울특별시 성동구 뚝섬로 지하 1"},
    {"name": "성수역 4번출구", "address": "서울특별시 성동구 뚝섬로 지하 1"},
    {"name": "뚝섬역 1번출구", "address": "서울특별시 성동구 서울숲2길 지하 32"},
    {"name": "뚝섬역 2번출구", "address": "서울특별시 성동구 서울숲2길 지하 32"},
    {"name": "서울숲역 1번출구", "address": "서울특별시 성동구 왕십리로 지하 83-6"},
    {"name": "서울숲역 3번출구", "address": "서울특별시 성동구 왕십리로 지하 83-6"},

    # 도로 교차로 (도로명 주소로 정확한 위치 특정)
    {"name": "연무장길 시작점 (성수이로 교차)", "address": "서울특별시 성동구 연무장길 1"},
    {"name": "연무장길 중간점", "address": "서울특별시 성동구 연무장길 15"},
    {"name": "연무장길 5길 교차점", "address": "서울특별시 성동구 연무장5길 1"},
    {"name": "연무장길 7길 교차점", "address": "서울특별시 성동구 연무장7길 1"},
    {"name": "연무장길 끝점 (뚝섬로 교차)", "address": "서울특별시 성동구 연무장길 45"},
    {"name": "성수이로 22길 시작점", "address": "서울특별시 성동구 성수이로22길 1"},
    {"name": "서울숲2길 시작점", "address": "서울특별시 성동구 서울숲2길 1"},
    {"name": "서울숲4길 시작점", "address": "서울특별시 성동구 서울숲4길 1"},
    {"name": "뚝섬로 1길 시작점", "address": "서울특별시 성동구 뚝섬로1길 1"},
    {"name": "뚝섬로 1나길 시작점", "address": "서울특별시 성동구 뚝섬로1나길 1"},
    {"name": "아차산로 시작점 (성수동)", "address": "서울특별시 성동구 아차산로 49"},
    {"name": "왕십리로 (성수역 부근)", "address": "서울특별시 성동구 왕십리로 83"},

    # 공공시설 / 랜드마크 (고정 건물)
    {"name": "서울숲 정문", "address": "서울특별시 성동구 뚝섬로 273"},
    {"name": "성수동 우체국", "address": "서울특별시 성동구 성수이로7길 14"},
    {"name": "성동구청", "address": "서울특별시 성동구 고산자로 270"},
    {"name": "성수1가1동 주민센터", "address": "서울특별시 성동구 독서당로 277"},
    {"name": "성수2가제3동 주민센터", "address": "서울특별시 성동구 뚝섬로1길 29"},
]


async def geocode_address_vworld(session: aiohttp.ClientSession, address: str) -> Dict | None:
    """VWorld Geocoder API로 도로명주소 → WGS84 좌표 변환"""
    if not settings.VWORLD_API_KEY or settings.VWORLD_API_KEY.startswith("your-"):
        logger.error("VWORLD_API_KEY is missing.")
        return None

    url = (
        f"https://api.vworld.kr/req/address?"
        f"service=address&request=getCoord&version=2.0"
        f"&crs=epsg:4326&refine=true&simple=false"
        f"&format=json&type=ROAD"
        f"&address={address}"
        f"&key={settings.VWORLD_API_KEY}"
    )

    try:
        async with session.get(url) as response:
            if response.status != 200:
                logger.warning(f"[VWorld] HTTP {response.status} for: {address}")
                return None

            data = await response.json(content_type=None)
            status = data.get("response", {}).get("status")

            if status != "OK":
                logger.warning(f"[VWorld] Status {status} for: {address}")
                return None

            point = data["response"]["result"]["point"]
            return {
                "vw_lng": float(point["x"]),
                "vw_lat": float(point["y"]),
            }
    except Exception as e:
        logger.error(f"[VWorld] Error geocoding '{address}': {e}")
        return None


async def collect_anchors(output_path: str = "data/vworld_anchors.csv"):
    """
    성수동 고정 기준점들의 VWorld 공식 좌표를 수집하고,
    PyProj로 EPSG:5179 좌표도 함께 산출합니다.
    """
    logger.info(f"Collecting {len(SEONGSU_ANCHORS)} ground truth anchors from VWorld...")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    dataset = []

    async with aiohttp.ClientSession() as session:
        for i, anchor in enumerate(SEONGSU_ANCHORS):
            result = await geocode_address_vworld(session, anchor["address"])

            if result:
                # PyProj 변환: WGS84 -> EPSG:5179
                tm_x, tm_y = wgs84_to_tm.transform(result["vw_lng"], result["vw_lat"])

                dataset.append({
                    "anchor_name": anchor["name"],
                    "address": anchor["address"],
                    "vw_lat": result["vw_lat"],
                    "vw_lng": result["vw_lng"],
                    "tm_x": round(tm_x, 4),
                    "tm_y": round(tm_y, 4),
                })
                logger.info(f"  ✅ {anchor['name']}: ({result['vw_lat']:.6f}, {result['vw_lng']:.6f})")
            else:
                logger.warning(f"  ❌ {anchor['name']}: geocoding failed")

            # VWorld rate limit: 1 req/sec
            await asyncio.sleep(1.0)

    if dataset:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
            writer.writeheader()
            writer.writerows(dataset)

        logger.info(
            f"\n[Ground Truth Anchors Complete] "
            f"총 {len(dataset)}/{len(SEONGSU_ANCHORS)}개 기준점 확보: {output_path}"
        )
    else:
        logger.warning("No anchors collected! Check VWORLD_API_KEY.")


if __name__ == "__main__":
    asyncio.run(collect_anchors())
