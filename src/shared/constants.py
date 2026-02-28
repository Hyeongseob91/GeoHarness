"""
GeoHarness 공유 상수 정의

좌표계 코드, Harness Score 공식 파라미터, API 제한 등
프로젝트 전역에서 사용되는 불변 값들을 중앙 관리합니다.
"""

# ─── 좌표계 (Coordinate Reference Systems) ────────────────
EPSG_WGS84 = "EPSG:4326"          # Google Maps 기본 좌표계
EPSG_KOREA_TM = "EPSG:5179"       # 한국 GRS80 중부원점 (VWorld 공식)
EPSG_KATECH = "EPSG:5178"         # KATECH TM128 (네이버 지도 내부)

# ─── 한국 영토 경계 (유효성 검증용) ───────────────────────
KOREA_LAT_RANGE = (33.0, 43.0)
KOREA_LNG_RANGE = (124.0, 132.0)

# ─── Harness Score ────────────────────────────────────────
HARNESS_MULTIPLIER = 10            # RMSE 1m당 감점 포인트
HARNESS_MAX = 100                  # 만점
HARNESS_DEEPTHINK_THRESHOLD = 80   # 이 점수 미만 시 DeepThink 모드 가동

# ─── API Rate Limits ──────────────────────────────────────
NAVER_DAILY_LIMIT = 25_000
GOOGLE_RESULTS_PER_QUERY = 20
VWORLD_REQUESTS_PER_SEC = 1

# ─── 서버 설정 ────────────────────────────────────────────
DEFAULT_PORT = 8080                # GCP Cloud Run 기본 포트
DEV_PORT = 8000                    # 로컬 개발 포트
