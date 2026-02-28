# GeoHarness ENDING PLAN: 배포까지의 병렬 워크플로우

> 작성일: 2026-02-28 14:30 KST  
> Person A (형섭): ML/Research | Person B (팀원): Product/Integration

---

## 타임라인 개요

```
Phase 1: 데이터 완성     Phase 2: ML + 골격      Phase 3: 통합      Phase 4: 배포
   (병렬)                   (병렬)                 (합류)            (FINAL)
    
A: 대기/Colab 준비      A: Colab에서             A+B: decoder.pkl    A: Docker 검증
B: Naver 수집              XGBoost 학습              통합 테스트      B: GCP 시크릿
                        B: inference.py              Harness 검증     → git push
                           + Dashboard              Score ≥ 90       → 자동 배포
```

---

## Phase별 상세 내용은 아래 문서를 참고하세요:
→ Antigravity Plan: `implementation_plan.md` (이 대화의 artifact)

---

## Person B: Antigravity에게 내릴 명령어 모음

### 1. 네이버 데이터 수집 후
```
"네이버 API 키를 .env에 설정했어. docs/complete/02_team_handoff_guide.md 읽고
naver_collector.py 실행해서 data/ml_dataset.csv 만들어줘."
```

### 2. 서비스 골격 구축 (Person A 모델 대기 중)
```
"src/engine/inference.py를 만들어줘.
 - load_model()로 decoder.pkl 로드
 - predict_offset(g_lat, g_lng) → (corrected_lat, corrected_lng) 반환
 - 모델 없으면 PyProj 기본 변환으로 fallback

 src/api/local_verifier.py도 만들어줘.
 - 보정된 좌표로 네이버 역지오코딩 호출
 - 실제 상호명 + 주소 반환"
```

### 3. decoder.pkl 받은 후
```
"Person A가 완성한 decoder.pkl을 src/models/에 넣었어.
 inference.py의 mock을 실제 모델로 교체하고,
 server.py에 /api/v1/predict-offset 엔드포인트를 연동해줘.
 그리고 전체 테스트 돌려줘."
```

---

## 배포 체크리스트

- [ ] `uv run pytest tests/ -v` → 전체 통과
- [ ] `docker build -t geoharness:v2 .` → 빌드 성공
- [ ] GitHub Secrets 등록 (GCP_CREDENTIALS, API Keys)
- [ ] `git push origin main` → CI/CD 자동 배포
- [ ] Cloud Run URL 접속 → 라이브 데모 확인
