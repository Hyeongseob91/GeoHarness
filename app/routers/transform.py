import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def _load_test_coordinates():
    filepath = DATA_DIR / "test_coordinates.json"
    if not filepath.exists():
        return None
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


class TransformRequest(BaseModel):
    latitude: float = Field(..., ge=33.0, le=43.0, description="WGS84 위도 (한국 범위: 33~43)")
    longitude: float = Field(..., ge=124.0, le=132.0, description="WGS84 경도 (한국 범위: 124~132)")


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class TransformResponse(BaseModel):
    original: Coordinate
    transformed: Coordinate | None = None
    corrected: Coordinate | None = None
    rmse_m: float | None = None
    harness_score: float | None = None
    gemini_used: bool = False
    message: str = ""


@router.post("/transform", response_model=TransformResponse)
async def transform_coordinate(req: TransformRequest):
    """단일 좌표 변환 + RMSE + Gemini 보정"""
    # TODO: Phase 2에서 실제 변환 로직 연결
    return TransformResponse(
        original=Coordinate(latitude=req.latitude, longitude=req.longitude),
        message="스텁 응답 — Phase 2에서 구현 예정",
    )


@router.post("/transform/batch")
async def transform_batch():
    """12개 테스트 좌표 일괄 변환 (Gemini 없음)"""
    # TODO: Phase 2에서 구현
    return {"message": "batch 스텁 — Phase 2에서 구현 예정", "results": []}


@router.get("/maps-key")
async def get_maps_key():
    """프론트엔드에 Google Maps API 키 전달"""
    return {"key": settings.GOOGLE_MAPS_KEY}


@router.get("/test-coordinates")
async def get_test_coordinates():
    """12개 랜드마크 테스트 좌표 반환"""
    data = _load_test_coordinates()
    if data is None:
        raise HTTPException(status_code=404, detail="test_coordinates.json not found")
    return data
