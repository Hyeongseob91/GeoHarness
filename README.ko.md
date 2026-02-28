<p align="center">
  <h1 align="center">GeoHarness</h1>
  <p align="center">
    구글 지도 POI를 네이버 데이터와 교차검증하여<br/>
    폐업·이전·유령 등록을 탐지하는 시스템
  </p>
  <p align="center">
    한국어&nbsp;&nbsp;|&nbsp;&nbsp;<a href="README.md">English</a>
  </p>
</p>

---

## 문제

구글 지도는 한국을 방문하는 관광객의 기본 지도입니다. 그러나 **한국 내 구글 POI의 31%**가 네이버 지도에서 확인되지 않습니다. 네이버는 가장 최신의 국내 상업 데이터를 보유한 플랫폼으로, 확인 불가 POI는 폐업·이전·미등록으로 추정됩니다.

관광객이 구글 지도에서 카페를 찾아 15분을 걸어갔는데, 빈 가게를 발견하는 일이 매일 수천 건 발생합니다.

## GeoHarness가 하는 일

구글 지도에서 장소를 검색하면 → 네이버 로컬 검색 DB와 교차검증하여 생존 판정을 반환합니다:

| 판정 | 의미 | 기준 |
|---|---|---|
| **영업 중 확인** | 영업 확인됨 | 네이버에 존재 + 50m 이내 + 이름 일치 |
| **이전 가능성** | 이전되었을 수 있음 | 네이버에 존재하나 위치/이름 불일치 |
| **폐업 추정** | 폐업 가능성 높음 | 네이버 미등록 또는 거리 500m 초과 |

각 결과에는 네이버 매칭 업체명, 카테고리, 전화번호, 네이버 플레이스 직접 확인 링크가 포함됩니다.

## 작동 방식

```
사용자가 "블루보틀 성수" 검색
        │
        ├──→ Google Places Text Search API
        │         → 가게명, 좌표, 주소, 평점
        │
        ├──→ Naver Search Local API (병렬 호출)
        │         → 매칭 업체명, 좌표, 카테고리, 전화번호, 링크
        │
        ├──→ 교차검증 엔진
        │         → Haversine 거리 (구글 vs 네이버 좌표)
        │         → 이름 유사도 (SequenceMatcher, 정규화)
        │         → 상태 분류: verified / warning / not_found
        │
        └──→ 응답
                  → 판정 카드 + 듀얼 지도 뷰 (구글 좌, 네이버 우)
```

### 검증 로직

```python
def classify_poi_status(google_name, google_coords, naver_item, naver_coords):
    distance = haversine(google_coords, naver_coords)
    similarity = name_similarity(google_name, naver_name)

    if distance <= 50m and similarity >= 0.4:  → "verified"  (영업 중 확인)
    if distance <= 500m:                        → "warning"   (이전 가능성)
    else:                                       → "not_found" (폐업 추정)
```

### ML 좌표 보정 (보조 기능)

XGBoost 기반 ML 보정 파이프라인도 함께 동작합니다. 그러나 구글-네이버 좌표 오차 중앙값이 6.6m에 불과하여 보정의 실질적 가치는 미미합니다. 반면 POI 생존 검증은 31%의 POI를 위험으로 플래그하므로 즉각적인 가치가 있습니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     GeoHarness 파이프라인                         │
├──────────┬──────────────┬──────────────────┬────────────────────┤
│  입력     │  이중 API    │  검증 엔진       │  시각화             │
│  핸들러   │  호출        │                  │                    │
├──────────┼──────────────┼──────────────────┼────────────────────┤
│ 쿼리     │ Google Places│ 이름 유사도 계산  │ 판정 카드           │
│ 검증     │ (병렬 호출)   │ 거리 계산        │ (상태 + 상세정보)   │
│          │ Naver Search │ 상태 분류        │ 구글 지도 (좌측)    │
│          │ Local API    │ 신뢰도 산출      │ 네이버 지도 (우측)   │
└──────────┴──────────────┴──────────────────┴────────────────────┘
                              │
                     ┌────────┴────────┐
                     │  ML 추론 엔진    │
                     │  (보조 기능)     │
                     │  decoder.pkl    │
                     └─────────────────┘
```

## 핵심 데이터

- **3,065건** 서울 내 Google POI 분석
- **957건 (31.2%)** 네이버에서 확인 불가
- **6.6m** 좌표 오차 중앙값 (구글 vs 네이버) — 너무 작아서 보정 불필요
- **31%** 검증 실패율 — 충분히 크므로 즉각적 가치

## 기술 스택

| 레이어 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, Uvicorn |
| 프론트엔드 | Next.js 15, React, Tailwind CSS |
| Google API | Places Text Search, Places Autocomplete |
| Naver API | Search Local API, Maps SDK, NCP Geocoding |
| ML (보조) | scikit-learn, XGBoost |
| CI/CD | GitHub Actions → GCP Cloud Run |
| 패키지 관리 | [uv](https://github.com/astral-sh/uv) (백엔드), npm (프론트엔드) |

## 시작하기

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) 패키지 관리자

### 설치

```bash
git clone https://github.com/Hyeongseob91/GeoHarness.git
cd GeoHarness

# 백엔드
uv sync

# 프론트엔드
cd frontend && npm install
```

### 환경 변수

프로젝트 루트에 `.env` 파일을 생성하세요:

```env
GOOGLE_MAPS_KEY=your-google-maps-api-key
NAVER_SEARCH_CLIENT_ID=your-naver-search-client-id
NAVER_SEARCH_CLIENT_SECRET=your-naver-search-client-secret
NAVER_CLIENT_ID=your-ncp-client-id
NAVER_CLIENT_SECRET=your-ncp-client-secret
```

### 실행

```bash
# 백엔드 (포트 8000)
PYTHONPATH=src uv run uvicorn src.api.server:app --reload --port 8000

# 프론트엔드 (포트 3000)
cd frontend && npm run dev
```

브라우저에서 `http://localhost:3000`으로 접속하세요.

## API 레퍼런스

### `POST /api/v1/search`

장소 검색 및 생존 검증.

**요청**
```json
{ "query": "블루보틀 성수", "region": "성수동" }
```

**응답**
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

Google Places Autocomplete 자동완성 (한국 내 상업시설 한정).

## 지도 국외 반출과 GeoHarness

2026년 2월 27일, 한국 정부가 구글의 1:5,000 축척 지도 반출을 조건부 허가했습니다 — 18년간의 논쟁이 종결. 이로 인해 구글 지도의 한국 내 길찾기가 개선되겠지만, POI 최신성 문제는 해결되지 않습니다. 상점은 끊임없이 개폐업하며, 구글의 한국 POI 업데이트 주기는 네이버보다 현저히 느립니다.

GeoHarness는 이 데이터 신선도 격차를 해소합니다. 구글 POI를 네이버의 실시간 사업체 DB와 교차검증하여, 관광객에게 "이 가게 아직 있나요?"에 대한 즉각적인 답변을 제공합니다.

## 라이선스

MIT
