"""
Prediction & Inference Module for ADES BIDAI
Provides ultra-fast local inference (< 10ms) using the serialized model artifact.
Maps continuous predicted dengue case counts into actionable public health risk tiers
(Low, Medium, High, Critical) using trained dynamic quantiles, and extracts primary drivers.
"""

import os
import sys
import joblib
import pandas as pd
import numpy as np

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_LOADED_ARTIFACT = None


def load_model(model_path: str = "models/dengue_outbreak_model.joblib"):
    """
    Loads and caches the trained model artifact from disk.
    Ensures zero redundant disk reads and zero API costs.
    """
    global _LOADED_ARTIFACT
    if _LOADED_ARTIFACT is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model artifact not found at {model_path}. Please run train_model.py first."
            )
        _LOADED_ARTIFACT = joblib.load(model_path)
        print(f"[prediction] Loaded model: {_LOADED_ARTIFACT['model_name']} from {model_path}")
    return _LOADED_ARTIFACT


def map_quantile_tier(val: float, thresholds: dict) -> str:
    """Maps a predicted continuous case count to risk tiers using dynamic quantiles."""
    if thresholds is None:
        if val < 2.0:
            return "Low"
        elif val < 6.0:
            return "Medium"
        elif val < 15.0:
            return "High"
        else:
            return "Critical"
            
    if val < thresholds.get("q_low", 1.5):
        return "Low"
    elif val < thresholds.get("q_med", 4.0):
        return "Medium"
    elif val < thresholds.get("q_high", 10.0):
        return "High"
    else:
        return "Critical"


def predict_dataframe(df: pd.DataFrame, model_path: str = "models/dengue_outbreak_model.joblib") -> pd.DataFrame:
    """
    Generates dynamic predictions and risk tiers for a featured DataFrame.
    Returns the DataFrame augmented with:
    - predicted_cases (float)
    - predicted_risk_tier (Low / Medium / High / Critical)
    """
    artifact = load_model(model_path)
    model = artifact["model"]
    feature_cols = artifact["feature_cols"]
    thresholds = artifact.get("quantile_thresholds")
    
    missing_cols = [c for c in feature_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Input DataFrame is missing required features: {missing_cols}")
        
    X = df[feature_cols]
    raw_preds = model.predict(X)
    clipped_preds = np.clip(raw_preds, 0, None)
    
    output_df = df.copy()
    output_df["predicted_cases"] = np.round(clipped_preds, 2)
    output_df["predicted_risk_tier"] = [map_quantile_tier(p, thresholds) for p in clipped_preds]
    
    return output_df


def predict_single_ward(
    ward_features: dict,
    model_path: str = "models/dengue_outbreak_model.joblib"
) -> dict:
    """
    Predicts dengue outbreak risk for a single ward scenario.
    Returns:
    - predicted_cases
    - risk_tier
    - top_drivers: Key factors influencing the risk score
    """
    artifact = load_model(model_path)
    feature_cols = artifact["feature_cols"]
    thresholds = artifact.get("quantile_thresholds")
    
    input_df = pd.DataFrame([ward_features])
    
    # Fill any missing features with zero or median defaults
    for col in feature_cols:
        if col not in input_df.columns:
            input_df[col] = 0.0
            
    pred_df = predict_dataframe(input_df, model_path)
    predicted_cases = float(pred_df["predicted_cases"].iloc[0])
    risk_tier = str(pred_df["predicted_risk_tier"].iloc[0])
    
    # Analyze key drivers
    drivers = []
    if ward_features.get("rainfall_lag_2w", 0) > 35:
        drivers.append("Heavy rainfall 2 weeks ago (triggering rapid Aedes larval emergence)")
    if ward_features.get("rainfall_lag_3w", 0) > 35:
        drivers.append("Sustained rainfall 3 weeks ago (peak adult mosquito transmission window)")
    if ward_features.get("rainfall_roll_sum_4w", 0) > 120:
        drivers.append("High 4-week cumulative rainfall (persistent urban breeding pool saturation)")
    if ward_features.get("water_logging_risk_index", 0) > 0.6:
        drivers.append("Severe drainage bottlenecks (water logging traps stagnant pools)")
    if ward_features.get("sanitation_score", 1.0) < 0.45:
        drivers.append("Low sanitation score (solid waste containers multiply breeding sites)")
    if ward_features.get("relative_humidity_pct", 0) > 75:
        drivers.append("High relative humidity (>75%) extending adult mosquito lifespan")
    if ward_features.get("population_density_sqkm", 0) > 50000:
        drivers.append("Dense population crowding (facilitates rapid vector-to-human transmission)")
        
    if not drivers:
        drivers.append("Baseline environmental conditions within normal seasonal limits")
        
    return {
        "predicted_cases": round(predicted_cases, 1),
        "predicted_risk_tier": risk_tier,
        "primary_drivers": drivers
    }


if __name__ == "__main__":
    test_artifact = load_model()
    print("[prediction] Verified model loading. Model Name:", test_artifact["model_name"])
    print("[prediction] Quantile Thresholds:", test_artifact["quantile_thresholds"])
