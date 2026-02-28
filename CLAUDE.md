# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GeoHarness (Spatial-Sync) is a geometry-based coordinate alignment system that measures and corrects the visual position discrepancy between Google Maps and Naver Maps for the same WGS84 coordinates. Built for the Gemini 3 Global Hackathon (2-person team, 8-hour budget).

The system is a **unidirectional pipeline**: coordinate input → pyproj transform (EPSG:4326 ↔ EPSG:5179) → Gemini AI self-correction → split-view visualization with RMSE/Harness Score overlay.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, uvicorn
- **Coordinate transform**: pyproj 3.6+ (EPSG:4326 ↔ EPSG:5179)
- **AI**: google-generativeai SDK (Gemini Pro, standard API + CoT prompt, JSON structured output)
- **Math**: NumPy, Haversine distance
- **Frontend**: Vanilla HTML/CSS/JS + Google Maps JS API (two instances for split-view)
- **Deploy**: Google Colab notebook with pyngrok tunnel

## Architecture (4-Layer Pipeline)

1. **Data Ingestion**: Input handler validates WGS84 coords are within Korea (lat 33–43, lng 124–132)
2. **Coordinate Engine**: pyproj forward/reverse transform + RMSE calculation against ground truth
3. **Gemini Harness**: Self-correction loop (max 2 iterations, 15s timeout each). On failure, falls back to RMSE-only display
4. **Visualization**: Split-view with two Google Maps instances (left=roadmap style, right=satellite/terrain style with corrected markers) + score overlay

## Key Formulas

- **RMSE**: Haversine distance (meters) between transformed coords and ground truth (manually measured Naver coords)
- **Harness Score**: `max(0, 100 - (RMSE_m × 10))` — 0m=100pts, 1m=90pts, 5m=50pts, 10m+=0pts
- **Correction**: Simple WGS84 lat/lng offset addition (`corrected = original + offset`)

## API Endpoints (no auth for MVP)

- `POST /api/v1/transform` — Single coordinate transform + RMSE + Gemini self-correction
- `POST /api/v1/transform/batch` — 12 test coordinates batch (no Gemini call)
- `GET /api/v1/test-coordinates` — Returns 12 landmark test set with ground truth

## Ground Truth

Ground truth = manually measured coordinates from both Google Maps and Naver Maps for 12 Seoul landmarks. Stored in `data/test_coordinates.json`. The RMSE measures how close the pyproj + Gemini corrected coordinates are to the Naver reference coordinates.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pyproj google-generativeai numpy pyngrok

# Run server
uvicorn main:app --reload --port 8000

# Environment variables needed (.env)
GOOGLE_MAPS_KEY=<key>
GEMINI_API_KEY=<key>
```

## NFR Targets

- Coordinate transform: < 10ms
- Full pipeline (input→transform→Gemini→viz): < 30s
- Batch 12 coords (no Gemini): < 1s
- Average RMSE: < 5m, Average Harness Score: > 90

## Important Design Decisions

- Naver Maps API is **not** used — replaced by a second Google Maps instance with different styling
- Gemini uses **standard API only** — no `thinking_level` or special parameters; CoT is in the system prompt
- Self-correction is a **fixed 1–2 iteration loop**, not open-ended
- Gemini failure is graceful: display RMSE without correction + "(Gemini 보정 없음)" label
- All PRD and planning docs are in Korean
