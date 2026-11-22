"""
ADES BIDAI - FastAPI Backend
Dengue Outbreak Prediction & Early Warning System

Endpoints:
  GET /api/health
  GET /api/summary
  GET /api/wards
  GET /api/ward/{ward_id}
  GET /api/predict
  GET /api/weather/{ward_id}
  GET /api/metrics
  GET /api/historical
  GET /api/comparison
  GET /api/environmental
"""

import os
import sys
import json
import math
from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Path setup – make src/ and utils/ importable
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from src.data_processing import get_preprocessed_data
from src.feature_engineering import engineer_features
from src.prediction import predict_dataframe, map_quantile_tier
from utils.ward_coordinates import ALL_WARD_COORDS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ADES BIDAI – Dengue Outbreak API",
    description="Real-time dengue outbreak prediction for urban wards.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global state (loaded once at startup)
# ---------------------------------------------------------------------------
_FEATURED_DF: pd.DataFrame = None          # full featured dataset
_PREDICTED_DF: pd.DataFrame = None         # full dataset + predicted_cases / predicted_risk_tier
_LATEST_PRED_DF: pd.DataFrame = None       # latest week predictions per ward
_ARTIFACT: dict = None                     # {model, feature_cols, model_name, quantile_thresholds}
_METRICS: dict = None                      # contents of metrics_summary.json
_MODEL_MAE: float = 1.0                    # MAE of the loaded model (for CI)


def _safe_float(val, decimals: int = 2) -> Optional[float]:
    """Round a float, return None if NaN/inf."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


def _build_risk_drivers(row: pd.Series) -> List[str]:
    """Return a human-readable list of risk drivers for a ward row."""
    drivers = []
    if row.get("rainfall_lag_2w", 0) > 35:
        drivers.append("Heavy rainfall 2 weeks ago (Aedes larval emergence peak)")
    if row.get("rainfall_lag_3w", 0) > 35:
        drivers.append("Sustained rainfall 3 weeks ago (peak adult mosquito window)")
    if row.get("rainfall_roll_sum_4w", 0) > 120:
        drivers.append("High 4-week cumulative rainfall (urban breeding pool saturation)")
    if row.get("water_logging_risk_index", 0) > 0.6:
        drivers.append("Severe drainage bottlenecks (stagnant water pooling)")
    if row.get("sanitation_score", 1.0) < 0.45:
        drivers.append("Low sanitation score (proliferation of breeding containers)")
    if row.get("relative_humidity_pct", 0) > 75:
        drivers.append("High relative humidity (>75%) extending mosquito lifespan")
    if row.get("population_density_sqkm", 0) > 50000:
        drivers.append("Dense population crowding (rapid vector-to-human transmission)")
    if row.get("vector_climate_suitability", 0) > 0.7:
        drivers.append("High vector climate suitability (optimal temp/humidity for Aedes)")
    if row.get("composite_vulnerability_index", 0) > 0.6:
        drivers.append("Elevated composite vulnerability index (combined structural risk)")
    if not drivers:
        drivers.append("Baseline environmental conditions within normal seasonal limits")
    return drivers


# ---------------------------------------------------------------------------
# Startup event – load data and model ONCE
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_load():
    global _FEATURED_DF, _PREDICTED_DF, _LATEST_PRED_DF, _ARTIFACT, _METRICS, _MODEL_MAE

    print("[api] Loading and processing dataset...")
    csv_path = os.path.join(ROOT, "data", "google_sheet_dengue_dataset.csv")
    raw_df = get_preprocessed_data(filepath=csv_path)
    _FEATURED_DF = engineer_features(raw_df, drop_burnin=True)

    print("[api] Running model predictions on full dataset...")
    model_path = os.path.join(ROOT, "models", "dengue_outbreak_model.joblib")
    _ARTIFACT = joblib.load(model_path)
    _PREDICTED_DF = predict_dataframe(_FEATURED_DF, model_path=model_path)

    # Latest week prediction per ward (last row per ward in time order)
    _LATEST_PRED_DF = (
        _PREDICTED_DF
        .sort_values(["ward_id", "date"])
        .groupby("ward_id", as_index=False)
        .last()
    )

    # Load metrics
    metrics_path = os.path.join(ROOT, "models", "metrics_summary.json")
    with open(metrics_path, "r") as f:
        _METRICS = json.load(f)

    # Pick MAE from the model that was loaded
    model_name = _ARTIFACT.get("model_name", "")
    if model_name in _METRICS:
        _MODEL_MAE = _METRICS[model_name].get("MAE", 1.0)
    else:
        # fallback: best MAE across all models
        _MODEL_MAE = min(v.get("MAE", 999) for v in _METRICS.values())

    print(f"[api] Startup complete. Model: {model_name}, MAE: {_MODEL_MAE}")
    print(f"[api] Featured rows: {len(_FEATURED_DF)}, Wards: {_LATEST_PRED_DF['ward_id'].nunique()}")


# ---------------------------------------------------------------------------
# 1. GET /api/health
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


# ---------------------------------------------------------------------------
# 2. GET /api/summary
# ---------------------------------------------------------------------------
@app.get("/api/summary")
def summary():
    if _LATEST_PRED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    total_cases = int(_FEATURED_DF["dengue_cases"].sum())
    total_wards = int(_LATEST_PRED_DF["ward_id"].nunique())
    latest_date = _FEATURED_DF["date"].max().date().isoformat()
    avg_temp = _safe_float(_FEATURED_DF["avg_temp_c"].mean())
    total_rainfall = _safe_float(_FEATURED_DF["rainfall_mm"].mean())
    avg_humidity = _safe_float(_FEATURED_DF["relative_humidity_pct"].mean())

    high_risk_count = int((_LATEST_PRED_DF["predicted_risk_tier"] == "High").sum())
    critical_count = int((_LATEST_PRED_DF["predicted_risk_tier"] == "Critical").sum())

    cities = sorted(_FEATURED_DF["city"].dropna().unique().tolist()) if "city" in _FEATURED_DF.columns else []

    return {
        "total_cases": total_cases,
        "total_wards": total_wards,
        "latest_date": latest_date,
        "avg_temp": avg_temp,
        "total_rainfall": total_rainfall,
        "avg_humidity": avg_humidity,
        "high_risk_count": high_risk_count,
        "critical_count": critical_count,
        "cities": cities,
    }


# ---------------------------------------------------------------------------
# 3. GET /api/wards
# ---------------------------------------------------------------------------
@app.get("/api/wards")
def wards():
    if _LATEST_PRED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    result = []
    for _, row in _LATEST_PRED_DF.iterrows():
        wid = str(row["ward_id"])
        coords = ALL_WARD_COORDS.get(wid, (None, None, wid))
        lat, lon, locality = coords[0], coords[1], coords[2] if len(coords) > 2 else wid
        city = str(row.get("city", "")) if "city" in row else ""
        result.append({
            "ward_id": wid,
            "predicted_cases": _safe_float(row.get("predicted_cases", 0)),
            "risk_tier": str(row.get("predicted_risk_tier", "Low")),
            "lat": _safe_float(lat, 6),
            "lon": _safe_float(lon, 6),
            "city": city,
            "locality": str(locality),
        })
    return result


# ---------------------------------------------------------------------------
# 4. GET /api/ward/{ward_id}
# ---------------------------------------------------------------------------
@app.get("/api/ward/{ward_id}")
def ward_detail(ward_id: str):
    if _PREDICTED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    ward_df = _PREDICTED_DF[_PREDICTED_DF["ward_id"] == ward_id].sort_values("date")
    if ward_df.empty:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")

    coords = ALL_WARD_COORDS.get(ward_id, (None, None, ward_id))
    lat, lon = _safe_float(coords[0], 6), _safe_float(coords[1], 6)
    locality = coords[2] if len(coords) > 2 else ward_id

    latest_row = ward_df.iloc[-1]
    city = str(latest_row.get("city", "")) if "city" in latest_row else ""
    current_risk_tier = str(latest_row.get("predicted_risk_tier", "Low"))

    # 2-week prediction: last prediction
    predicted_2w = _safe_float(latest_row.get("predicted_cases", 0.0))

    # 4-week prediction: average of last 4 predicted values per ward
    last4 = ward_df.tail(4)["predicted_cases"]
    predicted_4w = _safe_float(last4.mean())

    # History: last 12 weeks
    history_df = ward_df.tail(12)
    history = []
    for _, hrow in history_df.iterrows():
        history.append({
            "date": hrow["date"].date().isoformat() if hasattr(hrow["date"], "date") else str(hrow["date"]),
            "cases": int(hrow.get("dengue_cases", 0)),
            "predicted": _safe_float(hrow.get("predicted_cases", 0)),
        })

    # Weather summary (from latest row)
    weather_summary = {
        "avg_temp": _safe_float(latest_row.get("avg_temp_c")),
        "rainfall": _safe_float(latest_row.get("rainfall_mm")),
        "humidity": _safe_float(latest_row.get("relative_humidity_pct")),
        "waterlog": _safe_float(latest_row.get("water_logging_risk_index")),
        "sanitation": _safe_float(latest_row.get("sanitation_score")),
        "density": _safe_float(latest_row.get("population_density_sqkm")),
    }

    # Risk drivers
    risk_drivers = _build_risk_drivers(latest_row)

    # Confidence intervals (predicted ± 1.5 × MAE)
    half_width_2w = round(1.5 * _MODEL_MAE, 2)
    pred_2w_val = predicted_2w or 0.0
    pred_4w_val = predicted_4w or 0.0

    ci_2w = {
        "lower": _safe_float(max(0.0, pred_2w_val - half_width_2w)),
        "upper": _safe_float(pred_2w_val + half_width_2w),
    }
    half_width_4w = round(1.5 * _MODEL_MAE * math.sqrt(2), 2)  # slightly wider for 4w
    ci_4w = {
        "lower": _safe_float(max(0.0, pred_4w_val - half_width_4w)),
        "upper": _safe_float(pred_4w_val + half_width_4w),
    }

    return {
        "ward_id": ward_id,
        "city": city,
        "lat": lat,
        "lon": lon,
        "locality": str(locality),
        "current_risk_tier": current_risk_tier,
        "predicted_2w_cases": predicted_2w,
        "predicted_4w_cases": predicted_4w,
        "history": history,
        "weather_summary": weather_summary,
        "risk_drivers": risk_drivers,
        "confidence_interval_2w": ci_2w,
        "confidence_interval_4w": ci_4w,
    }


# ---------------------------------------------------------------------------
# 5. GET /api/predict
# ---------------------------------------------------------------------------
@app.get("/api/predict")
def predict(
    ward_id: str = Query(..., description="Ward identifier"),
    horizon: int = Query(2, ge=1, le=12, description="Forecast horizon in weeks"),
):
    if _PREDICTED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    ward_df = _PREDICTED_DF[_PREDICTED_DF["ward_id"] == ward_id].sort_values("date")
    if ward_df.empty:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")

    latest_row = ward_df.iloc[-1]

    if horizon <= 2:
        predicted_cases = float(latest_row.get("predicted_cases", 0.0))
    else:
        # For longer horizons use average of last min(horizon, all) predictions with mild trend factor
        look_back = min(horizon, len(ward_df))
        predicted_cases = float(ward_df.tail(look_back)["predicted_cases"].mean())

    predicted_cases = max(0.0, predicted_cases)

    thresholds = _ARTIFACT.get("quantile_thresholds")
    risk_tier = map_quantile_tier(predicted_cases, thresholds)

    half_width = round(1.5 * _MODEL_MAE * math.sqrt(max(1, horizon / 2)), 2)
    confidence_lower = _safe_float(max(0.0, predicted_cases - half_width))
    confidence_upper = _safe_float(predicted_cases + half_width)

    primary_drivers = _build_risk_drivers(latest_row)

    return {
        "ward_id": ward_id,
        "horizon_weeks": horizon,
        "predicted_cases": _safe_float(predicted_cases),
        "risk_tier": risk_tier,
        "confidence_lower": confidence_lower,
        "confidence_upper": confidence_upper,
        "primary_drivers": primary_drivers,
    }


# ---------------------------------------------------------------------------
# 6. GET /api/weather/{ward_id}
# ---------------------------------------------------------------------------
@app.get("/api/weather/{ward_id}")
def weather(ward_id: str):
    if _FEATURED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    ward_df = _FEATURED_DF[_FEATURED_DF["ward_id"] == ward_id].sort_values("date")
    if ward_df.empty:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")

    last4 = ward_df.tail(4).reset_index(drop=True)
    weeks = []
    for i, (_, row) in enumerate(last4.iterrows()):
        date_val = row["date"].date().isoformat() if hasattr(row["date"], "date") else str(row["date"])
        weeks.append({
            "week_label": f"Week -{len(last4) - i}",
            "date": date_val,
            "avg_temp": _safe_float(row.get("avg_temp_c")),
            "rainfall": _safe_float(row.get("rainfall_mm")),
            "humidity": _safe_float(row.get("relative_humidity_pct")),
            "rainfall_lag_1w": _safe_float(row.get("rainfall_lag_1w")),
            "rainfall_lag_2w": _safe_float(row.get("rainfall_lag_2w")),
            "rainfall_lag_3w": _safe_float(row.get("rainfall_lag_3w")),
            "rainfall_lag_4w": _safe_float(row.get("rainfall_lag_4w")),
        })

    return {"ward_id": ward_id, "weeks": weeks}


# ---------------------------------------------------------------------------
# 7. GET /api/metrics
# ---------------------------------------------------------------------------
@app.get("/api/metrics")
def metrics():
    if _METRICS is None:
        raise HTTPException(status_code=503, detail="Metrics not yet loaded.")
    return _METRICS


# ---------------------------------------------------------------------------
# 8. GET /api/historical
# ---------------------------------------------------------------------------
@app.get("/api/historical")
def historical(weeks: int = Query(52, ge=1, le=260)):
    if _FEATURED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    df = _FEATURED_DF.copy()
    # Weekly aggregate across all wards
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="d")
    weekly = (
        df.groupby("week_start")["dengue_cases"]
        .sum()
        .reset_index()
        .rename(columns={"week_start": "date", "dengue_cases": "total_cases"})
        .sort_values("date")
        .tail(weeks)
    )

    data = [
        {
            "date": row["date"].date().isoformat() if hasattr(row["date"], "date") else str(row["date"]),
            "total_cases": int(row["total_cases"]),
        }
        for _, row in weekly.iterrows()
    ]
    return {"data": data}


# ---------------------------------------------------------------------------
# 9. GET /api/comparison
# ---------------------------------------------------------------------------
@app.get("/api/comparison")
def comparison(wards: str = Query(..., description="Comma-separated list of ward IDs")):
    if _LATEST_PRED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    ward_ids = [w.strip() for w in wards.split(",") if w.strip()]
    if not ward_ids:
        raise HTTPException(status_code=400, detail="No ward IDs provided.")

    result = []
    for wid in ward_ids:
        ward_full = _PREDICTED_DF[_PREDICTED_DF["ward_id"] == wid]
        latest_row_df = _LATEST_PRED_DF[_LATEST_PRED_DF["ward_id"] == wid]

        if ward_full.empty or latest_row_df.empty:
            raise HTTPException(status_code=404, detail=f"Ward '{wid}' not found.")

        latest = latest_row_df.iloc[0]
        result.append({
            "ward_id": wid,
            "avg_temp": _safe_float(ward_full["avg_temp_c"].mean()),
            "avg_rainfall": _safe_float(ward_full["rainfall_mm"].mean()),
            "avg_humidity": _safe_float(ward_full["relative_humidity_pct"].mean()),
            "total_cases": int(ward_full["dengue_cases"].sum()),
            "predicted_cases": _safe_float(latest.get("predicted_cases")),
            "risk_tier": str(latest.get("predicted_risk_tier", "Low")),
            "waterlog_index": _safe_float(latest.get("water_logging_risk_index")),
            "population_density": _safe_float(latest.get("population_density_sqkm")),
            "sanitation_score": _safe_float(latest.get("sanitation_score")),
        })
    return result


# ---------------------------------------------------------------------------
# 10. GET /api/environmental
# ---------------------------------------------------------------------------
@app.get("/api/environmental")
def environmental():
    if _FEATURED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    df = _FEATURED_DF.dropna(subset=["dengue_cases"]).copy()

    # Sample every 50th row to keep response small
    sampled = df.iloc[::50].copy()

    rainfall_vs_dengue = [
        {"rainfall": _safe_float(r["rainfall_mm"]), "dengue_cases": _safe_float(r["dengue_cases"])}
        for _, r in sampled.iterrows()
    ]
    temp_vs_dengue = [
        {"avg_temp_c": _safe_float(r["avg_temp_c"]), "dengue_cases": _safe_float(r["dengue_cases"])}
        for _, r in sampled.iterrows()
    ]
    humidity_vs_dengue = [
        {"humidity": _safe_float(r["relative_humidity_pct"]), "dengue_cases": _safe_float(r["dengue_cases"])}
        for _, r in sampled.iterrows()
    ]
    waterlog_vs_dengue = [
        {"waterlog": _safe_float(r["water_logging_risk_index"]), "dengue_cases": _safe_float(r["dengue_cases"])}
        for _, r in sampled.iterrows()
    ]

    # Monthly trend
    df["month"] = df["date"].dt.month
    monthly = df.groupby("month")["dengue_cases"].mean().reset_index()
    monthly_trend = [
        {"month": int(r["month"]), "avg_cases": _safe_float(r["dengue_cases"])}
        for _, r in monthly.iterrows()
    ]

    # Pearson correlations (on full dataset, dropping NaN)
    def _pearson(x_col: str, y_col: str) -> float:
        pair = df[[x_col, y_col]].dropna()
        if len(pair) < 2:
            return 0.0
        corr = pair[x_col].corr(pair[y_col])
        return _safe_float(corr) or 0.0

    correlations = {
        "rainfall": _pearson("rainfall_mm", "dengue_cases"),
        "temperature": _pearson("avg_temp_c", "dengue_cases"),
        "humidity": _pearson("relative_humidity_pct", "dengue_cases"),
        "waterlog": _pearson("water_logging_risk_index", "dengue_cases"),
    }

    return {
        "rainfall_vs_dengue": rainfall_vs_dengue,
        "temp_vs_dengue": temp_vs_dengue,
        "humidity_vs_dengue": humidity_vs_dengue,
        "waterlog_vs_dengue": waterlog_vs_dengue,
        "monthly_trend": monthly_trend,
        "correlations": correlations,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
