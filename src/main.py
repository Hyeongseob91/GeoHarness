import os
import uvicorn
from api.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting GeoHarness Spatial-Sync API (MVP v4.0) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
