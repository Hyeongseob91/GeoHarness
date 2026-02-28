<p align="center">
  <h1 align="center">GeoHarness</h1>
  <p align="center">
    Geometry-based coordinate alignment system that measures and corrects<br/>
    the spatial discrepancy between Google Maps (WGS84) and Naver Maps (GRS80/TM)
  </p>
  <p align="center">
    <a href="README.ko.md">한국어</a>&nbsp;&nbsp;|&nbsp;&nbsp;English
  </p>
</p>

---

## Overview

When the same WGS84 coordinate is rendered on Google Maps and Naver Maps, a visual offset of **1–5 meters** appears. GeoHarness quantifies this offset, corrects it with an AI self-correction loop, and visualizes the before/after on a synchronized split-view dashboard.

**Pipeline**: Coordinate Input &rarr; pyproj Transform (EPSG:4326 &harr; EPSG:5179) &rarr; Gemini AI Self-Correction &rarr; Split-View Visualization with RMSE / Harness Score Overlay

> Built for the **Gemini 3 Global Hackathon** (2-person team, 8-hour budget).

### Why Does the Offset Occur?

**1. Datum Difference**

Google Maps uses the WGS84 ellipsoid (EPSG:4326), while Naver Maps uses Korea 2000 (EPSG:5179) based on the GRS80 ellipsoid. Although the two ellipsoids share nearly identical parameters (semi-major axis, flattening), they are not exactly the same. This subtle difference introduces sub-meter level offsets during coordinate transformation. In mid-latitude regions like Korea, east-west distortion accumulates relative to the Transverse Mercator central meridian at 127.5&deg;E.

**2. Projection Difference**

Google Maps renders tiles in Web Mercator (EPSG:3857), a global-scale projection optimized for tiling that introduces distance and area distortion at the regional level. Naver Maps renders in Korea TM Central Belt (EPSG:5179), a local projection optimized for the Korean Peninsula with higher positional accuracy. Converting the same WGS84 coordinate into each projection produces a pixel-level displacement of several meters.

**3. Tile Rendering and Data Source Difference**

Each platform collects road networks, building polygons, and POI location data using different survey baselines and update cycles. As a result, even at the same coordinate, the visual rendering position differs. This offset averages approximately 3.1m across central Seoul, and exceeds 4m in areas with significant elevation change such as Namsan.

## Map Data Export Approval and GeoHarness

### Background

On February 27, 2026, the Korean government conditionally approved Google's export of 1:5,000 scale high-precision map data — ending an 18-year debate that began in 2007. The approval includes conditions such as obscuring security facilities, restricting coordinate display, and requiring domestic server processing.

### Relevance to GeoHarness

This approval is expected to substantially improve Google Maps service quality in Korea (routing, navigation, etc.). However, even with high-precision maps, the coordinate transformation error between WGS84 and Korea TM remains, and data alignment issues with domestic map services (Naver, Kakao) persist.

GeoHarness provides an algorithm that quantifies the offset between two map coordinate systems and corrects it with AI. During this transitional period, it serves as a foundation tool for improving cross-platform location accuracy — particularly relevant in industries where cross-platform positional precision is critical, such as tourism, logistics, and autonomous driving. Detecting and correcting inter-source offsets in real time is a practical infrastructure problem in these domains.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GeoHarness Pipeline                        │
├──────────┬──────────────┬────────────────┬──────────────────────┤
│  Layer 1 │   Layer 2    │    Layer 3     │       Layer 4        │
│  Input   │  Coordinate  │    Gemini      │   Visualization      │
│  Handler │  Engine      │    Harness     │                      │
├──────────┼──────────────┼────────────────┼──────────────────────┤
│ Validate │ pyproj fwd/  │ Self-correct   │ Google Maps (left)   │
│ WGS84    │ rev transform│ loop (1-2 iter)│ Naver Maps  (right)  │
│ bounds   │ RMSE calc    │ JSON offsets   │ Score overlay         │
│ (Korea)  │ Haversine    │ 15s timeout    │ Diagnostic logs       │
└──────────┴──────────────┴────────────────┴──────────────────────┘
                              │
                     ┌────────┴────────┐
                     │  ML Inference   │
                     │  (Optional)     │
                     │  decoder.pkl    │
                     │  XGBoost model  │
                     └─────────────────┘
```

**Layer 1 — Input Handler**: Validates that input coordinates fall within the Korean bounding box (lat 33–43, lng 124–132). Coordinates outside this range are rejected early, since the EPSG:5179 projection and ground truth dataset are only valid for this coverage area.

**Layer 2 — Coordinate Engine**: Beyond simple forward/reverse projection (EPSG:4326 &harr; EPSG:5179), this layer calculates the RMSE against ground truth using Haversine distance. The RMSE value serves as the quantitative input that drives the AI correction in the next layer.

**Layer 3 — Gemini Harness**: Uses AI reasoning rather than rule-based correction because the coordinate offset is non-linear and varies by region — building density, elevation, and local survey baselines all affect the error pattern. A fixed offset table cannot capture this variability; the Gemini model analyzes the spatial context and proposes per-point corrections.

**Layer 4 — Visualization**: The split-view dashboard is not just a map display — it renders both the original and corrected coordinates side-by-side with quantitative metrics (RMSE, Harness Score), enabling direct verification of whether the correction actually reduced the offset.

### Dual Correction Strategies

| Strategy | Method | When Used |
|---|---|---|
| **Gemini AI** | Chain-of-Thought reasoning with structured JSON offset output | `Run Sync` button — AI analyzes error sources and proposes corrections |
| **ML Model** | XGBoost regressor trained on anchor-point features | `ML Offset` button — sub-millisecond inference if `decoder.pkl` is present |
| **PyProj Fallback** | Pure EPSG:4326 &harr; EPSG:5179 projection round-trip | Automatic fallback when ML model is not loaded |

## Key Metrics

- **RMSE**: Haversine distance (meters) between corrected coordinates and ground truth
- **Harness Score**: `max(0, 100 - RMSE_m * 10)` — 0m = 100pts, 5m = 50pts, 10m+ = 0pts

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Coordinate Transform | pyproj 3.6+ (EPSG:4326 &harr; EPSG:5179) |
| AI Correction | Google Generative AI SDK (Gemini 2.0 Flash) |
| ML Inference | scikit-learn, XGBoost, NumPy, Pandas |
| Frontend | Vanilla HTML/CSS/JS, Google Maps JS API, Naver Maps SDK |
| CI/CD | GitHub Actions &rarr; GCP Cloud Run |
| Package Manager | [uv](https://github.com/astral-sh/uv) |

## Project Structure

```
GeoHarness/
├── src/
│   ├── main.py                  # Uvicorn entry point
│   ├── api/
│   │   ├── server.py            # FastAPI app, transform & batch endpoints
│   │   └── local_verifier.py    # ML offset prediction & Naver verification
│   ├── engine/
│   │   ├── transform.py         # pyproj WGS84 ↔ Korea TM transforms
│   │   ├── ai.py                # Gemini self-correction loop
│   │   ├── metrics.py           # Haversine, RMSE, Harness Score
│   │   ├── prompt.py            # Gemini CoT system/user prompts
│   │   └── inference.py         # ML model loading & prediction
│   ├── ml/
│   │   ├── dataset_generator.py # Google/Naver POI data collection
│   │   ├── naver_collector.py   # Naver coordinate scraper
│   │   ├── vworld_collector.py  # VWorld anchor point collector
│   │   ├── rapids_trainer.py    # GPU-accelerated model training
│   │   └── advanced_trainer.py  # XGBoost/sklearn model training
│   ├── shared/
│   │   ├── config.py            # Pydantic settings (.env loader)
│   │   └── constants.py         # CRS codes, score params, limits
│   └── static/
│       └── index.html           # Split-view dashboard UI
├── data/
│   ├── test_coordinates.json    # 12 Seoul landmark ground truth
│   ├── vworld_anchors.csv       # VWorld reference anchor points
│   └── google_poi_base.csv      # Google POI base dataset
├── tests/
│   ├── test_engine.py           # Transform & metrics unit tests
│   └── test_api.py              # API endpoint integration tests
├── Dockerfile                   # Cloud Run container image
├── pyproject.toml               # Project metadata & dependencies
└── .github/workflows/
    └── deploy-cloud-run.yml     # CI/CD pipeline
```

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/Hyeongseob91/GeoHarness.git
cd GeoHarness

# Install dependencies
uv sync
```

### Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_MAPS_KEY=your-google-maps-api-key
GEMINI_API_KEY=your-gemini-api-key
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
VWORLD_API_KEY=your-vworld-api-key        # Optional, for anchor data collection
```

### Run

```bash
# Start the development server
PYTHONPATH=src uv run uvicorn src.api.server:app --reload --port 8000
```

Open `http://localhost:8000` in your browser.

### Test

```bash
uv run pytest tests/ -v
```

## API Reference

### `POST /api/v1/transform`

Single coordinate transform with RMSE calculation and optional Gemini AI self-correction.

**Request**
```json
{
  "latitude": 37.49794,
  "longitude": 127.02764,
  "run_harness": true
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "input": { "latitude": 37.49794, "longitude": 127.02764 },
    "epsg5179": { "x": 1000000.0, "y": 2000000.0 },
    "ground_truth": { "lat": 37.49795, "lng": 127.0276, "source": "강남역" },
    "harness": {
      "rmse_before_m": 3.7,
      "rmse_after_m": 0.8,
      "harness_score": 92,
      "iterations": 2,
      "gemini_status": "success"
    }
  },
  "meta": { "processing_time_ms": 4500 }
}
```

### `POST /api/v1/transform/batch`

Batch transform for all 12 test landmarks (no Gemini call, for performance).

### `GET /api/v1/test-coordinates`

Returns the 12 Seoul landmark test set with ground truth coordinates.

### `POST /api/v1/predict-offset`

ML-based coordinate offset prediction.

```json
{ "lat": 37.5442, "lng": 127.0499 }
```

### `POST /api/v1/verify-location`

ML correction + Naver reverse geocoding verification.

### `GET /api/v1/model-status`

Returns the current ML model loading status and metadata.

## Deployment

### Docker

```bash
docker build -t geoharness .
docker run -p 8080:8080 --env-file .env geoharness
```

### GCP Cloud Run (CI/CD)

The project includes a GitHub Actions workflow that automatically deploys to GCP Cloud Run on every push to `main`.

**Required GitHub Secrets:**

| Secret | Description |
|---|---|
| `GCP_CREDENTIALS` | GCP Service Account JSON key (roles: Cloud Run Admin, Service Account User) |
| `GOOGLE_MAPS_KEY` | Google Maps JavaScript API key |
| `GEMINI_API_KEY` | Gemini API key |
| `NAVER_CLIENT_ID` | Naver Maps SDK Client ID |

## Ground Truth Dataset

12 manually measured Seoul landmarks with coordinates from both Google Maps and Naver Maps:

| Landmark | Category | Offset (m) |
|---|---|---|
| Gangnam Station | Transit | 3.7 |
| Seoul City Hall | Government | 2.8 |
| Gwanghwamun | Landmark | 2.4 |
| Namsan Tower | Landmark | 4.3 |
| COEX | Commercial | 3.7 |
| Yeouido Park | Park | 2.2 |
| Hongdae Station | Transit | 4.8 |
| Jamsil Stadium | Sports | 1.1 |
| Gyeongbokgung | Heritage | 2.4 |
| Itaewon Station | Transit | 4.2 |
| Dongdaemun DDP | Commercial | 2.8 |
| SNU Station | Transit | 2.9 |

**Average offset: ~3.1m**

## NFR Targets

| Metric | Target |
|---|---|
| Coordinate transform latency | < 10ms |
| Full pipeline (input &rarr; Gemini &rarr; viz) | < 30s |
| Batch 12 coords (no Gemini) | < 1s |
| Average RMSE | < 5m |
| Average Harness Score | > 90 |

## License

This project was built for the Gemini 3 Global Hackathon.
