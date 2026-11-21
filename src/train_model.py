"""
Model Training Module for ADES BIDAI
Step 4: Machine Learning Model Training & Chronological Validation
- Strictly chronological split (2016-2023 Train, 2024-2025 Test)
- Target: 2-4 week lagged dengue outbreak prediction
- Models compared: HistGradientBoosting, RandomForest, and Ridge baseline
- Metrics evaluated: MAE, RMSE, R2, and Risk Tier Accuracy
- Quantile-based dynamic risk tier mapping: Low, Medium, High, Critical
- Model serialization via joblib into models/
"""

import os
import sys
import json
import joblib
import pandas as pd
import numpy as np

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_processing import get_preprocessed_data
from src.feature_engineering import engineer_features
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score


FEATURE_COLS = [
    # Static ward features (density, drainage bottleneck, sanitation)
    "population_density_sqkm",
    "water_logging_risk_index",
    "sanitation_score",
    "composite_vulnerability_index",
    "density_exposure_factor",
    "vector_climate_suitability",
    "temp_range_c",
    
    # Current weather
    "avg_temp_c",
    "rainfall_mm",
    "relative_humidity_pct",
    
    # Multi-week weather lags (2-4 week vector breeding & incubation clock)
    "rainfall_lag_1w",
    "rainfall_lag_2w",
    "rainfall_lag_3w",
    "rainfall_lag_4w",
    "avg_temp_lag_1w",
    "avg_temp_lag_2w",
    "avg_temp_lag_3w",
    "humidity_lag_1w",
    "humidity_lag_2w",
    "humidity_lag_3w",
    
    # Multi-week rolling statistics
    "rainfall_roll_mean_2w",
    "rainfall_roll_sum_2w",
    "rainfall_roll_mean_4w",
    "rainfall_roll_sum_4w",
    "rainfall_roll_sum_3w",
    "avg_temp_roll_mean_3w",
    "humidity_roll_mean_3w",
    
    # Vulnerability interactions
    "rain_lag2_x_waterlog",
    "rain_lag3_x_waterlog",
    "rain_lag2_x_unsanitary",
    "rain_lag3_x_unsanitary",
    
    # Seasonal and cyclical calendar
    "month",
    "week_of_year",
    "is_monsoon",
    "sin_week",
    "cos_week",
    "sin_month",
    "cos_month"
]


def compute_quantile_tiers(y_train: pd.Series):
    """
    Computes quantile thresholds from the training target distribution:
    - Low: 0 up to 50th percentile (zero or sporadic cases)
    - Medium: 50th to 75th percentile
    - High: 75th to 90th percentile
    - Critical: Above 90th percentile (outbreak epidemic surge)
    """
    q50 = float(y_train.quantile(0.50))  # typically ~0-1
    q75 = float(y_train.quantile(0.75))  # typically ~4
    q90 = float(y_train.quantile(0.90))  # typically ~9
    
    # Ensure distinct strictly increasing thresholds
    if q50 < 1.0:
        q50 = 1.5
    if q75 <= q50:
        q75 = q50 + 3.0
    if q90 <= q75:
        q90 = q75 + 5.0
        
    thresholds = {
        "q_low": round(q50, 1),      # < q_low -> Low
        "q_med": round(q75, 1),      # q_low to q_med -> Medium
        "q_high": round(q90, 1)      # q_med to q_high -> High, > q_high -> Critical
    }
    print(f"[train_model] Dynamic Quantile Thresholds: Low < {thresholds['q_low']} <= Medium < {thresholds['q_med']} <= High < {thresholds['q_high']} <= Critical")
    return thresholds


def map_quantile_tier(val: float, thresholds: dict) -> str:
    """Maps a predicted continuous case count to risk tiers using dynamic quantiles."""
    if val < thresholds["q_low"]:
        return "Low"
    elif val < thresholds["q_med"]:
        return "Medium"
    elif val < thresholds["q_high"]:
        return "High"
    else:
        return "Critical"


def chronological_split(df: pd.DataFrame, split_date: str = "2024-01-01"):
    """
    Chronological time-series split (strictly non-random):
    - Training Set: Historical records prior to split_date (2016-02-01 to 2023-12-25)
    - Holdout Test Set: Future records after split_date (2024-01-01 to 2025-12-29)
    """
    train_df = df[df["date"] < pd.to_datetime(split_date)].copy()
    test_df = df[df["date"] >= pd.to_datetime(split_date)].copy()
    
    print(f"[train_model] Chronological Train-Test Split at {split_date}:")
    print(f"  Train: {train_df['date'].min().date()} to {train_df['date'].max().date()} ({len(train_df)} records)")
    print(f"  Test : {test_df['date'].min().date()} to {test_df['date'].max().date()} ({len(test_df)} records)")
    
    return train_df, test_df


def train_models(df: pd.DataFrame, output_dir: str = "models"):
    """
    Trains candidate ML models on historical training data,
    evaluates MAE/RMSE/R2 and quantile tier accuracy on unseen holdout test set,
    and serializes the winning model via joblib.dump().
    """
    train_df, test_df = chronological_split(df, split_date="2024-01-01")
    
    X_train = train_df[FEATURE_COLS]
    y_train = train_df["dengue_cases"]
    
    X_test = test_df[FEATURE_COLS]
    y_test = test_df["dengue_cases"]
    
    # 1. Compute dynamic quantile thresholds from training data
    quantile_thresholds = compute_quantile_tiers(y_train)
    y_test_true_tiers = [map_quantile_tier(y, quantile_thresholds) for y in y_test]
    
    # 2. Candidate Models (ML + Simple Linear Baseline)
    models = {
        "Ridge_Baseline": Ridge(alpha=1.0),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=180,
            learning_rate=0.08,
            max_depth=6,
            random_state=42
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=60,
            max_depth=10,
            min_samples_split=4,
            n_jobs=1,
            random_state=42
        )
    }
    
    results = {}
    best_model_name = None
    best_mae = float("inf")
    fitted_models = {}
    
    print("\n[train_model] Evaluating candidate models on Out-of-Time Test Set (2024-2025)...")
    for name, model in models.items():
        print(f"  Training {name}...")
        model.fit(X_train, y_train)
        fitted_models[name] = model
        
        preds = model.predict(X_test)
        preds = np.clip(preds, 0, None)  # Physical constraint: dengue cases >= 0
        
        mae = float(mean_absolute_error(y_test, preds))
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        r2 = float(r2_score(y_test, preds))
        
        # Risk tier accuracy using dynamic quantiles
        pred_tiers = [map_quantile_tier(p, quantile_thresholds) for p in preds]
        tier_acc = float(accuracy_score(y_test_true_tiers, pred_tiers))
        
        results[name] = {
            "MAE": round(mae, 3),
            "RMSE": round(rmse, 3),
            "R2": round(r2, 3),
            "Tier_Accuracy_Pct": round(tier_acc * 100, 2)
        }
        print(f"  -> {name} | MAE: {mae:.3f} | RMSE: {rmse:.3f} | R²: {r2:.3f} | Tier Accuracy: {tier_acc * 100:.2f}%")
        
        if mae < best_mae:
            best_mae = mae
            best_model_name = name
            
    print(f"\n[train_model] Winning Model Selected: {best_model_name} (MAE: {best_mae:.3f})")
    winning_model = fitted_models[best_model_name]
    
    # 3. Serialize Model Artifact via joblib.dump()
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "dengue_outbreak_model.joblib")
    
    artifact = {
        "model": winning_model,
        "model_name": best_model_name,
        "feature_cols": FEATURE_COLS,
        "quantile_thresholds": quantile_thresholds,
        "metrics": results,
        "split_date": "2024-01-01"
    }
    joblib.dump(artifact, model_path)
    print(f"[train_model] Model successfully serialized to: {model_path}")
    
    # 4. Save JSON metrics summary
    metrics_path = os.path.join(output_dir, "metrics_summary.json")
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"[train_model] Metrics summary saved to: {metrics_path}")
    
    return artifact, results


if __name__ == "__main__":
    raw_df = get_preprocessed_data()
    featured_df = engineer_features(raw_df)
    train_models(featured_df)
