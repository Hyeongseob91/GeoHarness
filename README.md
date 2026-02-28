# GeoHarness Spatial-Sync MVP

대한민국 지리정보체계(GIS) 좌표(GRS80/TM)와 Google Maps(WGS84) 간의 공간 왜곡을 **Gemini AI**의 시각적 추론(Self-Correction)을 통해 1% 오차 이내로 동기화하는 프레임워크입니다.

---

## 🚀 팀원 & 심사위원을 위한 "1분 배포 가이드" (For @Hyeongseob91)

현재 Github Actions를 통해 **코드가 `main`에 머지되면 자동으로 GCP Cloud Run에 배포**되도록 완벽한 CI/CD 파이프라인(`deploy-cloud-run.yml`)이 세팅되어 있습니다! 🎉

다만, API 키 유출 방지와 보안을 위해 **레포지토리 소유자(형섭님)** 께서 딱 한 번만 아래의 4가지 "비밀키(Secrets)"를 Github 설정에 넣어주셔야 자동 배포가 정상적으로 마무리됩니다. 
*(이것만 넣어주시면 앞으로 팀원 누구나 Push할 때마다 자동으로 배포 링크가 갱신됩니다! 😆)*

### 🔑 셋팅 방법 (소요 시간: 1분)

1. 위쪽 메뉴 탭에서 **[Settings]** 클릭
2. 좌측 사이드바에서 **[Secrets and variables]** -> **[Actions]** 클릭
3. 녹색 **[New repository secret]** 버튼을 눌러 다음 4개의 값을 차례대로 생성해 주세요.

| Name (이름) | Secret (값) | 설명 |
|---|---|---|
| `GCP_CREDENTIALS` | `{"type": "service_account"...}` | **가장 중요합니다!** 구글 클라우드 콘솔의 `IAM -> 서비스 계정` 메뉴에서 새 키(JSON)를 발급받아 그 **내용 전체**를 그대로 복붙해 주세요. (역할은 `Cloud Run 관리자`, `서비스 계정 사용자` 2개 부여 필요) |
| `GOOGLE_MAPS_KEY` | `AIzaSyD...` | 구글 맵스 렌더링을 위한 API 키 |
| `GEMINI_API_KEY` | `AIzaSyB...` | Gemini Self-Correction 추론을 위한 API 키 |
| `NAVER_CLIENT_ID` | `5u1b9...` | 우측 네이버 지도 렌더링용 Client ID |

위 설정이 끝났다면, [Actions 탭]에 들어가서 가장 최근 실패한 배포(빨간색 ❌)를 클릭 후 우측 상단의 **[Re-run all jobs]** 버튼만 눌러주시면 끝입니다! 

> 💡 *팁: 나중에 해커톤 데모 영상을 찍으실 때, Actions에서 성공적으로 생성된 Cloud Run 배포 URL을 공유해 주시면 모든 팀원이 핸드폰/PC에서 즉석으로 동기화 테스트를 해볼 수 있습니다!*

---

## 🛠 로컬 개발 환경 실행 방법

로컬에서 테스트하실 팀원(지민님 등)은 아래 명령어를 참고해 주세요.

```bash
# 1. uv 패키지 매니저로 의존성 동기화
uv sync

# 2. 로컬 서버 기동 (핫 리로드 적용)
PYTHONPATH=src uv run uvicorn src.main:app --reload
```
브라우저에서 `http://localhost:8000` 으로 접속하시면 UI를 확인하실 수 있습니다. (루트의 `.env` 파일에 API 키 세팅 필수)
