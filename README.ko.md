<p align="center">
  <h1 align="center">GeoHarness</h1>
  <p align="center">
    구글 지도(WGS84)와 네이버 지도(GRS80/TM) 간의<br/>
    공간 좌표 편차를 측정하고 보정하는 기하학 기반 좌표 정합 시스템
  </p>
  <p align="center">
    한국어&nbsp;&nbsp;|&nbsp;&nbsp;<a href="README.md">English</a>
  </p>
</p>

---

## 개요

동일한 WGS84 좌표를 구글 지도와 네이버 지도에 렌더링하면 **1~5미터**의 시각적 오프셋이 발생합니다. GeoHarness는 이 오프셋을 정량화하고, AI 자기보정 루프로 교정한 뒤, 동기화된 분할 뷰 대시보드에서 보정 전후를 시각화합니다.

**파이프라인**: 좌표 입력 &rarr; pyproj 변환 (EPSG:4326 &harr; EPSG:5179) &rarr; Gemini AI 자기보정 &rarr; RMSE / Harness Score 오버레이가 포함된 분할 뷰 시각화

> **Gemini 3 Global Hackathon** 출품작 (2인 팀, 8시간 개발)

### 오차 발생 원인

**1. 데이텀(Datum) 차이**

구글 지도는 WGS84 타원체(EPSG:4326)를 사용하고, 네이버 지도는 GRS80 기반의 Korea 2000(EPSG:5179) 좌표계를 사용합니다. 두 타원체는 장반경과 편평율이 거의 동일하지만 완전히 같지는 않으며, 이 미세한 차이가 좌표 변환 시 서브미터 수준의 오프셋을 유발합니다. 특히 한국처럼 중위도 지역에서는 횡메르카토르(TM) 투영의 중앙 자오선(127.5&deg;E) 기준으로 동서 방향 왜곡이 누적됩니다.

**2. 투영(Projection) 방식의 차이**

구글 지도는 전 지구적 타일링에 최적화된 Web Mercator(EPSG:3857)로 렌더링하여 한국 영역에서 거리/면적 왜곡이 존재합니다. 네이버 지도는 한반도에 최적화된 Korea TM Central Belt(EPSG:5179)로 렌더링하여 위치 정밀도가 높습니다. 동일 WGS84 좌표를 각각의 투영으로 변환하면 픽셀 단위에서 수 미터의 위치 편차가 발생합니다.

**3. 타일 렌더링 및 지도 데이터 소스 차이**

양 플랫폼의 도로망, 건물 폴리곤, POI 위치 데이터가 서로 다른 측량 기준과 업데이트 주기로 수집되어, 같은 좌표에서도 시각적으로 다른 위치에 렌더링됩니다. 이 오프셋은 서울 도심에서 평균 약 3.1m이며, 고도 변화가 큰 지역(남산 등)에서는 4m 이상까지 확대됩니다.

## 지도 국외 반출과 GeoHarness

### 배경

2026년 2월 27일, 한국 정부는 구글의 1:5,000 축척 고정밀 지도 국외 반출을 조건부로 허가했습니다. 2007년 이후 약 18년간 지속되어 온 논쟁이 종결된 것으로, 보안시설 가림 처리, 좌표 표시 제한, 국내 서버 가공 등의 조건이 포함되어 있습니다.

### GeoHarness와의 연관성

이 반출 허가로 구글 지도의 한국 내 서비스 품질(길찾기, 내비게이션 등)이 대폭 개선될 전망입니다. 그러나 고정밀 지도가 도입되더라도, WGS84 &harr; Korea TM 간의 좌표계 변환 오차와 네이버/카카오 등 국내 지도 서비스와의 데이터 정합 문제는 여전히 남습니다.

GeoHarness는 두 지도 좌표계 간의 오차를 정량화하고 AI로 보정하는 알고리즘을 제공합니다. 이 과도기에서 크로스 플랫폼 위치 정확도 향상을 위한 기반 도구로서 기능하며, 관광, 물류, 자율주행 등 크로스 플랫폼 위치 정밀도가 핵심인 산업에서 지도 소스 간 오프셋을 실시간으로 감지하고 보정하는 것은 실질적인 인프라 과제입니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     GeoHarness 파이프라인                        │
├──────────┬──────────────┬────────────────┬──────────────────────┤
│  Layer 1 │   Layer 2    │    Layer 3     │       Layer 4        │
│  입력    │  좌표 변환    │    Gemini      │    시각화             │
│  핸들러   │  엔진        │    Harness     │                      │
├──────────┼──────────────┼────────────────┼──────────────────────┤
│ WGS84    │ pyproj 순방향/│ 자기보정 루프   │ 구글 지도 (좌측)      │
│ 유효성   │ 역방향 변환   │ (1-2회 반복)   │ 네이버 지도 (우측)     │
│ 검증     │ RMSE 계산    │ JSON 오프셋    │ 점수 오버레이          │
│ (한국)   │ Haversine    │ 15초 타임아웃   │ 진단 로그             │
└──────────┴──────────────┴────────────────┴──────────────────────┘
                              │
                     ┌────────┴────────┐
                     │  ML 추론 엔진    │
                     │  (선택사항)      │
                     │  decoder.pkl    │
                     │  XGBoost 모델   │
                     └─────────────────┘
```

**Layer 1 — 입력 핸들러**: 입력 좌표가 한국 영역(lat 33–43, lng 124–132) 내에 있는지 검증합니다. EPSG:5179 투영과 Ground Truth 데이터셋이 이 커버리지 범위에서만 유효하므로, 범위 밖의 좌표는 조기에 거부합니다.

**Layer 2 — 좌표 변환 엔진**: 단순한 순/역방향 투영(EPSG:4326 &harr; EPSG:5179)을 넘어, Haversine 거리를 사용하여 Ground Truth 대비 RMSE를 산출합니다. 이 RMSE 값이 다음 레이어의 AI 보정을 구동하는 정량적 입력이 됩니다.

**Layer 3 — Gemini Harness**: 좌표 오차가 비선형적이고 지역별로 패턴이 다르기 때문에(건물 밀도, 고도, 지역별 측량 기준점 등이 모두 영향) 룰 기반 보정이 아닌 AI 추론을 사용합니다. 고정 오프셋 테이블로는 이 변동성을 포착할 수 없으며, Gemini 모델이 공간 컨텍스트를 분석하여 포인트별 보정값을 제안합니다.

**Layer 4 — 시각화**: 분할 뷰 대시보드는 단순한 지도 표시가 아닙니다. 원본 좌표와 보정된 좌표를 정량적 지표(RMSE, Harness Score)와 함께 나란히 렌더링하여, 보정이 실제로 오프셋을 줄였는지 직접 검증할 수 있는 구조입니다.

### 이중 보정 전략

| 전략 | 방식 | 사용 시점 |
|---|---|---|
| **Gemini AI** | Chain-of-Thought 추론 + 구조화된 JSON 오프셋 출력 | `Run Sync` 버튼 — AI가 오차 원인을 분석하고 보정값 제안 |
| **ML 모델** | 앵커 포인트 피처 기반 XGBoost 회귀 모델 | `ML Offset` 버튼 — `decoder.pkl` 존재 시 밀리초 단위 추론 |
| **PyProj 폴백** | EPSG:4326 &harr; EPSG:5179 순수 투영 왕복 변환 | ML 모델 미로드 시 자동 폴백 |

## 핵심 지표

- **RMSE**: 보정된 좌표와 Ground Truth 간의 Haversine 거리 (미터)
- **Harness Score**: `max(0, 100 - RMSE_m * 10)` — 0m = 100점, 5m = 50점, 10m 이상 = 0점

## 기술 스택

| 레이어 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, Uvicorn |
| 좌표 변환 | pyproj 3.6+ (EPSG:4326 &harr; EPSG:5179) |
| AI 보정 | Google Generative AI SDK (Gemini 2.0 Flash) |
| ML 추론 | scikit-learn, XGBoost, NumPy, Pandas |
| 프론트엔드 | Vanilla HTML/CSS/JS, Google Maps JS API, Naver Maps SDK |
| CI/CD | GitHub Actions &rarr; GCP Cloud Run |
| 패키지 관리 | [uv](https://github.com/astral-sh/uv) |

## 프로젝트 구조

```
GeoHarness/
├── src/
│   ├── main.py                  # Uvicorn 진입점
│   ├── api/
│   │   ├── server.py            # FastAPI 앱, 변환 및 배치 엔드포인트
│   │   └── local_verifier.py    # ML 오프셋 예측 및 네이버 검증
│   ├── engine/
│   │   ├── transform.py         # pyproj WGS84 ↔ Korea TM 변환
│   │   ├── ai.py                # Gemini 자기보정 루프
│   │   ├── metrics.py           # Haversine, RMSE, Harness Score
│   │   ├── prompt.py            # Gemini CoT 시스템/사용자 프롬프트
│   │   └── inference.py         # ML 모델 로딩 및 예측
│   ├── ml/
│   │   ├── dataset_generator.py # Google/Naver POI 데이터 수집
│   │   ├── naver_collector.py   # 네이버 좌표 스크래퍼
│   │   ├── vworld_collector.py  # VWorld 앵커 포인트 수집기
│   │   ├── rapids_trainer.py    # GPU 가속 모델 학습
│   │   └── advanced_trainer.py  # XGBoost/sklearn 모델 학습
│   ├── shared/
│   │   ├── config.py            # Pydantic 설정 (.env 로더)
│   │   └── constants.py         # CRS 코드, 점수 파라미터, 제한값
│   └── static/
│       └── index.html           # 분할 뷰 대시보드 UI
├── data/
│   ├── test_coordinates.json    # 서울 12개 랜드마크 Ground Truth
│   ├── vworld_anchors.csv       # VWorld 기준 앵커 포인트
│   └── google_poi_base.csv      # Google POI 기본 데이터셋
├── tests/
│   ├── test_engine.py           # 변환 및 메트릭 단위 테스트
│   └── test_api.py              # API 엔드포인트 통합 테스트
├── Dockerfile                   # Cloud Run 컨테이너 이미지
├── pyproject.toml               # 프로젝트 메타데이터 및 의존성
└── .github/workflows/
    └── deploy-cloud-run.yml     # CI/CD 파이프라인
```

## 시작하기

### 사전 요구사항

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) 패키지 관리자

### 설치

```bash
# 레포지토리 클론
git clone https://github.com/Hyeongseob91/GeoHarness.git
cd GeoHarness

# 의존성 설치
uv sync
```

### 환경 변수

프로젝트 루트에 `.env` 파일을 생성하세요:

```env
GOOGLE_MAPS_KEY=your-google-maps-api-key
GEMINI_API_KEY=your-gemini-api-key
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
VWORLD_API_KEY=your-vworld-api-key        # 선택사항, 앵커 데이터 수집용
```

### 실행

```bash
# 개발 서버 시작
PYTHONPATH=src uv run uvicorn src.api.server:app --reload --port 8000
```

브라우저에서 `http://localhost:8000`으로 접속하세요.

### 테스트

```bash
uv run pytest tests/ -v
```

## API 레퍼런스

### `POST /api/v1/transform`

단일 좌표 변환 + RMSE 계산 + Gemini AI 자기보정 (선택적).

**요청**
```json
{
  "latitude": 37.49794,
  "longitude": 127.02764,
  "run_harness": true
}
```

**응답**
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

12개 테스트 랜드마크 일괄 변환 (Gemini 미호출, 성능 우선).

### `GET /api/v1/test-coordinates`

서울 12개 랜드마크 테스트 셋과 Ground Truth 좌표를 반환합니다.

### `POST /api/v1/predict-offset`

ML 기반 좌표 오프셋 예측.

```json
{ "lat": 37.5442, "lng": 127.0499 }
```

### `POST /api/v1/verify-location`

ML 보정 + 네이버 역지오코딩 검증.

### `GET /api/v1/model-status`

현재 ML 모델 로딩 상태 및 메타데이터를 반환합니다.

## 배포

### Docker

```bash
docker build -t geoharness .
docker run -p 8080:8080 --env-file .env geoharness
```

### GCP Cloud Run (CI/CD)

`main` 브랜치에 Push 시 GitHub Actions를 통해 GCP Cloud Run에 자동 배포됩니다.

**필요한 GitHub Secrets:**

| Secret | 설명 |
|---|---|
| `GCP_CREDENTIALS` | GCP 서비스 계정 JSON 키 (역할: Cloud Run 관리자, 서비스 계정 사용자) |
| `GOOGLE_MAPS_KEY` | Google Maps JavaScript API 키 |
| `GEMINI_API_KEY` | Gemini API 키 |
| `NAVER_CLIENT_ID` | 네이버 지도 SDK Client ID |

## Ground Truth 데이터셋

구글 지도와 네이버 지도 양쪽에서 수동 측정한 서울 12개 랜드마크:

| 랜드마크 | 카테고리 | 오프셋 (m) |
|---|---|---|
| 강남역 | 교통 | 3.7 |
| 서울시청 | 관공서 | 2.8 |
| 광화문 | 랜드마크 | 2.4 |
| 남산타워 | 랜드마크 | 4.3 |
| 코엑스 | 상업 | 3.7 |
| 여의도공원 | 공원 | 2.2 |
| 홍대입구역 | 교통 | 4.8 |
| 잠실종합운동장 | 스포츠 | 1.1 |
| 경복궁 | 문화재 | 2.4 |
| 이태원역 | 교통 | 4.2 |
| 동대문DDP | 상업 | 2.8 |
| 서울대입구역 | 교통 | 2.9 |

**평균 오프셋: ~3.1m**

## NFR 목표

| 지표 | 목표 |
|---|---|
| 좌표 변환 지연 시간 | < 10ms |
| 전체 파이프라인 (입력 &rarr; Gemini &rarr; 시각화) | < 30s |
| 12개 좌표 배치 (Gemini 미사용) | < 1s |
| 평균 RMSE | < 5m |
| 평균 Harness Score | > 90 |

## 라이선스

이 프로젝트는 Gemini 3 Global Hackathon 출품작입니다.
