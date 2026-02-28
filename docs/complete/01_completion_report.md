# GeoHarness v2.0 — ML 데이터 파이프라인 완료 보고서

> 작성일: 2026-02-28 | 작업자: Member 1 (Antigravity Agent 활용)

---

## 📋 완료된 작업 요약

### 1. 프로젝트 구조 리팩토링
- `app/` 폴더(초기 스캐폴딩 스텁) → `src/`로 통합 완료
- `src/config.py`에 환경변수 통합 관리 (pydantic-settings)
- `.env.example` 생성: 모든 API 키 플레이스홀더 포함

### 2. Google WGS84 좌표 수집 ✅
- **스크립트:** `src/ml/dataset_generator.py`
- **결과:** `data/google_poi_base.csv` — **120개 POI**
- 대상 지역: 성수동 카페/식당/팝업스토어, 연무장길, 뚝섬역, 서울숲역
- Google Places API (Legacy Text Search) 사용

### 3. VWorld Ground Truth 기준점 수집 ✅
- **스크립트:** `src/ml/vworld_collector.py`
- **결과:** `data/vworld_anchors.csv` — **16개 고정 기준점**
- 지하철역 출구 (성수역/뚝섬역/서울숲역)
- 도로 교차점 (연무장길 시작·끝점, 뚝섬로, 아차산로 등)
- 공공시설 (서울숲 정문, 우체국, 구청, 주민센터)
- 각 기준점에 WGS84 좌표 + PyProj EPSG:5179 좌표 포함

### 4. Naver 수집기 구현 완료 (실행 대기) ⏳
- **스크립트:** `src/ml/naver_collector.py`
- 네이버 검색 Open API (지역 검색) 사용
- `NAVER_CLIENT_ID` + `NAVER_CLIENT_SECRET` 설정 후 실행 가능

---

## 📁 생성된 파일 목록

| 파일 | 역할 |
|------|------|
| `src/ml/dataset_generator.py` | Google Places API로 WGS84 좌표 추출 |
| `src/ml/vworld_collector.py` | VWorld 고정 기준점(Anchor) 수집 |
| `src/ml/naver_collector.py` | 네이버 지역 검색 API로 KATECH 좌표 매칭 |
| `src/ml/rapids_trainer.py` | NVIDIA RAPIDS ML 학습 스크립트 (Colab용) |
| `src/config.py` | 환경변수 통합 관리 |
| `data/google_poi_base.csv` | 구글 WGS84 좌표 120개 |
| `data/vworld_anchors.csv` | VWorld 기준점 16개 |
| `data/ground_truth_with_projections.csv` | PyProj 투영 좌표 120개 |
| `.env.example` | API 키 템플릿 |
| `.env.sample` | API 키 템플릿 (백업) |

---

## 🔑 필요한 API 키 목록

| 키 | 발급처 | 현재 상태 |
|----|--------|----------|
| `GOOGLE_MAPS_KEY` | [Google Cloud Console](https://console.cloud.google.com/) | ✅ 설정됨 |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) | ✅ 설정됨 |
| `VWORLD_API_KEY` | [VWorld](https://www.vworld.kr/dev/v4api.do) | ✅ 설정됨 |
| `NAVER_CLIENT_ID` | [Naver Developers](https://developers.naver.com/apps/#/register?api=search) | ❌ 미설정 |
| `NAVER_CLIENT_SECRET` | 위와 동일 (같이 발급) | ❌ 미설정 |
