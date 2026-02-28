# Task Plan: Spatial-Sync (GeoHarness) — MVP v4.0

> **Generated from**: docs/prd/PRD_spatial-sync.md (v4.0 Risk-Cleared)
> **Created**: 2026-02-28
> **Status**: pending
> **Time Budget**: 8시간

## Execution Config

| Option | Value | Description |
|--------|-------|-------------|
| `auto_commit` | true | 완료 시 자동 커밋 |
| `commit_per_phase` | true | Phase별 중간 커밋 |
| `quality_gate` | true | /auto-commit 품질 검사 |

## Pre-Hackathon (전날 필수)

- [ ] Google Cloud Console 프로젝트 생성 + Maps JS API 키 발급 + 테스트
- [ ] Google AI Studio Gemini API 키 발급 + `gemini-2.0-flash` 호출 테스트
- [ ] 12개 랜드마크 구글/네이버 지도 좌표 수동 수집 → test_coordinates.json 작성

## 8시간 타임라인

```
10:00  11:00  12:00  13:00  14:00  15:00  16:00  17:00  18:00
  │      │      │      │      │      │      │      │      │
A ██ Setup ██████ pyproj+Gemini ████ ██ Correction+Error ██ ▓▓ 통합 ▓▓
B ██ Setup ██████ API+UI ██████████ ██ split-view+Score ██ ▓▓ 통합 ▓▓ 데모
                               점심
```

## Phases

### Phase 1: 환경 설정 (10:00~11:00)

**형섭님:**
- [ ] Gemini Self-Correction CoT 프롬프트 작성
- [ ] Gemini JSON 응답 테스트 (response_mime_type)
- [ ] Harness Score 공식 확인

**팀원:**
- [ ] FastAPI 프로젝트 초기화 (pip + venv)
- [ ] .env / .env.example / .gitignore 설정
- [ ] 의존성 설치 (pyproj, fastapi, uvicorn, google-generativeai, numpy)
- [ ] Google Maps API 키 로딩 확인

### Phase 2: 핵심 구현 (11:00~13:00)

**형섭님:**
- [ ] pyproj 변환 함수 (EPSG:4326 ↔ EPSG:5179)
- [ ] Haversine RMSE 계산 함수
- [ ] Gemini Self-Correction 루프 (1~2회, 15s 타임아웃)
- [ ] test_coordinates.json 로드 + 12개 배치 RMSE 검증

**팀원:**
- [ ] POST /api/v1/transform 엔드포인트
- [ ] POST /api/v1/transform/batch 엔드포인트 (Gemini 미호출)
- [ ] GET /api/v1/test-coordinates 엔드포인트
- [ ] split-view HTML 레이아웃 (CSS grid)

### Phase 3: 점심 (13:00~13:30)

- [ ] 중간 통합 테스트 계획

### Phase 4: UI + 폴백 (13:30~15:30)

**형섭님:**
- [ ] Self-Correction 폴백 (Gemini 실패 → RMSE만)
- [ ] 에러 핸들링 (INVALID_COORDINATES, OUT_OF_COVERAGE)
- [ ] Harness Score 산출 최종화

**팀원:**
- [ ] Google Maps 2개 인스턴스 split-view
- [ ] RMSE / Harness Score / Gemini reasoning 오버레이
- [ ] 에러 시 빨간 오버레이
- [ ] API fetch + 마커 동기화

### Phase 5: 통합 테스트 (15:30~16:30)

- [ ] Backend ↔ Frontend 연결
- [ ] 강남역 E2E 테스트
- [ ] 12개 배치 테스트
- [ ] 에러 시나리오 (도쿄, Gemini 타임아웃)
- [ ] 버그 수정

### Phase 6: 데모 + 제출 (16:30~18:00)

- [ ] Colab 노트북 (FastAPI + pyngrok + HTML)
- [ ] Colab 공개 링크 테스트
- [ ] 3분 데모 영상 녹화
- [ ] 아키텍처 다이어그램
- [ ] 200단어 Gemini Integration 설명
- [ ] Devpost 제출

## MVP 성공 기준

| Metric | Target |
|--------|--------|
| 강남역 한 장면 | 입력→변환→Gemini 검증→split-view |
| RMSE | < 5m (12개 평균) |
| Harness Score | > 90점 |
| 전체 파이프라인 | < 30s |
| Devpost | 제출 완료 |

## Progress

| Metric | Value |
|--------|-------|
| Total Tasks | 0/30 |
| Current Phase | - |
| Status | pending |
