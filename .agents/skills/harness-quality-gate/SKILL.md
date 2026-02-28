---
description: Automatically run quality gates (RMSE, Harness Score) to enforce the Harness Operating Principles and DeepThink mode on projection errors.
---

# Harness Quality Gate Skill

**Trigger:** "품질 검사해줘", "런 게이트", "방향성 점검", "run quality gate" 또는 변환 로직 변경 후 커밋을 시도할 때 작동합니다.

## Core Directives

당신은 GeoHarness 프로젝트의 **측정 우선(Measurement First)** 원칙과 **DeepThink** 방어 기제를 집행합니다.

### 1. 측정 우선 (Measurement First) 
코드를 수정하거나 확정하기 전에 반드시 정합성을 수치로 증명해야 합니다.
- 테스트 스크립트(예: `pytest tests/test_engine.py`)를 실행하여 WGS84 -> GRS80/TM 변환에 대한 **RMSE(m)** 및 **Harness Score**를 산출하십시오.
- Harness Score 공식: `max(0, 100 - (RMSE_m * 10))`

### 2. DeepThink 가동 (오차 2m 이상 발생 시)
만약 측정된 **RMSE가 2.0m를 초과(Harness Score 80점 미만)**하는 경우:
- **즉시 코드 수정을 중단(Block)하십시오.** 단순한 파라미터 끼워 맞추기를 엄격히 금지합니다.
- **DeepThink 모드 분기:** 투영 왜곡의 원인을 논리적으로 분석하는 단계로 넘어가십시오.
- 타원체 변환(Datum Shift) 문제인지, 카메라 뷰포트(POV) 파라미터의 동기화 문제인지 원인을 추적합니다.

### 3. 지오메트리 중심 정렬 (Geometry-Centric Alignment)
왜곡 원인 분석 및 해결책 도출 시:
- 간판(Signboard) 등 텍스트나 가변적 피처(Feature)를 기준으로 삼지 마십시오.
- **도로의 위상(Topology)**과 **교차로의 각도**, **고정된 건축물 폴리곤**을 정렬의 유일한 기준으로 삼으십시오.

### 4. Output Format (출력 규격 적용)
결과를 반환할 때 반드시 다음 구조를 엄격히 따르십시오:
- `[Analysis]`: 현재 좌표 및 방향 데이터 또는 위상 분석 결과 기록
- `[Transformation]`: 변환된 로컬 좌표 빛 카메라 파라미터 조정안
- `[Harness Score]`: 최종 산출된 측정 점수 (0-100)
- `[Improvement]`: 오차 보정을 위한 다음 피드백 루프 제안
