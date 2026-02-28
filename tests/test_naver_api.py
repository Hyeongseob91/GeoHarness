import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": "하이라인 성수동",
        "display": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            print(data)

if __name__ == "__main__":
    asyncio.run(main())
