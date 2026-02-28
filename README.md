<p align="center">
  <h1 align="center">GeoHarness</h1>
  <p align="center">
    Cross-verify Google Maps POIs against Naver data<br/>
    to detect closures, relocations, and ghost listings in Korea
  </p>
  <p align="center">
    <a href="README.ko.md">한국어</a>&nbsp;&nbsp;|&nbsp;&nbsp;English
  </p>
</p>

---

## The Problem

Google Maps is the default map for tourists visiting Korea. But **31% of Google POIs in Korea** cannot be verified on Naver Maps — the dominant domestic platform with the most up-to-date local business data. These are likely closed, relocated, or never registered.

A tourist finds a café on Google Maps, walks 15 minutes, and discovers an empty storefront. This happens thousands of times daily.

## What GeoHarness Does

Search any place on Google Maps → GeoHarness cross-references it against Naver's local search database and returns a survival verdict:

| Verdict | Meaning | Criteria |
|---|---|---|
| **Verified** | Business confirmed active | Found on Naver, within 50m, name match |
| **Warning** | Possible relocation | Found on Naver but location/name mismatch |
| **Not Found** | Likely closed | Not found on Naver or distance > 500m |

Each result includes the Naver-matched business name, category, phone number, and a direct link to verify on Naver Places.

## How It Works

```
User searches "블루보틀 성수"
        │
        ├──→ Google Places Text Search API
        │         → name, coordinates, address, rating
        │
        ├──→ Naver Search Local API (parallel)
        │         → matched name, coordinates, category, phone, link
        │
        ├──→ Cross-Verification Engine
        │         → Haversine distance (Google vs Naver coords)
        │         → Name similarity (SequenceMatcher, normalized)
        │         → Status classification: verified / warning / not_found
        │
        └──→ Response
                  → Verdict card + dual map view (Google left, Naver right)
```

### Verification Logic

```python
def classify_poi_status(google_name, google_coords, naver_item, naver_coords):
    distance = haversine(google_coords, naver_coords)
    similarity = name_similarity(google_name, naver_name)

    if distance <= 50m and similarity >= 0.4:  → "verified"
    if distance <= 500m:                        → "warning"
    else:                                       → "not_found"
```

### ML Coordinate Correction (Secondary)

The system also runs an optional ML correction pipeline (XGBoost) that adjusts Google's WGS84 coordinates. However, with a median Google-Naver offset of only 6.6m, this provides marginal value compared to the survival verification — which flags 31% of POIs as potentially invalid.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GeoHarness Pipeline                         │
├──────────┬──────────────┬──────────────────┬────────────────────┤
│  Input   │  Dual API    │  Verification    │  Visualization     │
│  Handler │  Fetch       │  Engine          │                    │
├──────────┼──────────────┼──────────────────┼────────────────────┤
│ Validate │ Google Places│ Name similarity  │ Verdict card       │
│ query    │ (parallel)   │ Distance calc    │ (status + details) │
│          │ Naver Search │ Status classify  │ Google Map (left)  │
│          │ Local API    │ Confidence score │ Naver Map  (right) │
└──────────┴──────────────┴──────────────────┴────────────────────┘
                              │
                     ┌────────┴────────┐
                     │  ML Inference   │
                     │  (Secondary)    │
                     │  decoder.pkl    │
                     └─────────────────┘
```

## Key Data Points

- **3,065** Google POIs analyzed in Seoul
- **957 (31.2%)** could not be verified on Naver
- **6.6m** median coordinate offset (Google vs Naver) — too small to matter
- **31%** failure rate — large enough to matter

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | Next.js 15, React, Tailwind CSS |
| Google API | Places Text Search, Places Autocomplete |
| Naver API | Search Local API, Maps SDK, NCP Geocoding |
| ML (secondary) | scikit-learn, XGBoost |
| CI/CD | GitHub Actions → GCP Cloud Run |
| Package Manager | [uv](https://github.com/astral-sh/uv) (backend), npm (frontend) |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
git clone https://github.com/Hyeongseob91/GeoHarness.git
cd GeoHarness

# Backend
uv sync

# Frontend
cd frontend && npm install
```

### Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_MAPS_KEY=your-google-maps-api-key
NAVER_SEARCH_CLIENT_ID=your-naver-search-client-id
NAVER_SEARCH_CLIENT_SECRET=your-naver-search-client-secret
NAVER_CLIENT_ID=your-ncp-client-id
NAVER_CLIENT_SECRET=your-ncp-client-secret
```

### Run

```bash
# Backend (port 8000)
PYTHONPATH=src uv run uvicorn src.api.server:app --reload --port 8000

# Frontend (port 3000)
cd frontend && npm run dev
```

Open `http://localhost:3000` in your browser.

## API Reference

### `POST /api/v1/search`

Search and verify a place.

**Request**
```json
{ "query": "블루보틀 성수", "region": "성수동" }
```

**Response**
```json
{
  "places": [{
    "name": "블루보틀 성수",
    "address": "서울시 성동구...",
    "status": "verified",
    "status_reason": "네이버 검색 확인됨",
    "status_confidence": 0.95,
    "naver_name": "블루보틀 성수카페",
    "naver_category": "카페",
    "naver_phone": "02-1234-5678",
    "naver_link": "https://...",
    "name_similarity": 0.92,
    "original": { "lat": 37.5442, "lng": 127.0499 },
    "naver_location": { "lat": 37.5443, "lng": 127.0501 }
  }],
  "query": "블루보틀 성수 성수동",
  "total": 1
}
```

### `GET /api/v1/search/autocomplete?q=블루보틀`

Google Places Autocomplete suggestions (Korean establishments only).

## Map Data Export Approval and GeoHarness

On February 27, 2026, the Korean government conditionally approved Google's export of 1:5,000 scale map data — ending an 18-year debate. While this will improve Google Maps routing in Korea, it does not solve the POI freshness problem: businesses open and close constantly, and Google's update cycle for Korean POIs lags significantly behind Naver's.

GeoHarness addresses this data freshness gap by cross-referencing Google POIs against Naver's real-time business database, providing tourists with an instant "is this place still open?" check.

## License

MIT
