import uvicorn
from api.server import app

if __name__ == "__main__":
    print("Starting GeoHarness Spatial-Sync API (MVP v4.0) on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
