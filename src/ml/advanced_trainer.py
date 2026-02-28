"""
GeoHarness v4.0: Advanced Scikit-Learn Spatial Offset Trainer (CPU Optimized)

목적:
수집된 약 4,000개의 (Google_WGS84, Naver_KATECH) 좌표 쌍을 바탕으로
보안 오프셋(Encryption Algorithm)의 패턴을 리버스 엔지니어링하는 초정밀 앙상블 회귀 모델을 학습합니다.

특징:
1. Feature Engineering: 
   - H3 / Geohash 대신 가장 가까운 3개의 가상 앵커 포인트와의 상대적 거리/방위각을 모두 Feature로 계산합니다. (공간 삼각 측량망 형성)
2. Ensemble Architecture:
   - 메모리/속도 최적화를 위해 Random Forest와 HistGradientBoosting을 결합하여 Bias-Variance 트레이드오프를 맞춥니다.
3. K-Fold Cross Validation:
   - 과적합을 방지하고 일반화된 오차를 보고하기 위해 5-Fold 검증 체계를 갖추었습니다.
"""

import math
import logging
import os
import pickle
from pathlib import Path

import pandas as pd
import numpy as np

try:
    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor, VotingRegressor
    from sklearn.model_selection import KFold, train_test_split
    from sklearn.metrics import mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("WARNING: scikit-learn library not found. Run: pip install scikit-learn pandas numpy")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AdvancedTrainer")

def haversine_distance(lat1, lng1, lat2, lng2):
    """두 WGS84 좌표 사이의 표면 거리 (미터)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def bearing(lat1, lng1, lat2, lng2):
    """두 WGS84 좌표 사이의 초기 방위각 (도)"""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lng2 - lng1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def load_vworld_anchors(anchors_path: str):
    import csv
    anchors = []
    if not os.path.exists(anchors_path):
        return anchors
    with open(anchors_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            anchors.append({
                "lat": float(row["vw_lat"]),
                "lng": float(row["vw_lng"]),
            })
    return anchors

def generate_triangulation_features(df: pd.DataFrame, anchors: list):
    """
    각 위치에서 가장 가까운 3개의 앵커와의 거리, 방위각을 Feature로 추출
    """
    if not anchors or len(anchors) < 3:
        logger.warning("Not enough anchors for 3-point triangulation. Only using lat/lng features.")
        return df

    # Vectorized Haversine/Bearing can be faster, but for 4000 rows, iteration is fine.
    dist_1, bear_1 = [], []
    dist_2, bear_2 = [], []
    dist_3, bear_3 = [], []

    for _, row in df.iterrows():
        lat, lng = row['g_lat'], row['g_lng']
        
        # Calculate all distances and bearings to all anchors
        relations = []
        for anchor in anchors:
            d = haversine_distance(lat, lng, anchor['lat'], anchor['lng'])
            b = bearing(lat, lng, anchor['lat'], anchor['lng'])
            relations.append((d, b))
        
        # Sort by distance
        relations.sort(key=lambda x: x[0])
        
        # Take Top 3 closest anchors
        dist_1.append(relations[0][0]); bear_1.append(relations[0][1])
        dist_2.append(relations[1][0]); bear_2.append(relations[1][1])
        dist_3.append(relations[2][0]); bear_3.append(relations[2][1])
        
    df['anchor1_dist'] = dist_1; df['anchor1_bear'] = bear_1
    df['anchor2_dist'] = dist_2; df['anchor2_bear'] = bear_2
    df['anchor3_dist'] = dist_3; df['anchor3_bear'] = bear_3
    
    return df

def build_ensemble_model():
    """
    Random Forest: 노이즈 내성, 강건성
    HistGradientBoosting: CPU 멀티스레드 기반 빠르고 정밀한 부스팅, 1만개 이하 데이터에 최적화
    """
    rf = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
    # HistGradientBoostingRegressor is specifically designed for datasets with >1000 samples
    hgb = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_depth=8, random_state=42)
    
    ensemble = VotingRegressor(estimators=[('rf', rf), ('hgb', hgb)])
    return ensemble

def train_advanced_model(
    dataset_path: str = "data/ml_dataset.csv",
    anchors_path: str = "data/vworld_anchors.csv",
    output_model_path: str = "src/models/decoder.pkl"
):
    logger.info("=" * 60)
    logger.info("GeoHarness Advanced CPU Spatial Offset Trainer")
    logger.info("=" * 60)

    if not SKLEARN_AVAILABLE:
        logger.error("scikit-learn not found. Training aborted.")
        return

    if not Path(dataset_path).exists():
        logger.error(f"Dataset path not found: {dataset_path}")
        return

    logger.info(f"[1/5] Loading data from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    logger.info(f"Loaded {len(df)} samples.")

    # Target: The precise coordinate diff between KATECH and Input WGS84
    # NOTE: Naver Search API returns `mapx`, `mapy` as WGS84 coordinates multiplied by 10^7!
    df["n_wgs_lng"] = df["n_mapx"] / 10000000.0
    df["n_wgs_lat"] = df["n_mapy"] / 10000000.0
    
    # "Degree 단위의 실제 오차(Delta)"를 모델이 학습
    df["delta_x"] = df["n_wgs_lng"] - df["g_lng"]
    df["delta_y"] = df["n_wgs_lat"] - df["g_lat"]

    logger.info("[2/5] Engineering Geometric Features...")
    anchors = load_vworld_anchors(anchors_path)
    df = generate_triangulation_features(df, anchors)
    
    # Select features dynamically based on what was generated
    feature_cols = ['g_lat', 'g_lng']
    if 'anchor1_dist' in df.columns:
        feature_cols.extend(['anchor1_dist', 'anchor1_bear', 'anchor2_dist', 'anchor2_bear', 'anchor3_dist', 'anchor3_bear'])

    X = df[feature_cols].values
    y_x = df['delta_x'].values
    y_y = df['delta_y'].values

    logger.info(f"Target dimension: X={X.shape}, using {len(feature_cols)} features: {feature_cols}")

    # === K-Fold Cross Validation ===
    logger.info(f"[3/5] Performing 5-Fold Cross Validation for generalization...")
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    cv_rmse_x, cv_rmse_y = [], []
    
    # Quick CV loop to assess robustness
    for train_index, test_index in kf.split(X):
        X_tr, X_te = X[train_index], X[test_index]
        yx_tr, yx_te = y_x[train_index], y_x[test_index]
        yy_tr, yy_te = y_y[train_index], y_y[test_index]

        temp_mx = build_ensemble_model().fit(X_tr, yx_tr)
        temp_my = build_ensemble_model().fit(X_tr, yy_tr)
        
        rx = np.sqrt(mean_squared_error(yx_te, temp_mx.predict(X_te)))
        ry = np.sqrt(mean_squared_error(yy_te, temp_my.predict(X_te)))
        
        cv_rmse_x.append(rx)
        cv_rmse_y.append(ry)

    logger.info(f"CV RMSE X: {np.mean(cv_rmse_x):.4f} ± {np.std(cv_rmse_x):.4f}")
    logger.info(f"CV RMSE Y: {np.mean(cv_rmse_y):.4f} ± {np.std(cv_rmse_y):.4f}")

    # === Final Full Model Training ===
    logger.info("[4/5] Training Final Ensemble Models on 100% of data...")
    final_model_x = build_ensemble_model()
    final_model_x.fit(X, y_x)

    final_model_y = build_ensemble_model()
    final_model_y.fit(X, y_y)

    # === Save Bundle ===
    logger.info(f"[5/5] Exporting inference decoding bundle...")
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    
    bundle = {
        "model_x": final_model_x,
        "model_y": final_model_y,
        "feature_cols": feature_cols,
        "anchors": anchors,
        "n_samples": len(df),
        "rmse_x": float(np.mean(cv_rmse_x)),
        "rmse_y": float(np.mean(cv_rmse_y)),
        "gpu_trained": False,
        "method": "Ensemble(RF+HistGB)"
    }
    
    with open(output_model_path, 'wb') as f:
        pickle.dump(bundle, f)

    logger.info(f"✅ Advanced Decoder successfully exported to {output_model_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    csv_path = os.path.join(project_root, "data", "ml_dataset.csv")
    anchors_path = os.path.join(project_root, "data", "vworld_anchors.csv")
    model_path = os.path.join(project_root, "src", "models", "decoder.pkl")
    
    train_advanced_model(csv_path, anchors_path, model_path)
