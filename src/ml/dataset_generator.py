"""
GeoHarness v2.0: ML Dataset Generator for Google vs Naver Coordination

목적: 
네이버 지도의 좌표계(보안 암호화 적용)와 구글 지도(반출 조건부 허용 WGS84)의 데이터를 
대량으로 스크래핑/추출하여 (Lat, Lng) 쌍의 Dataset을 구축합니다.
"""

import asyncio
import csv
import json
import logging
import random
import urllib.parse
from pathlib import Path
from typing import List, Dict

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DatasetGenerator")

load_dotenv()

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


async def fetch_poi_data_google(session: aiohttp.ClientSession, region_keyword: str) -> List[Dict]:
    """Fetch WGS84 coordinates using Google Places Text Search API"""
    if not settings.GOOGLE_MAPS_KEY or settings.GOOGLE_MAPS_KEY.startswith("your-"):
        logger.warning("GOOGLE_MAPS_KEY is missing or invalid. Skipping Google extraction.")
        return []

    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(region_keyword)}&region=kr&language=ko&key={settings.GOOGLE_MAPS_KEY}"
    
    try:
        async with session.get(url) as response:
            data = await response.json()
            if "error_message" in data:
                logger.error(f"[Google] API Error: {data['error_message']}")
            
            pois = []
            for place in data.get("results", []):
                pois.append({
                    "name": place.get("name", ""),
                    "g_lat": place.get("geometry", {}).get("location", {}).get("lat", 0),
                    "g_lng": place.get("geometry", {}).get("location", {}).get("lng", 0),
                    "address": place.get("formatted_address", ""),
                    "poi_type": place.get("types", ["unknown"])[0] if place.get("types") else "unknown"
                })
            logger.info(f"[Google] Found {len(pois)} POIs for '{region_keyword}'")
            return pois
    except Exception as e:
        logger.error(f"[Google] Error fetching POIs: {e}")
        return []


async def fetch_poi_data_naver(session: aiohttp.ClientSession, keyword: str) -> Dict | None:
    """Fallback scraping for Naver Map search using the public autocomplete/search endpoint"""
    # Using the public mobile local search API which is less restrictive
    url = f"https://m.map.naver.com/search2/searchMore.naver?query={urllib.parse.quote(keyword)}&sm=hty&style=v5&page=1"
    
    try:
        custom_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://m.map.naver.com/"
        }
        
        async with session.get(url, headers=custom_headers) as response:
            if response.status != 200:
                logger.warning(f"[Naver] Request failed for '{keyword}' with status: {response.status}")
                return None
            
            # Naver mobile searchMore returns a JSON wrapped in a weird structure or just JSON
            data = await response.json(content_type=None)
            items = data.get("result", {}).get("site", {}).get("list", [])
            if not items:
                return None
            
            first_hit = items[0]
            # m.map.naver.com usually returns x/y in 'x' and 'y' fields
            return {
                "n_name": first_hit.get("name"),
                "n_lng": float(first_hit.get("x", 0)),
                "n_lat": float(first_hit.get("y", 0))
            }
    except Exception as e:
        logger.error(f"[Naver] Error scraping POI '{keyword}': {e}")
        return None


async def build_google_base_dataset(regions: List[str], output_path: str = "data/google_poi_base.csv"):
    """
    Step 1. For each region, grab POIs from Google (WGS84).
    We extract this first as our ground-truth search list, since we don't have Naver API keys yet.
    """
    logger.info("Starting Google Base Dataset Extraction...")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    dataset = []
    
    async with aiohttp.ClientSession() as session:
        for region in regions:
            google_pois = await fetch_poi_data_google(session, region)
            
            for g_poi in google_pois:
                dataset.append({
                    "poi_name": g_poi["name"],
                    "g_lat": g_poi["g_lat"],
                    "g_lng": g_poi["g_lng"],
                    "poi_type": g_poi["poi_type"],
                    "search_region": region
                })
            
            # Simple rate limiting for Google API
            await asyncio.sleep(1.0)
                
    if not dataset:
        logger.warning("No Google data extracted successfully! Dataset is empty.")
        return

    # Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
        writer.writeheader()
        writer.writerows(dataset)
    
    logger.info(f"[Step 1 Complete] 총 {len(dataset)} 개의 구글 WGS84 기준 좌표 추출 완료: {output_path}")


if __name__ == "__main__":
    # Target Regions for Hackathon Density Gathering (Focus: Seongsu / Yeonmujang-gil)
    target_regions = [
        "성수동 카페", "성수동 식당", "성수동 팝업스토어", 
        "연무장길 카페", "연무장길 식당", "연무장길 맛집",
        "뚝섬역 카페", "서울숲역 맛집"
    ]
    # Step 1: Extract Google Data First
    asyncio.run(build_google_base_dataset(target_regions))
