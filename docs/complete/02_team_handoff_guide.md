# 팀원 가이드: 네이버 데이터 수집 & ML 학습 준비

> 이 문서는 `git pull` 후 Antigravity Agent에게 명령하여 작업을 이어갈 수 있도록 작성되었습니다.

---

## 🚀 Quick Start (5분 세팅)

### Step 1: 환경 설정
```bash
# 프로젝트 최신 코드 받기
git pull origin main

# 가상환경 활성화 및 의존성 설치
python3 -m venv venv
source venv/bin/activate
pip install aiohttp beautifulsoup4 pyproj pydantic pydantic-settings python-dotenv

# .env 파일 생성 (이미 있다면 스킵)
cp .env.example .env
```

### Step 2: 네이버 API 키 발급
1. [developers.naver.com](https://developers.naver.com/apps/#/register?api=search) 접속
2. 애플리케이션 등록 → **검색 > 지역** API 선택
3. 발급받은 `Client ID`와 `Client Secret`을 `.env`에 입력:
```dotenv
NAVER_CLIENT_ID=발급받은_클라이언트_ID
NAVER_CLIENT_SECRET=발급받은_클라이언트_시크릿
```

### Step 3: 네이버 데이터 수집 실행
```bash
# 구글에서 수집한 120개 POI 이름으로 네이버 좌표 매칭
source venv/bin/activate
PYTHONPATH=src python src/ml/naver_collector.py
```

**결과:** `data/ml_dataset.csv` 생성 (Google WGS84 ↔ Naver KATECH 좌표 쌍)

---

## 📊 현재 수집된 데이터 현황

| 파일 | 건수 | 내용 |
|------|------|------|
| `data/google_poi_base.csv` | 120 | 성수동 POI의 Google WGS84 좌표 |
| `data/vworld_anchors.csv` | 16 | VWorld 고정 기준점 (역출구/교차로/공공시설) |
| `data/ml_dataset.csv` | ⏳ | 네이버 수집 후 생성 예정 |

---

## 🤖 Antigravity Agent에게 내릴 수 있는 명령어

### 네이버 데이터 수집
```
"네이버 API 키를 .env에 설정했어. naver_collector.py를 실행해서
data/ml_dataset.csv를 만들어줘."
```

### ML 학습 준비 (Colab)
```
"data/ml_dataset.csv가 완성됐어. Google Colab에서 RAPIDS로
XGBoost 학습할 수 있도록 rapids_trainer.py를 업데이트하고,
Colab 노트북(.ipynb)도 만들어줘."
```

### 오프셋 분석
```
"vworld_anchors.csv의 기준점과 google_poi_base.csv, ml_dataset.csv를
비교해서 각 지도 소스별 오프셋 벡터를 분석해줘.
성수동 지역의 왜곡 히트맵도 시각화해줘."
```

---

## 🏗️ 파이프라인 아키텍처 (전체 흐름)

```
 ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐
 │ Google Places    │   │ VWorld Geocoder   │   │ Naver Search    │
 │ (WGS84)         │   │ (Ground Truth)    │   │ (KATECH)        │
 │ ✅ 120개 수집    │   │ ✅ 16개 수집      │   │ ⏳ 대기중        │
 └────────┬────────┘   └────────┬──────────┘   └────────┬────────┘
          │                     │                       │
          ▼                     ▼                       ▼
  google_poi_base.csv   vworld_anchors.csv      ml_dataset.csv
          │                     │                       │
          └─────────────────────┼───────────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │  Offset Calculation   │
                    │  Google→Anchor 거리   │
                    │  Naver →Anchor 거리   │
                    │  ΔOffset = 차이       │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  RAPIDS ML Training   │
                    │  (Google Colab GPU)    │
                    │  XGBoost Regressor    │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  decoder.pkl 배포     │
                    │  src/api/server.py    │
                    │  실시간 좌표 보정      │
                    └───────────────────────┘
```

---

## ⚠️ 주의사항
- `.env` 파일은 **절대 커밋하지 마세요** (`.gitignore`에 등록됨)
- 네이버 API는 일일 25,000건 제한이 있으므로, 120건은 충분히 여유
- `data/` 폴더의 CSV 파일은 커밋해도 됩니다 (민감 정보 없음)
- VWorld API는 무료이지만 일일 호출 제한이 있을 수 있음
