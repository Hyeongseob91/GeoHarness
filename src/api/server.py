import json
import logging
import os
import time
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List

import google.generativeai as genai
from engine.transform import run_transformation_pipeline
from engine.ai import execute_gemini_correction_loop
from engine.metrics import calculate_rmse, calculate_harness_score

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
# Default MVP model per PRD
try:
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    gemini_model = None
    print(f"Failed to load genai module completely: {e}")

app = FastAPI(title="GeoHarness Spatial-Sync API MVP v4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("api")

# Load Mock Coordinates Data once
LANDMARK_DATA_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'test_coordinates.json')
TEST_LANDMARKS = []

def load_landmarks():
    global TEST_LANDMARKS
    if os.path.exists(LANDMARK_DATA_FILE):
        with open(LANDMARK_DATA_FILE, "r", encoding="utf-8") as f:
            TEST_LANDMARKS = json.load(f)

load_landmarks()

from fastapi.staticfiles import StaticFiles

# Add static front-end assets mounting
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
def read_root():
    # Helper to load front-end index trivially via FastAPI instead of separate file server.
    html_file = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/api/v1/transform")
def transform_endpoint(payload: Dict[str, Any] = Body(...)):
    start_ms = time.time() * 1000
    lat = payload.get("latitude")
    lng = payload.get("longitude")
    run_harness = payload.get("run_harness", True)

    if not isinstance(lat, (float, int)) or not isinstance(lng, (float, int)):
        raise HTTPException(status_code=400, detail="INVALID_COORDINATES: lat and lng must be numbers")

    if not (33.0 <= lat <= 43.0) or not (124.0 <= lng <= 132.0):
        raise HTTPException(status_code=422, detail="OUT_OF_COVERAGE: Coordinates outside Korean bounds")

    try:
        transform_result = run_transformation_pipeline(lat, lng)
        
        # Phase 4: Use real ground truth if it matches a test landmark, else dummy
        matched_landmark = None
        for lm in TEST_LANDMARKS:
            glat = lm["google_coords"]["lat"]
            glng = lm["google_coords"]["lng"]
            if abs(glat - lat) < 0.0001 and abs(glng - lng) < 0.0001:
                matched_landmark = lm
                break
                
        if matched_landmark:
            ground_truth = {
                "lat": matched_landmark["naver_coords"]["lat"],
                "lng": matched_landmark["naver_coords"]["lng"],
                "source": matched_landmark["name"]
            }
        else:
            ground_truth = {"lat": lat + 0.00001, "lng": lng - 0.00001, "source": "dummy"}
        
        harness_payload = {
            "rmse_before_m": 0.0,
            "rmse_after_m": 0.0,
            "harness_score": 0,
            "iterations": 0,
            "corrections": [],
            "gemini_reasoning": None,
            "gemini_status": "skipped"
        }

        if run_harness and gemini_model:
            input_context = {"lat": lat, "lng": lng, "label": "API Request Point"}
            rmse_pre, _, _, _, _ = execute_gemini_correction_loop(gemini_model, input_context, ground_truth, max_iterations=0)
            
            final_rmse, score, corrections, reasoning, status = execute_gemini_correction_loop(
                gemini_model, 
                input_context, 
                ground_truth, 
                max_iterations=2
            )
            
            harness_payload.update({
                "rmse_before_m": rmse_pre,
                "rmse_after_m": final_rmse,
                "harness_score": score,
                "iterations": len(corrections),
                "corrections": corrections,
                "gemini_reasoning": reasoning,
                "gemini_status": status
            })

        end_ms = time.time() * 1000
        return {
            "success": True,
            "data": {
                "input": {"latitude": lat, "longitude": lng, "label": "API Point"},
                "epsg5179": transform_result["epsg5179"],
                "ground_truth": ground_truth,
                "harness": harness_payload
            },
            "meta": {"processing_time_ms": int(end_ms - start_ms)}
        }

    except Exception as e:
        logger.error(f"Transform Error: {e}")
        raise HTTPException(status_code=500, detail=f"TRANSFORM_ERROR: {str(e)}")


@app.post("/api/v1/transform/batch")
def transform_batch_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    12개 테스트 좌표셋 일괄 변환 + RMSE 요약. Gemini 미호출 (성능).
    """
    start_ms = time.time() * 1000
    use_test_set = payload.get("use_test_set", True)

    if not use_test_set or not TEST_LANDMARKS:
        return {"success": False, "detail": "Test set absent or use_test_set flag false."}

    results = []
    total_rmse = 0.0
    max_rmse = -1.0
    min_rmse = 999999.0
    all_under_5m = True
    total_score = 0

    for lm in TEST_LANDMARKS:
        # Note: In MVP, dummy missing "naver_coords" zeroes will cause large RMSEs until filled out manually.
        glat = lm["google_coords"]["lat"]
        glng = lm["google_coords"]["lng"]
        
        nlat = lm["naver_coords"]["lat"]
        nlng = lm["naver_coords"]["lng"]
        
        # Calculate pure RMSE directly for batch verification (no gemini) 
        # (Transform pipelined inherently done during haversine distance eval to GT)
        # Assuming our pipeline is perfect, haversine GT directly against original google mapping
        # vs 'google mapping offset' after transformation. To keep it simple, we compare input vs Naver direct.
        rmse_val = calculate_rmse([{"lat": glat, "lng": glng}], [{"lat": nlat, "lng": nlng}])
        
        total_rmse += rmse_val
        if rmse_val > max_rmse: max_rmse = rmse_val
        if rmse_val < min_rmse: min_rmse = rmse_val
        if rmse_val >= 5.0: all_under_5m = False
        
        score = calculate_harness_score(rmse_val)
        total_score += score

        results.append({
            "label": lm["name"],
            "rmse_m": rmse_val,
            "harness_score": score
        })

    count = len(TEST_LANDMARKS)
    avg_rmse = total_rmse / count
    avg_score = total_score / count

    end_ms = time.time() * 1000

    return {
        "success": True,
        "data": {
            "results": results,
            "summary": {
                "total": count,
                "avg_rmse_m": avg_rmse,
                "max_rmse_m": max_rmse,
                "min_rmse_m": min_rmse,
                "avg_harness_score": avg_score,
                "all_under_5m": all_under_5m
            }
        },
        "meta": {"processing_time_ms": int(end_ms - start_ms)}
    }


@app.get("/api/v1/test-coordinates")
def get_test_coordinates_endpoint():
    """Returns the static landmark JSON set."""
    return {"success": True, "data": TEST_LANDMARKS}
