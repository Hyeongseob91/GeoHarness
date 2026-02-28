"""
Gemini Interface implementation.
"""

import json
import logging
from typing import Dict, Any, Tuple, List
import google.generativeai as genai

from .prompt import GEMINI_SYSTEM_PROMPT, format_user_prompt
from .metrics import calculate_rmse, calculate_harness_score

logger = logging.getLogger(__name__)

def execute_gemini_correction_loop(
    model: genai.GenerativeModel,
    input_data: Dict[str, Any],
    ground_truth: Dict[str, float],
    max_iterations: int = 2,
    timeout_s: float = 15.0
) -> Tuple[float, int, List[Dict[str, Any]], str, str]:
    """
    Executes the self-correction Gemini loop based on the PRD specification.
    
    Returns:
        (final_rmse, harness_score, corrections_list, gemini_reasoning, status)
    """
    # Initialize with input lat/lng as floating point
    current_lat = float(input_data["lat"])
    current_lng = float(input_data["lng"])
    
    # Calculate initial RMSE
    current_rmse = calculate_rmse([{"lat": current_lat, "lng": current_lng}], [ground_truth])
    
    corrections = []
    final_reasoning = None
    status = "success"

    for i in range(max_iterations):
        if current_rmse < 1.0:
            logger.info("RMSE < 1.0m reached. Stopping Gemini loop early.")
            break

        # Prepare context payload
        transform_context = {
            "label": input_data.get("label", "Unknown"),
            "lat": current_lat,
            "lng": current_lng,
            "ground_truth": ground_truth
        }
        
        prompt = format_user_prompt(transform_context, current_rmse)
        
        try:
            response = model.generate_content(
                contents=[
                    {"role": "user", "parts": [{"text": GEMINI_SYSTEM_PROMPT}]},
                    {"role": "user", "parts": [{"text": prompt}]}
                ],
                generation_config={"response_mime_type": "application/json"},
                request_options={"timeout": timeout_s}
            )
            
            # The prompt requires strict JSON output. Parse it here.
            correction_payload = json.loads(response.text)
            lat_off = float(correction_payload.get("lat_offset", 0.0))
            lng_off = float(correction_payload.get("lng_offset", 0.0))
            confidence = float(correction_payload.get("confidence", 0.0))
            reasoning = correction_payload.get("reasoning", "")
            
            final_reasoning = reasoning

            # Apply correction
            current_lat += lat_off
            current_lng += lng_off
            
            # Re-calculate RMSE
            current_rmse = calculate_rmse([{"lat": current_lat, "lng": current_lng}], [ground_truth])
            
            corrections.append({
                "iteration": i + 1,
                "lat_offset": lat_off,
                "lng_offset": lng_off,
                "confidence": confidence,
                "rmse_after_m": current_rmse
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON: {e}")
            status = "json_parse_error"
            break
        except Exception as e:
            logger.error(f"Gemini API Error or Timeout: {e}")
            status = "timeout_or_error"
            break

    harness_score = calculate_harness_score(current_rmse)
    
    return current_rmse, harness_score, corrections, final_reasoning, status

