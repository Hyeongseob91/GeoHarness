import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    mapx = 1270498827
    mapy = 375390219
    from src.engine.transform import run_transformation_pipeline
    
    # KATEC -> WGS84 변환 테스트
    pass

if __name__ == "__main__":
    asyncio.run(main())
