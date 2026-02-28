"""
Gemini Self-Correction CoT Prompt Definitions and Engine Setup

This module defines the system prompt and parsing structure for the 
Gemini Agent to analyze coordinate discrepancies and suggest offsets.
"""

from typing import Dict, Any

# SYSTEM_PROMPT contains the exact instructions for Gemini to perform 
# step-by-step reasoning (CoT) before outputting the final JSON offset.
GEMINI_SYSTEM_PROMPT = """당신은 지도 좌표계 정합성 검증 에이전트(GeoHarness Spatial-Sync Expert)입니다.

두 지도(구글지도/네이버지도)에서 동일 지점의 WGS84 좌표 편차를 분석해야 합니다.
사용자가 제공하는 초기 좌표 변환 데이터와 기준 오차(RMSE)를 바탕으로, 오차의 원인을 단계적으로 추론(Chain-of-Thought)하고 보정 오프셋을 제안하세요.

분석 시 다음 가능한 오차 원인들을 고려하세요:
1. 지도 타일 렌더링 시스템의 미세한 좌표 기준점(Datum) 차이
2. 투영법(Projection) 변환 과정에서의 비선형 왜곡
3. 건물 밀집 지역이나 도심지에서의 GPS 기준점 편차

추론 후, 반드시 지정된 JSON 스키마 형식으로 응답해야 합니다.

응답 JSON 스키마 구조:
{
  "lat_offset": float,     // 위도 보정값 (도 단위, ±0.001 이내)
  "lng_offset": float,     // 경도 보정값 (도 단위, ±0.001 이내)
  "confidence": float,     // 보정 신뢰도 (0~1 사이)
  "reasoning": string      // 오차 원인 한국어 분석 (1~2문장으로 간결하게)
}"""

def format_user_prompt(transform_data: Dict[str, Any], current_rmse: float) -> str:
    """
    Format the input data into a prompt for the Gemini model.
    """
    prompt = (
        f"현재 변환 및 오차 데이터 분석 요청:\n"
        f"- Target 랜드마크 (또는 좌표 특성): {transform_data.get('label', '알 수 없음')}\n"
        f"- 현재 좌표: {transform_data.get('lat')}, {transform_data.get('lng')}\n"
        f"- Ground Truth (측정값): {transform_data.get('ground_truth', '알 수 없음')}\n"
        f"- 현재 오차 (RMSE): {current_rmse:.2f}m\n\n"
        f"이 거리를 줄이기 위한 최적의 보정값(lat_offset, lng_offset)을 계산하여 JSON으로 응답해주세요."
    )
    return prompt
