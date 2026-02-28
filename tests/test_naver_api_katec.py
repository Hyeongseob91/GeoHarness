import asyncio
import aiohttp
import os
from pyproj import Transformer
from dotenv import load_dotenv

load_dotenv()

# KATEC -> WGS84
# Naver Search API returns KATEC coords for mapx, mapy
# KATEC is EPSG:5179 but with different parameters, or maybe it's TM128.
# Actually Naver Local Search mapx, mapy are in KATEC (KTM).
# Let's test TM128 to WGS84
TRANSFORM_TM128_TO_WGS84 = Transformer.from_crs(
    "+proj=tmerc +lat_0=38 +lon_0=128 +k=0.9999 +x_0=400000 +y_0=600000 +ellps=bessel +units=m +no_defs +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43", 
    "EPSG:4326", 
    always_xy=True
)

async def main():
    mapx = 314909
    mapy = 549306
    # Wait, the search result had mapx='1270498827', mapy='375390219'
    # These look like lon/lat multiplied by 10^7!
    # Let's check: 127.0498827, 37.5390219
    # Yes, Naver local search format changed recently to return WGS84 x 10^7!
    
    print("Coordinates are just WGS84 multiplied by 10^7")

if __name__ == "__main__":
    asyncio.run(main())
