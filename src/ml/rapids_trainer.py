"""
GeoHarness v2.0: RAPIDS cuML Trainer — GPU 가속 오프셋 회귀 모델

환경: Google Colab (T4/A100 GPU)
설치: !pip install cudf-cu12 cuml-cu12 --extra-index-url=https://pypi.nvidia.com

학습 플로우:
    1. ml_dataset.csv 로드 (Google WGS84 ↔ Naver KATECH 쌍)
    2. vworld_anchors.csv 로드 (Ground Truth 기준점)
    3. Feature Engineering: 기준점까지의 거리/방향각 계산
    4. cuML XGBoost로 Δlat, Δlng 학습
    5. decoder.pkl 내보내기 → src/models/에 배치

로컬 CPU 대체 실행:
    GPU 없는 환경에서는 sklearn으로 자동 fallback합니다.
"""

import math
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAPIDSTrainer")

# GPU (cuML) / CPU (sklearn) 자동 감지
try:
    import cudf
    import cuml
    from cuml.ensemble import RandomForestRegressor as RF
    from cuml.metrics import mean_squared_error
    GPU_AVAILABLE = True
    logger.info("✅ NVIDIA RAPIDS (cuML/cuDF) detected — GPU mode")
except ImportError:
    import pandas as cudf  # pandas를 cudf alias로 사용
    from sklearn.ensemble import RandomForestRegressor as RF
    from sklearn.metrics import mean_squared_error
    GPU_AVAILABLE = False
    logger.info("⚠️ RAPIDS not available — falling back to sklearn (CPU)")

try:
    import joblib
except ImportError:
    import pickle as joblib


def haversine_distance(lat1, lng1, lat2, lng2):
    """두 WGS84 좌표 사이의 거리 (미터)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 방위각 (degrees)"""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lng2 - lng1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def load_anchors(anchors_path: str = "data/vworld_anchors.csv"):
    """VWorld 기준점 로드"""
    import csv
    anchors = []
    with open(anchors_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            anchors.append({
                "name": row["anchor_name"],
                "lat": float(row["vw_lat"]),
                "lng": float(row["vw_lng"]),
            })
    logger.info(f"Loaded {len(anchors)} VWorld anchors")
    return anchors


def compute_anchor_features(g_lat, g_lng, anchors):
    """
    가장 가까운 기준점까지의 거리/방향각 계산
    Returns: (nearest_dist, nearest_bearing, anchor_idx)
    """
    min_dist = float("inf")
    min_bearing = 0
    min_idx = 0
    for i, a in enumerate(anchors):
        d = haversine_distance(g_lat, g_lng, a["lat"], a["lng"])
        if d < min_dist:
            min_dist = d
            min_bearing = bearing(g_lat, g_lng, a["lat"], a["lng"])
            min_idx = i
    return min_dist, min_bearing, min_idx


def train_offset_model(
    dataset_path: str = "data/ml_dataset.csv",
    anchors_path: str = "data/vworld_anchors.csv",
    output_path: str = "src/models/decoder.pkl",
    n_estimators: int = 200,
    test_ratio: float = 0.2,
):
    """
    비선형 오프셋 회귀 모델 학습

    Features:
        g_lat, g_lng                — Google WGS84 좌표
        nearest_anchor_dist         — 가장 가까운 VWorld 기준점까지 거리 (m)
        nearest_anchor_bearing      — 기준점까지 방위각 (degrees)

    Targets:
        delta_x                     — n_mapx - g_lng (경도 오프셋)
        delta_y                     — n_mapy - g_lat (위도 오프셋)
    """
    logger.info("=" * 60)
    logger.info("GeoHarness RAPIDS Trainer v2.0")
    logger.info(f"GPU Mode: {GPU_AVAILABLE}")
    logger.info("=" * 60)

    # === 1. 데이터 로드 ===
    if not Path(dataset_path).exists():
        logger.error(f"Dataset not found: {dataset_path}")
        logger.info("먼저 naver_collector.py를 실행하여 ml_dataset.csv를 생성하세요.")
        return None

    df = cudf.read_csv(dataset_path)
    logger.info(f"[1/5] Dataset loaded: {len(df)} rows")
    logger.info(f"  Columns: {list(df.columns)}")

    # === 2. 기준점 로드 & Feature Engineering ===
    anchors = load_anchors(anchors_path) if Path(anchors_path).exists() else []

    # delta 계산 — Naver KATECH 좌표는 mapx/mapy (큰 정수)
    # Google 좌표는 WGS84 lat/lng (소수)
    # 오프셋은 같은 좌표계 내에서 비교해야 의미 있음
    df["delta_x"] = df["n_mapx"].astype(float) - df["g_lng"]
    df["delta_y"] = df["n_mapy"].astype(float) - df["g_lat"]

    # Anchor 기반 features
    if anchors:
        anchor_dists = []
        anchor_bearings = []
        if GPU_AVAILABLE:
            df_pd = df.to_pandas()
        else:
            df_pd = df

        for _, row in df_pd.iterrows():
            dist, bear, _ = compute_anchor_features(
                float(row["g_lat"]), float(row["g_lng"]), anchors
            )
            anchor_dists.append(dist)
            anchor_bearings.append(bear)

        if GPU_AVAILABLE:
            import cudf as real_cudf
            df["anchor_dist"] = real_cudf.Series(anchor_dists)
            df["anchor_bearing"] = real_cudf.Series(anchor_bearings)
        else:
            df["anchor_dist"] = anchor_dists
            df["anchor_bearing"] = anchor_bearings

        feature_cols = ["g_lat", "g_lng", "anchor_dist", "anchor_bearing"]
    else:
        feature_cols = ["g_lat", "g_lng"]
        logger.warning("  No anchors found — using lat/lng features only")

    logger.info(f"[2/5] Features: {feature_cols}")

    # === 3. Train/Test Split ===
    n_test = max(1, int(len(df) * test_ratio))
    n_train = len(df) - n_test

    X = df[feature_cols]
    y = df[["delta_x", "delta_y"]]

    X_train, X_test = X.iloc[:n_train], X.iloc[n_train:]
    y_train, y_test = y.iloc[:n_train], y.iloc[n_train:]

    logger.info(f"[3/5] Split: {n_train} train / {n_test} test")

    # === 4. 모델 학습 ===
    # delta_x, delta_y를 각각 독립적으로 학습
    model_x = RF(n_estimators=n_estimators, random_state=42)
    model_y = RF(n_estimators=n_estimators, random_state=42)

    logger.info(f"[4/5] Training RandomForest (n_estimators={n_estimators})...")
    model_x.fit(X_train, y_train["delta_x"])
    model_y.fit(X_train, y_train["delta_y"])

    # === 5. 평가 ===
    pred_x = model_x.predict(X_test)
    pred_y = model_y.predict(X_test)

    if GPU_AVAILABLE:
        mse_x = mean_squared_error(y_test["delta_x"], pred_x).item()
        mse_y = mean_squared_error(y_test["delta_y"], pred_y).item()
    else:
        mse_x = mean_squared_error(y_test["delta_x"], pred_x)
        mse_y = mean_squared_error(y_test["delta_y"], pred_y)

    rmse_x = mse_x ** 0.5
    rmse_y = mse_y ** 0.5

    logger.info(f"[5/5] Evaluation:")
    logger.info(f"  RMSE (delta_x): {rmse_x:.6f}")
    logger.info(f"  RMSE (delta_y): {rmse_y:.6f}")

    # === 6. 모델 저장 ===
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    model_bundle = {
        "model_x": model_x,
        "model_y": model_y,
        "feature_cols": feature_cols,
        "anchors": anchors,
        "rmse_x": rmse_x,
        "rmse_y": rmse_y,
        "gpu_trained": GPU_AVAILABLE,
        "n_samples": len(df),
    }
    joblib.dump(model_bundle, output_path)
    logger.info(f"✅ Model saved to {output_path}")
    logger.info(f"   Bundle keys: {list(model_bundle.keys())}")

    return model_bundle


if __name__ == "__main__":
    train_offset_model()
