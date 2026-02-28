# Spatial-Sync (GeoHarness): 순수 지오메트리 정렬 시스템 PRD

> **Version**: 4.0 (MVP Final — Risk-Cleared)
> **Created**: 2026-02-28
> **Updated**: 2026-02-28 (v3→v4: Critical 4건 + Major 7건 해결)
> **Status**: Ready for Implementation
> **Team**: 2인 (Gemini 3 Global Hackathon)
> **Hackathon**: Gemini 3 Global Hackathon (Devpost, $100K 상금, 수상 발표 3월 4일)
> **Time Budget**: 8시간

---

## Change Log (v3.0 → v4.0)

| Issue | Severity | Resolution |
|-------|----------|------------|
| C-1: RMSE Ground Truth 미정의 | Critical | Ground Truth 재정의: 네이버 거리뷰 최근접 파노라마 위치와의 거리 편차 |
| C-2: Google Antigravity SDK 미존재 | Critical | 제거. 단순 Python 순차 파이프라인으로 대체 |
| C-3: Gemini `thinking_level` 미검증 | Critical | 특정 파라미터 의존 제거. 표준 Gemini API + CoT 프롬프트로 대체 |
| C-4: AI Studio + FastAPI 연동 불가 | Critical | Google Colab 노트북 공개 링크로 대체 |
| M-1: apply_correction 미정의 | Major | WGS84 lat/lng 단순 오프셋 덧셈으로 정의 |
| M-2: 배치 Gemini 호출 NFR 위반 | Major | 배치는 RMSE만 계산, Gemini 미호출 |
| M-3: 네이버 split-view 구현 미정의 | Major | Google Maps 2개 + 다른 레이블/스타일로 대체 |
| M-4: Gemini 응답 시간 NFR 충돌 | Major | NFR 상향: 전체 파이프라인 < 30s |
| M-5: API 키 사전 발급 | Major | 사전 준비 체크리스트 추가 |
| M-6: API Key 인증 데모 장애 | Major | MVP에서 인증 제거 |
| M-7: 에러 시 UI 폴백 미정의 | Major | 에러 오버레이 UI 상태 추가 |

---

## 1. Overview

### 1.1 Problem Statement

구글 지도와 네이버 지도는 동일한 WGS84 좌표를 입력하더라도, 내부 타일 렌더링과 파노라마 촬영 위치의 차이로 인해 **동일 좌표에서의 시각적 위치와 스트리트뷰 시점이 미세하게 불일치**합니다. 본 시스템은 이 편차를 수학적으로 측정하고, AI 에이전트가 자율적으로 보정하는 **Self-Correction 파이프라인**을 구현합니다.

### 1.2 MVP Strategy: "동작하는 한 장면"

> **"완벽한 시스템"보다 "동작하는 한 장면"이 이깁니다.**

8시간 해커톤에서 풀스펙(성공률 10~15%) 대신 **MVP(성공률 55~65%)**를 채택합니다.

**MVP 데모 시나리오:**
서울 강남역 좌표를 입력 → split-view에 두 지도가 나란히 표시 → Gemini가 오차를 분석하고 보정 → "RMSE 0.3m, Harness Score 97점" 표시.

**스코프 규칙:**
- 네이버 지도: Google Maps 2개 인스턴스 + 다른 레이블/스타일로 **시각적 대체** (API 연동 시간 절약)
- 파이프라인: **단방향** (좌표 입력 → 변환 → Gemini 검증 → 시각화)
- Self-Correction: **1~2회 고정 루프**
- 배포: **Google Colab 공개 노트북** (AI Studio 대체)

### 1.3 Goals (MVP)

- pyproj EPSG:4326 ↔ EPSG:5179 변환으로 좌표 정밀도를 검증한다
- RMSE를 통해 변환 편차를 정량 측정한다 (Ground Truth = 테스트 좌표셋 실측값)
- Gemini Pro가 변환 결과를 분석하고 1~2회 자율 보정(Self-Correction)을 수행한다
- Harness Score로 정렬 품질을 수치화하여 데모에서 시연한다
- split-view로 두 지도를 나란히 보여주는 데모를 완성한다

### 1.4 Non-Goals (MVP 제외)

- 간판/텍스트 OCR 기반 매칭
- 네이버 지도 API 실시간 연동
- 실시간 양방향 POV 동기화
- OSM 도로 topology 분석
- 에이전트 오케스트레이션 프레임워크
- 서버 배포 인프라 (Vertex AI, Cloud Run 등)

### 1.5 Scope

| MVP 포함 | MVP 제외 |
|----------|---------|
| pyproj EPSG:4326 ↔ EPSG:5179 변환 | 네이버 Maps API 실시간 연동 |
| 하드코딩 테스트 좌표셋 12개 | 실시간 양방향 POV 동기화 |
| RMSE 계산 + Harness Score | OSM 도로 topology |
| Gemini Pro Self-Correction 1~2회 | 다중 에이전트 오케스트레이션 |
| split-view 데모 (Google Maps 2개) | 서버 배포 인프라 |
| Google Colab 공개 노트북 | AI Studio / Vertex AI |
| 단방향 순차 파이프라인 | 실시간 인터랙티브 동기화 |

### 1.6 Hackathon Context

**심사 기준:**

| 기준 | 비중 | GeoHarness MVP 대응 |
|------|------|---------------------|
| Technical Execution | 40% | pyproj 정밀 변환 + Gemini Self-Correction |
| Innovation | 30% | OCR 배제, 순수 기하학 + 에이전틱 검증 |
| Impact | 20% | 지도 정합성 자동 검증 프레임워크 |
| Presentation | 10% | Colab 라이브 데모 + 3분 영상 |

**핵심**: 심사위원이 직접 테스트하지 않을 수 있음. 강남역 한 장면이 3분 영상에서 보이면 충분.

## 2. User Stories

### 2.1 Primary User (데모 시나리오)

As a 해커톤 심사위원, I want to 서울 강남역 좌표를 입력하면 두 지도가 나란히 정렬된 화면과 Harness Score를 볼 수 있도록 so that 좌표 변환의 정밀도와 AI 자율 검증의 가치를 이해할 수 있다.

### 2.2 Acceptance Criteria (Gherkin)

```gherkin
Scenario: MVP 핵심 데모 (Happy Path)
  Given 사용자가 강남역 좌표(37.4979, 127.0276)를 입력하면
  When 변환 → Gemini 검증 → 시각화 파이프라인이 실행될 때
  Then split-view에 두 지도가 나란히 표시되고
  And RMSE와 Harness Score가 오버레이로 표시된다
  And 전체 처리 시간이 30초 이내이다

Scenario: Self-Correction (Happy Path)
  Given 초기 RMSE가 3m을 초과할 때
  When Gemini가 오차 원인을 분석하면
  Then lat/lng 오프셋을 제안하고 1~2회 재시도하여 RMSE를 줄인다

Scenario: 테스트 좌표셋 일괄 검증 (Happy Path)
  Given 12개 랜드마크를 일괄 변환하면
  When RMSE를 계산할 때
  Then 평균 RMSE가 5m 이내이고 평균 Harness Score가 90점 이상이다

Scenario: 한국 영역 밖 좌표 (Error Path)
  Given 도쿄 좌표를 입력하면
  When 변환을 시도할 때
  Then split-view에 "한국 영역 밖 좌표" 에러 메시지를 오버레이로 표시한다

Scenario: Gemini API 장애 (Error Path)
  Given Gemini API가 타임아웃될 때
  When Self-Correction이 실패하면
  Then RMSE만 표시하고 "(Gemini 보정 없음)" 라벨을 추가한다
```

## 3. Functional Requirements (MVP)

| ID | Requirement | Priority | Dependencies |
|----|------------|----------|--------------|
| FR-001 | pyproj 기반 EPSG:4326 ↔ EPSG:5179 변환 엔진 | P0 (Must) | - |
| FR-002 | WGS84 통합 변환 API (입출력 모두 WGS84, 인증 없음) | P0 (Must) | FR-001 |
| FR-003 | RMSE 계산 + Harness Score 산출 (Ground Truth = 테스트 좌표 실측값) | P0 (Must) | FR-001 |
| FR-004 | Gemini Pro Self-Correction (표준 API + CoT 프롬프트, 1~2회 고정) | P0 (Must) | FR-003 |
| FR-005 | 테스트 좌표셋 12개 하드코딩 (좌표 + Ground Truth 포함) | P0 (Must) | - |
| FR-006 | split-view 데모 UI (Google Maps 2개 인스턴스, 좌=구글 뷰, 우=네이버 대체 뷰) | P0 (Must) | FR-002 |
| FR-007 | 입력 검증 + 에러 핸들링 + **에러 시 UI 오버레이 표시** | P0 (Must) | FR-006 |
| FR-008 | Google Colab 공개 노트북 배포 | P1 (Should) | FR-006 |
| FR-009 | 3분 데모 영상 녹화 | P1 (Should) | FR-006 |
| FR-010 | 아키텍처 다이어그램 + Gemini Integration 설명 200단어 | P1 (Should) | - |

## 4. Non-Functional Requirements

### 4.1 Performance (MVP)

- 좌표 변환 연산: < 10ms
- Gemini Self-Correction 1회: < 15s (표준 API)
- **전체 파이프라인 (입력→변환→검증→시각화): < 30s**
- 배치 변환 (12개, Gemini 미호출): < 1s

### 4.2 Accuracy

- 좌표 변환 RMSE: < 5m (도심)
- Harness Score: > 90점 (Gemini 보정 후)

### 4.3 Security (MVP — 최소화)

- **API 인증: 없음** (해커톤 데모, localhost/Colab 전용)
- 외부 API 키 (Google Maps, Gemini): .env 환경변수 관리
- `.env.example` 템플릿 제공, `.gitignore`에 `.env` 포함
- CORS: `*` 허용 (MVP only)

### 4.4 Compatibility

- Python: 3.10+
- 브라우저: Chrome 최신
- 패키지 매니저: pip + venv
- ASGI 서버: uvicorn

## 5. Technical Design

### 5.1 System Architecture (4-Layer Pipeline — Simplified)

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: DATA INGESTION                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Input Handler                                       │    │
│  │  - 사용자 입력 WGS84 좌표 (lat, lng)                  │    │
│  │  - 또는 테스트 좌표셋 12개 자동 로드                   │    │
│  │  - 입력 범위 검증 (한국 영역: lat 33~43, lng 124~132) │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│  Layer 2: COORDINATE ENGINE (Python 순차 함수)              │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  transform_pipeline()                                │    │
│  │                                                      │    │
│  │  Step 1: pyproj.transform(EPSG:4326 → EPSG:5179)    │    │
│  │  Step 2: pyproj.transform(EPSG:5179 → EPSG:4326)    │    │
│  │  Step 3: RMSE 계산 (vs Ground Truth)                 │    │
│  │  Step 4: Harness Score 산출                           │    │
│  │                                                      │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│  Layer 3: GEMINI HARNESS (Self-Correction)                  │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  gemini_self_correct(transform_result)               │    │
│  │                                                      │    │
│  │  1. Gemini Pro API 호출 (표준, CoT 프롬프트)          │    │
│  │     - 입력: 변환 데이터 + RMSE + Ground Truth        │    │
│  │     - 출력: JSON (오프셋 + reasoning)                │    │
│  │                                                      │    │
│  │  2. 보정 적용:                                        │    │
│  │     corrected_lat = original_lat + offset_lat        │    │
│  │     corrected_lng = original_lng + offset_lng        │    │
│  │                                                      │    │
│  │  3. RMSE 재계산 → Harness Score 갱신                  │    │
│  │                                                      │    │
│  │  [고정 루프: 최대 2회, 타임아웃 15s/회]               │    │
│  │  [폴백: Gemini 실패 시 RMSE만 표시]                   │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│  Layer 4: VISUALIZATION                                     │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  split-view HTML                                     │    │
│  │                                                      │    │
│  │  ┌─────────────┐  ┌─────────────┐                   │    │
│  │  │ Google Map   │  │ "Naver" Map  │                   │    │
│  │  │ (기본 스타일) │  │ (다른 스타일) │                   │    │
│  │  │ + 마커       │  │ + 보정 마커   │                   │    │
│  │  └─────────────┘  └─────────────┘                   │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────┐         │    │
│  │  │ RMSE: 0.3m | Harness Score: 97 | ✅ PASS│         │    │
│  │  │ Gemini: "데이텀 편차 0.3m, 보정 완료"    │         │    │
│  │  └─────────────────────────────────────────┘         │    │
│  │                                                      │    │
│  │  [에러 시: 빨간 오버레이 + 에러 메시지]               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Ground Truth 정의

> **이전 문제 (v3.0)**: pyproj는 결정론적 함수이므로 round-trip 오차가 나노미터 수준 → "RMSE 검증"이 무의미.

**v4.0 해결:**

Ground Truth는 **수동으로 실측한 참조 좌표**입니다. 각 랜드마크에 대해:

1. 구글 지도에서 해당 건물/교차로 중심점의 WGS84 좌표를 기록 (`google_coords`)
2. 네이버 지도에서 동일 건물/교차로 중심점의 WGS84 좌표를 기록 (`naver_coords`)
3. 두 좌표 간 거리 편차가 Ground Truth 오차 = **"두 지도 간 동일 지점의 렌더링 편차"**

```python
# Ground Truth 구조
{
  "name": "강남역",
  "google_coords": {"lat": 37.49794, "lng": 127.02764},  # 구글 지도에서 실측
  "naver_coords":  {"lat": 37.49781, "lng": 127.02770},  # 네이버 지도에서 실측
  "distance_m": 1.7  # Haversine 거리
}
```

**RMSE 의미**: pyproj 변환 + Gemini 보정 후 좌표가 네이버 실측 좌표와 얼마나 가까운지.

**데이터 수집 방법**: 해커톤 전날 구글/네이버 지도에서 12개 랜드마크의 좌표를 수동으로 수집하여 `data/test_coordinates.json`에 저장.

### 5.3 Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3.10+ / FastAPI / uvicorn | pyproj 생태계 |
| Coordinate | pyproj 3.6+ | EPSG 변환 표준 |
| AI | google-generativeai SDK (Gemini Pro) | **표준 API 호출, 특수 파라미터 불사용** |
| Math | NumPy | RMSE 계산 |
| Frontend | HTML/CSS/JS + Google Maps JS API | 경량 split-view |
| Deploy | Google Colab 노트북 | **공개 링크로 심사위원 접근 가능** |

### 5.4 API Specification (MVP)

> **인증**: 없음 (MVP). 모든 엔드포인트 공개.

#### `POST /api/v1/transform`

**Description**: 좌표 변환 + RMSE + Gemini Self-Correction 통합 엔드포인트

**Request Body**:
```json
{
  "latitude": "number (required) - WGS84 위도 (33.0 ~ 43.0)",
  "longitude": "number (required) - WGS84 경도 (124.0 ~ 132.0)",
  "run_harness": "boolean (optional) - Gemini Self-Correction 실행, default: true"
}
```

**Request Example**:
```json
{
  "latitude": 37.4979,
  "longitude": 127.0276,
  "run_harness": true
}
```

**Response 200 OK**:
```json
{
  "success": true,
  "data": {
    "input": {
      "latitude": 37.4979,
      "longitude": 127.0276,
      "label": "강남역"
    },
    "epsg5179": {
      "x": 954131.22,
      "y": 1944837.19
    },
    "ground_truth": {
      "naver_lat": 37.49781,
      "naver_lng": 127.02770,
      "source": "manual_measurement"
    },
    "harness": {
      "rmse_before_m": 1.7,
      "rmse_after_m": 0.3,
      "harness_score": 97,
      "iterations": 1,
      "corrections": [
        {
          "iteration": 1,
          "lat_offset": 0.0000012,
          "lng_offset": -0.0000008,
          "confidence": 0.96
        }
      ],
      "gemini_reasoning": "구글-네이버 간 1.7m 편차는 타일 렌더링 오프셋으로 추정. 위도 +0.12m, 경도 -0.08m 보정 적용하여 0.3m로 수렴.",
      "gemini_status": "success"
    }
  },
  "meta": {
    "processing_time_ms": 8200
  }
}
```

**Gemini 실패 시 Response** (폴백):
```json
{
  "success": true,
  "data": {
    "input": { "latitude": 37.4979, "longitude": 127.0276 },
    "harness": {
      "rmse_before_m": 1.7,
      "rmse_after_m": 1.7,
      "harness_score": 83,
      "iterations": 0,
      "corrections": [],
      "gemini_reasoning": null,
      "gemini_status": "timeout"
    }
  }
}
```

**Error Responses**:
| Status | Code | Message | UI 동작 |
|--------|------|---------|---------|
| 400 | INVALID_COORDINATES | Latitude out of range | split-view에 빨간 오버레이 |
| 422 | OUT_OF_COVERAGE | Outside Korea | split-view에 경고 오버레이 |
| 500 | TRANSFORM_ERROR | pyproj error | split-view에 에러 오버레이 |

---

#### `POST /api/v1/transform/batch`

**Description**: 12개 테스트 좌표셋 일괄 변환 + RMSE 요약. **Gemini 미호출** (성능).

**Request Body**:
```json
{
  "use_test_set": true
}
```

**Response 200 OK**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "label": "강남역",
        "rmse_m": 1.7,
        "harness_score": 83
      }
    ],
    "summary": {
      "total": 12,
      "avg_rmse_m": 1.8,
      "max_rmse_m": 4.2,
      "min_rmse_m": 0.5,
      "avg_harness_score": 82,
      "all_under_5m": true
    }
  },
  "meta": {
    "processing_time_ms": 45
  }
}
```

---

#### `GET /api/v1/test-coordinates`

**Description**: 12개 랜드마크 테스트 좌표셋 (Ground Truth 포함)

### 5.5 Gemini Self-Correction Protocol

```python
import google.generativeai as genai

# 표준 Gemini Pro API (특수 파라미터 없음)
model = genai.GenerativeModel("gemini-2.0-flash")  # 또는 gemini-1.5-pro

SYSTEM_PROMPT = """당신은 지도 좌표계 정합성 검증 에이전트입니다.

두 지도(구글/네이버)에서 동일 지점의 WGS84 좌표 편차를 분석합니다.
RMSE 오차의 원인을 단계적으로 추론하고, 보정 오프셋을 제안하세요.

가능한 오차 원인:
- 지도 타일 렌더링 시스템의 미세한 좌표 기준점 차이
- 투영법 변환 시 비선형 왜곡
- 건물 밀집 지역의 GPS 기준점 편차

반드시 아래 JSON 형식으로 응답하세요:
{
  "lat_offset": float,     // 위도 보정값 (도 단위, ±0.001 이내)
  "lng_offset": float,     // 경도 보정값 (도 단위, ±0.001 이내)
  "confidence": float,     // 보정 신뢰도 (0~1)
  "reasoning": string      // 오차 원인 한국어 분석 (1~2문장)
}"""

def gemini_self_correct(transform_data, max_iterations=2, timeout_s=15):
    """Self-Correction 루프 (고정 최대 2회)"""
    current_rmse = transform_data["rmse_m"]
    corrections = []

    for i in range(max_iterations):
        if current_rmse < 1.0:  # 충분히 작으면 중단
            break

        try:
            response = model.generate_content(
                f"{SYSTEM_PROMPT}\n\n변환 데이터: {transform_data}\nRMSE: {current_rmse}m",
                generation_config={"response_mime_type": "application/json"},
                request_options={"timeout": timeout_s}
            )
            correction = json.loads(response.text)

            # 보정 적용 (단순 오프셋 덧셈)
            transform_data["lat"] += correction["lat_offset"]
            transform_data["lng"] += correction["lng_offset"]

            # RMSE 재계산
            current_rmse = calculate_rmse(transform_data, ground_truth)

            corrections.append({
                "iteration": i + 1,
                "lat_offset": correction["lat_offset"],
                "lng_offset": correction["lng_offset"],
                "rmse_after": current_rmse,
                "confidence": correction["confidence"]
            })
        except Exception:
            # 폴백: Gemini 실패 시 RMSE만 반환
            break

    harness_score = max(0, 100 - (current_rmse * 10))
    return current_rmse, harness_score, corrections
```

**핵심 설계 결정:**
- **특수 파라미터 불사용**: `thinking_level`, `thinking_budget` 등에 의존하지 않음
- **CoT 프롬프트**: 시스템 프롬프트 자체에 "단계적 추론" 지시를 포함
- **구조화 출력**: `response_mime_type: application/json`으로 파싱 안정성 확보
- **폴백**: Gemini 타임아웃/에러 시 RMSE만 표시 (데모 중단 방지)

### 5.6 Key Algorithms

#### 5.6.1 좌표 변환 (pyproj)

```python
from pyproj import Transformer

t_forward = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
t_reverse = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

def transform_coordinate(lat, lng):
    x, y = t_forward.transform(lng, lat)
    lat_back, lng_back = t_reverse.transform(x, y)  # round-trip 검증
    return {"epsg5179": {"x": x, "y": y}, "roundtrip": {"lat": lat_back, "lng": lng_back}}
```

#### 5.6.2 RMSE 계산

```python
from math import radians, sin, cos, sqrt, atan2

def haversine_m(lat1, lng1, lat2, lng2):
    """두 WGS84 좌표 간 거리 (미터)"""
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def calculate_rmse(coords_list, ground_truth_list):
    """N개 좌표의 RMSE (미터)"""
    errors_sq = [haversine_m(c["lat"], c["lng"], g["lat"], g["lng"])**2
                 for c, g in zip(coords_list, ground_truth_list)]
    return sqrt(sum(errors_sq) / len(errors_sq))
```

#### 5.6.3 Harness Score

```
Harness Score = max(0, 100 - (RMSE_m × 10))

// RMSE 0.0m → 100점
// RMSE 0.3m → 97점
// RMSE 1.0m → 90점
// RMSE 5.0m → 50점
// RMSE 10m+ → 0점
```

### 5.7 split-view 구현 (네이버 대체)

MVP에서 네이버 지도 API 연동 대신 **Google Maps 2개 인스턴스**를 사용합니다:

```html
<div style="display: grid; grid-template-columns: 1fr 1fr; height: 60vh;">
  <!-- 좌측: "구글 맵" (기본 스타일) -->
  <div id="google-map"></div>

  <!-- 우측: "네이버 대체" (Satellite/Terrain 스타일 + 보정 마커) -->
  <div id="naver-substitute-map"></div>
</div>

<div id="score-overlay">
  <!-- RMSE / Harness Score / Gemini 분석 결과 -->
</div>

<div id="error-overlay" style="display:none; background:rgba(255,0,0,0.8);">
  <!-- 에러 메시지 -->
</div>
```

**좌측 (구글)**: 기본 roadmap 스타일, 입력 좌표에 빨간 마커
**우측 (네이버 대체)**: satellite 또는 terrain 스타일, 보정된 좌표에 파란 마커
**하단**: RMSE, Harness Score, Gemini reasoning 오버레이

## 6. Implementation Phases (8시간 타임라인)

### Pre-Hackathon Checklist (전날 필수)

- [ ] Google Cloud Console에서 프로젝트 생성
- [ ] Google Maps JavaScript API 활성화 + API 키 발급
- [ ] `https://maps.googleapis.com/maps/api/js?key=KEY` 로딩 테스트
- [ ] Google AI Studio에서 Gemini API 키 발급
- [ ] `genai.GenerativeModel("gemini-2.0-flash")` 호출 테스트 (JSON 응답 확인)
- [ ] 구글/네이버 지도에서 12개 랜드마크 좌표 수동 수집 → `test_coordinates.json` 사전 작성

### Phase 1: 환경 설정 (10:00~11:00) — 1시간

**형섭님:**
- [ ] Gemini Self-Correction 프롬프트 작성 및 테스트
- [ ] Harness Score 공식 확인

**팀원:**
- [ ] FastAPI 프로젝트 초기화 (pip + venv)
- [ ] .env 설정 (GOOGLE_MAPS_KEY, GEMINI_API_KEY)
- [ ] .gitignore, .env.example 생성

### Phase 2: 핵심 구현 (11:00~13:00) — 2시간

**형섭님:**
- [ ] pyproj 변환 함수 구현
- [ ] RMSE 계산 (haversine) 구현
- [ ] Gemini Self-Correction 루프 구현 (1~2회)
- [ ] 12개 테스트 좌표셋 검증

**팀원:**
- [ ] POST /api/v1/transform 엔드포인트
- [ ] POST /api/v1/transform/batch 엔드포인트 (Gemini 미호출)
- [ ] GET /api/v1/test-coordinates 엔드포인트
- [ ] split-view HTML 레이아웃 (CSS grid 2-column)

### Phase 3: 점심 + 중간 정리 (13:00~13:30)

- [ ] 중간 통합 테스트 → 잔여 스코프 확인

### Phase 4: UI 완성 + 폴백 (13:30~15:30) — 2시간

**형섭님:**
- [ ] Self-Correction 최종화 + 폴백 (Gemini 실패 시 RMSE만)
- [ ] 에러 핸들링 (INVALID_COORDINATES, OUT_OF_COVERAGE)

**팀원:**
- [ ] Google Maps 2개 인스턴스 split-view 완성
- [ ] RMSE / Harness Score / Gemini reasoning 오버레이
- [ ] 에러 시 빨간 오버레이 표시
- [ ] API 응답 파싱 및 마커 동기화

### Phase 5: 통합 테스트 (15:30~16:30) — 1시간

- [ ] 두 파트 연결 (Backend ↔ Frontend)
- [ ] 강남역 좌표 E2E 테스트
- [ ] 12개 배치 테스트
- [ ] 에러 시나리오 테스트 (도쿄 좌표, Gemini 타임아웃)
- [ ] 버그 수정

### Phase 6: 데모 + 제출 (16:30~18:00) — 1.5시간

- [ ] Google Colab 노트북 작성 (FastAPI 서버 + ngrok 터널 + HTML)
- [ ] Colab 공개 링크 생성 및 테스트
- [ ] 3분 데모 영상 녹화 (강남역 시나리오)
- [ ] 아키텍처 다이어그램 작성
- [ ] 200단어 Gemini Integration 설명
- [ ] Devpost 제출

## 7. Team Assignment

| Member | Role | Scope |
|--------|------|-------|
| 형섭님 | Harness & Logic | Gemini 프롬프트, pyproj, RMSE, Self-Correction |
| 팀원 | Tool & API | FastAPI, split-view UI, Colab 배포, 데모 영상 |

```
10:00  11:00  12:00  13:00  14:00  15:00  16:00  17:00  18:00
  │      │      │      │      │      │      │      │      │
A ██ Setup ██████ pyproj+Gemini ████ ██ Correction+Error ██ ▓▓ 통합 ▓▓
B ██ Setup ██████ API+UI ██████████ ██ split-view+Score ██ ▓▓ 통합 ▓▓ 데모
                               점심
```

## 8. Success Metrics (MVP)

| Metric | Target |
|--------|--------|
| 좌표 변환 RMSE | < 5m (12개 평균) |
| Harness Score | > 90점 (Gemini 보정 후) |
| MVP 데모 | 강남역 한 장면 동작 |
| 전체 파이프라인 시간 | < 30s |
| Devpost 제출 | 완료 |

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini API 속도 지연 (>15s) | High | 폴백: RMSE만 표시 + "(보정 없음)" |
| Gemini JSON 파싱 실패 | Medium | try/except + 기본값 반환 |
| Google Maps API 키 미작동 | High | **전날 사전 테스트 필수** |
| split-view 렌더링 이슈 | Medium | 최소 CSS grid로 단순화 |
| Colab ngrok 터널 불안정 | Medium | 폴백: 로컬 데모 영상 녹화 후 제출 |
| 12개 Ground Truth 수집 시간 | Low | **전날 사전 수집 완료** |

## 10. External Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| pyproj | 3.6+ | EPSG 좌표 변환 |
| FastAPI | 0.100+ | REST API |
| uvicorn | 0.24+ | ASGI 서버 |
| google-generativeai | latest | Gemini Pro API (표준 호출) |
| numpy | 1.24+ | 수치 연산 |
| Google Maps JS API | v3 | 지도 표시 (2개 인스턴스) |
| Google Colab | - | 데모 배포 + 공개 노트북 |
| pyngrok | 7.0+ | Colab에서 FastAPI 외부 노출 |

## 11. Test Coordinate Set (12개 랜드마크)

| # | Name | Google lat | Google lng | Naver lat | Naver lng | Category |
|---|------|-----------|-----------|-----------|-----------|----------|
| 1 | 강남역 | 37.49794 | 127.02764 | TBD | TBD | 교통 |
| 2 | 서울시청 | 37.56668 | 126.97841 | TBD | TBD | 관공서 |
| 3 | 광화문 | 37.57600 | 126.97690 | TBD | TBD | 랜드마크 |
| 4 | 남산타워 | 37.55121 | 126.98828 | TBD | TBD | 랜드마크 |
| 5 | 코엑스 | 37.51190 | 127.05930 | TBD | TBD | 상업 |
| 6 | 여의도공원 | 37.52540 | 126.92440 | TBD | TBD | 공원 |
| 7 | 홍대입구역 | 37.55712 | 126.92370 | TBD | TBD | 교통 |
| 8 | 잠실종합운동장 | 37.51522 | 127.07300 | TBD | TBD | 스포츠 |
| 9 | 경복궁 | 37.57977 | 126.97699 | TBD | TBD | 문화재 |
| 10 | 이태원역 | 37.53454 | 126.99458 | TBD | TBD | 교통 |
| 11 | 동대문DDP | 37.56714 | 127.00920 | TBD | TBD | 상업 |
| 12 | 서울대입구역 | 37.48137 | 126.95270 | TBD | TBD | 교통 |

> **TBD**: 해커톤 전날 네이버 지도에서 동일 지점 좌표를 수동 수집하여 채움

## 12. Submission Checklist

- [ ] Google Colab 공개 노트북 링크
- [ ] 또는 공개 GitHub 저장소 링크
- [ ] 3분 데모 영상 (강남역 시나리오)
- [ ] 200단어 Gemini Integration 설명
- [ ] 아키텍처 다이어그램
- [ ] Devpost 제출
