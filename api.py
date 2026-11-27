"""
ADES BIDAI - Comprehensive FastAPI Backend
Phase 1: Dengue Outbreak Prediction & Early Warning System
Phase 2: Constrained Resource Allocation & Vector-Control Crew Assignment Engine

Endpoints:
  Phase 1:
    GET  /api/health
    GET  /api/summary
    GET  /api/wards
    GET  /api/ward/{ward_id}
    GET  /api/predict
    GET  /api/weather/{ward_id}
    GET  /api/metrics
    GET  /api/historical
    GET  /api/comparison
    GET  /api/environmental

  Phase 2:
    GET  /api/allocation/current
    POST /api/allocation/simulate
    POST /api/allocation/approve
    GET  /api/allocation/audit-logs
    POST /api/allocation/redistribute
    POST /api/allocation/counterfactual
    GET  /api/allocation/export/pdf
    GET  /api/allocation/export/html
    GET  /api/allocation/notifications
"""

import os
import sys
import json
import math
from datetime import datetime
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from src.data_processing import get_preprocessed_data
from src.feature_engineering import engineer_features
from src.prediction import predict_dataframe, map_quantile_tier
from utils.ward_coordinates import ALL_WARD_COORDS, WARD_AREAS, haversine_distance_km
from src.resource_engine import DengueResourceEngine, DEFAULT_DATASET
from src.hospital_routing import HospitalOverflowRoutingEngine
from src.database import (
    save_approved_plan,
    get_audit_logs,
    record_redistribution,
    log_audit,
    save_approved_hospital_plan,
    get_approved_hospital_plans,
    revalidate_hospital_plans,
)
from src.reports import generate_pdf_report, generate_html_report, generate_notification_templates

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ADES BIDAI – Dengue Surveillance & Resource Allocation API",
    description="Intelligent 2-Week Outbreak Prediction, Constrained Medical Resource Allocation, and Vector-Control Crew Assignment.",
    version="2.0.0",
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
_FEATURED_DF: Optional[pd.DataFrame] = None
_PREDICTED_DF: Optional[pd.DataFrame] = None
_LATEST_PRED_DF: Optional[pd.DataFrame] = None
_ARTIFACT: Optional[Dict[str, Any]] = None
_METRICS: Optional[Dict[str, Any]] = None
_MODEL_MAE: float = 0.827
_RESOURCE_ENGINE: Optional[DengueResourceEngine] = None


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
# Pydantic Request Models
# ---------------------------------------------------------------------------
class SimulationRequest(BaseModel):
    stock_percentage: float = Field(100.0, ge=30.0, le=100.0, description="Available regional stock percentage (30-100%)")
    total_spraying_crews: int = Field(150, ge=0, le=1000, description="Total available mosquito-control spraying crews")
    custom_availability: Optional[Dict[str, Dict[str, int]]] = Field(None, description="Optional custom ward inventory overrides")
    manual_allocations: Optional[Dict[str, Dict[str, int]]] = Field(None, description="Optional manual resource allocation modifications")
    manual_crews: Optional[Dict[str, int]] = Field(None, description="Optional manual crew assignments")


class ApprovalRequest(BaseModel):
    plan_name: str = Field("Official Regional Dengue Plan", description="Name of the allocation plan")
    approved_by: str = Field("Central Health Administrator", description="Official approving authority")
    stock_percentage: float = Field(100.0, ge=30.0, le=100.0)
    total_spraying_crews: int = Field(150, ge=0, le=1000)
    custom_availability: Optional[Dict[str, Dict[str, int]]] = None
    manual_allocations: Optional[Dict[str, Dict[str, int]]] = None
    manual_crews: Optional[Dict[str, int]] = None


class RedistributionRequest(BaseModel):
    resource_type: str = Field(..., description="Resource to transfer (e.g., 'Saline Bags', 'Diagnostic Kits')")
    source_ward_id: str = Field(..., description="Donor ward ID")
    destination_ward_id: str = Field(..., description="Recipient ward ID")
    quantity: int = Field(..., ge=1, description="Number of units to transfer")
    reason: str = Field(..., description="Justification for redistribution")
    user: str = Field("Central Health Administrator", description="Administrator name")


class CounterfactualRequest(BaseModel):
    ward_id: str = Field(..., description="Target ward ID")
    crews_assigned: int = Field(..., ge=0, le=50, description="Number of spraying crews to deploy")
    larvicide_coverage_pct: float = Field(80.0, ge=0.0, le=100.0, description="Target breeding site larviciding coverage (%)")


class HospitalSimulationRequest(BaseModel):
    stock_percentage: float = Field(100.0, ge=30.0, le=100.0, description="Available regional bed capacity percentage (30-100%)")
    custom_bed_demand: Optional[Dict[str, int]] = Field(None, description="Optional manual ward bed demand overrides for simulation")
    custom_bed_capacity: Optional[Dict[str, int]] = Field(None, description="Optional manual ward usable bed capacity overrides")
    scenario_name: str = Field("Hospital Overflow Simulation", description="Scenario label")


class HospitalApprovalRequest(BaseModel):
    plan_name: str = Field("Official Hospital Overflow Routing Plan", description="Name of the routing plan")
    approved_by: str = Field("Central Health Administrator", description="Official approving authority")
    stock_percentage: float = Field(100.0, ge=30.0, le=100.0)
    custom_bed_demand: Optional[Dict[str, int]] = None
    custom_bed_capacity: Optional[Dict[str, int]] = None


# ---------------------------------------------------------------------------
# Startup Event
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_load():
    global _FEATURED_DF, _PREDICTED_DF, _LATEST_PRED_DF, _ARTIFACT, _METRICS, _MODEL_MAE, _RESOURCE_ENGINE

    print("[api] Initializing Resource Engine on specified dataset...")
    csv_path = DEFAULT_DATASET
    if not os.path.exists(csv_path):
        csv_path = os.path.join(ROOT, "data", "google_sheet_dengue_dataset.csv")

    _RESOURCE_ENGINE = DengueResourceEngine(dataset_path=csv_path)

    print("[api] Loading and preprocessing dataset for Phase 1 endpoints...")
    raw_df = get_preprocessed_data(filepath=csv_path)
    _FEATURED_DF = engineer_features(raw_df, drop_burnin=True)

    model_path = os.path.join(ROOT, "models", "dengue_outbreak_model.joblib")
    if os.path.exists(model_path):
        _ARTIFACT = joblib.load(model_path)
        _PREDICTED_DF = predict_dataframe(_FEATURED_DF, model_path=model_path)
    else:
        _PREDICTED_DF = _FEATURED_DF.copy()
        _PREDICTED_DF["predicted_cases"] = _PREDICTED_DF["dengue_cases"]
        _PREDICTED_DF["predicted_risk_tier"] = "Low"

    _LATEST_PRED_DF = (
        _PREDICTED_DF
        .sort_values(["ward_id", "date"])
        .groupby("ward_id", as_index=False)
        .last()
    )

    metrics_path = os.path.join(ROOT, "models", "metrics_summary.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            _METRICS = json.load(f)
        _MODEL_MAE = _METRICS.get("HistGradientBoosting", {}).get("MAE", 0.827)

    print("[api] System ready. All 60 wards integrated.")


# ===========================================================================
# PHASE 1 ENDPOINTS
# ===========================================================================
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ADES BIDAI Surveillance & Resource Allocation Platform",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


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


@app.get("/api/wards")
def wards():
    if _LATEST_PRED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    result = []
    for _, row in _LATEST_PRED_DF.iterrows():
        wid = str(row["ward_id"])
        coords = ALL_WARD_COORDS.get(wid, (23.8103, 90.4125, wid))
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


@app.get("/api/ward/{ward_id}")
def ward_detail(ward_id: str):
    if _PREDICTED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    ward_df = _PREDICTED_DF[_PREDICTED_DF["ward_id"] == ward_id].sort_values("date")
    if ward_df.empty:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")

    coords = ALL_WARD_COORDS.get(ward_id, (23.8103, 90.4125, ward_id))
    lat, lon = _safe_float(coords[0], 6), _safe_float(coords[1], 6)
    locality = coords[2] if len(coords) > 2 else ward_id

    latest_row = ward_df.iloc[-1]
    city = str(latest_row.get("city", "")) if "city" in latest_row else ""
    current_risk_tier = str(latest_row.get("predicted_risk_tier", "Low"))

    predicted_2w = _safe_float(latest_row.get("predicted_cases", 0.0))
    last4 = ward_df.tail(4)["predicted_cases"]
    predicted_4w = _safe_float(last4.mean())

    history_df = ward_df.tail(12)
    history = [
        {
            "date": hrow["date"].date().isoformat() if hasattr(hrow["date"], "date") else str(hrow["date"]),
            "cases": int(hrow.get("dengue_cases", 0)),
            "predicted": _safe_float(hrow.get("predicted_cases", 0)),
        }
        for _, hrow in history_df.iterrows()
    ]

    weather_summary = {
        "avg_temp": _safe_float(latest_row.get("avg_temp_c")),
        "rainfall": _safe_float(latest_row.get("rainfall_mm")),
        "humidity": _safe_float(latest_row.get("relative_humidity_pct")),
        "waterlog": _safe_float(latest_row.get("water_logging_risk_index")),
        "sanitation": _safe_float(latest_row.get("sanitation_score")),
        "density": _safe_float(latest_row.get("population_density_sqkm")),
    }
    risk_drivers = _build_risk_drivers(latest_row)

    half_width_2w = round(1.5 * _MODEL_MAE, 2)
    pred_2w_val = predicted_2w or 0.0
    pred_4w_val = predicted_4w or 0.0

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
        "confidence_interval_2w": {
            "lower": _safe_float(max(0.0, pred_2w_val - half_width_2w)),
            "upper": _safe_float(pred_2w_val + half_width_2w),
        },
        "confidence_interval_4w": {
            "lower": _safe_float(max(0.0, pred_4w_val - round(1.5 * _MODEL_MAE * math.sqrt(2), 2))),
            "upper": _safe_float(pred_4w_val + round(1.5 * _MODEL_MAE * math.sqrt(2), 2)),
        },
    }


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
    predicted_cases = float(latest_row.get("predicted_cases", 0.0))
    thresholds = _ARTIFACT.get("quantile_thresholds") if _ARTIFACT else None
    risk_tier = map_quantile_tier(predicted_cases, thresholds)

    half_width = round(1.5 * _MODEL_MAE * math.sqrt(max(1, horizon / 2)), 2)

    return {
        "ward_id": ward_id,
        "horizon_weeks": horizon,
        "predicted_cases": _safe_float(predicted_cases),
        "risk_tier": risk_tier,
        "confidence_lower": _safe_float(max(0.0, predicted_cases - half_width)),
        "confidence_upper": _safe_float(predicted_cases + half_width),
        "primary_drivers": _build_risk_drivers(latest_row),
    }


@app.get("/api/weather/{ward_id}")
def weather(ward_id: str):
    if _FEATURED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    ward_df = _FEATURED_DF[_FEATURED_DF["ward_id"] == ward_id].sort_values("date")
    if ward_df.empty:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")

    last4 = ward_df.tail(4).reset_index(drop=True)
    weeks = [
        {
            "week_label": f"Week -{len(last4) - i}",
            "date": row["date"].date().isoformat() if hasattr(row["date"], "date") else str(row["date"]),
            "avg_temp": _safe_float(row.get("avg_temp_c")),
            "rainfall": _safe_float(row.get("rainfall_mm")),
            "humidity": _safe_float(row.get("relative_humidity_pct")),
            "rainfall_lag_1w": _safe_float(row.get("rainfall_lag_1w")),
            "rainfall_lag_2w": _safe_float(row.get("rainfall_lag_2w")),
            "rainfall_lag_3w": _safe_float(row.get("rainfall_lag_3w")),
            "rainfall_lag_4w": _safe_float(row.get("rainfall_lag_4w")),
        }
        for i, (_, row) in enumerate(last4.iterrows())
    ]
    return {"ward_id": ward_id, "weeks": weeks}


@app.get("/api/metrics")
def metrics():
    if _METRICS is None:
        raise HTTPException(status_code=503, detail="Metrics not yet loaded.")
    return _METRICS


@app.get("/api/historical")
def historical(weeks: int = Query(52, ge=1, le=260)):
    if _FEATURED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    df = _FEATURED_DF.copy()
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="d")
    weekly = (
        df.groupby("week_start")["dengue_cases"]
        .sum()
        .reset_index()
        .rename(columns={"week_start": "date", "dengue_cases": "total_cases"})
        .sort_values("date")
        .tail(weeks)
    )
    return {
        "data": [
            {
                "date": row["date"].date().isoformat() if hasattr(row["date"], "date") else str(row["date"]),
                "total_cases": int(row["total_cases"]),
            }
            for _, row in weekly.iterrows()
        ]
    }


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


@app.get("/api/environmental")
def environmental():
    if _FEATURED_DF is None:
        raise HTTPException(status_code=503, detail="Data not yet loaded.")

    df = _FEATURED_DF.dropna(subset=["dengue_cases"]).copy()
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

    df["month"] = df["date"].dt.month
    monthly = df.groupby("month")["dengue_cases"].mean().reset_index()
    monthly_trend = [
        {"month": int(r["month"]), "avg_cases": _safe_float(r["dengue_cases"])}
        for _, r in monthly.iterrows()
    ]

    def _pearson(x_col: str, y_col: str) -> float:
        pair = df[[x_col, y_col]].dropna()
        if len(pair) < 2:
            return 0.0
        corr = pair[x_col].corr(pair[y_col])
        return _safe_float(corr) or 0.0

    return {
        "rainfall_vs_dengue": rainfall_vs_dengue,
        "temp_vs_dengue": temp_vs_dengue,
        "humidity_vs_dengue": humidity_vs_dengue,
        "waterlog_vs_dengue": waterlog_vs_dengue,
        "monthly_trend": monthly_trend,
        "correlations": {
            "rainfall": _pearson("rainfall_mm", "dengue_cases"),
            "temperature": _pearson("avg_temp_c", "dengue_cases"),
            "humidity": _pearson("relative_humidity_pct", "dengue_cases"),
            "waterlog": _pearson("water_logging_risk_index", "dengue_cases"),
        },
    }


# ===========================================================================
# PHASE 2: RESOURCE ALLOCATION & CREW ENGINE ENDPOINTS
# ===========================================================================
@app.get("/api/allocation/current")
def get_current_allocation(
    stock_percentage: float = Query(100.0, ge=30.0, le=100.0, description="Available regional stock percentage"),
    total_crews: int = Query(150, ge=0, le=1000, description="Available mosquito-control spraying crews"),
):
    """
    Runs the Priority-Based Constrained Greedy Allocation Engine across all 60 wards.
    Returns dynamic allocations, scarcity calculations, hospital overflow routing, and critical warnings.
    """
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    result = _RESOURCE_ENGINE.run_allocation_engine(
        stock_percentage=stock_percentage,
        total_spraying_crews=total_crews,
    )
    return result


@app.post("/api/allocation/simulate")
def simulate_allocation(payload: SimulationRequest):
    """
    Simulates allocation changes with administrator interactive scarcity controls and manual overrides.
    Does NOT modify the persistent approved database plan.
    """
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    result = _RESOURCE_ENGINE.run_allocation_engine(
        stock_percentage=payload.stock_percentage,
        total_spraying_crews=payload.total_spraying_crews,
        custom_availability=payload.custom_availability,
        manual_allocations=payload.manual_allocations,
        manual_crews=payload.manual_crews,
    )
    return result


@app.post("/api/allocation/approve")
def approve_allocation(payload: ApprovalRequest):
    """
    Validates and persists the administrator-approved allocation plan to the SQLite database.
    Creates an immutable audit log entry.
    """
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    # 1. Run engine with final parameters
    result = _RESOURCE_ENGINE.run_allocation_engine(
        stock_percentage=payload.stock_percentage,
        total_spraying_crews=payload.total_spraying_crews,
        custom_availability=payload.custom_availability,
        manual_allocations=payload.manual_allocations,
        manual_crews=payload.manual_crews,
    )

    # 2. Validate constraints: no over-allocation beyond effective regional stock
    scarcity = result["scarcity_controls"]
    overview = result["regional_overview"]

    if overview["total_saline_allocated"] > scarcity["effective_saline_stock"]:
        raise HTTPException(
            status_code=400,
            detail=f"Approved saline allocation ({overview['total_saline_allocated']}) exceeds effective regional stock ({scarcity['effective_saline_stock']})."
        )
    if overview["total_kits_allocated"] > scarcity["effective_kits_stock"]:
        raise HTTPException(
            status_code=400,
            detail=f"Approved kits allocation ({overview['total_kits_allocated']}) exceeds effective regional stock ({scarcity['effective_kits_stock']})."
        )
    if overview["total_assigned_crews"] > scarcity["total_spraying_crews"]:
        raise HTTPException(
            status_code=400,
            detail=f"Assigned crews ({overview['total_assigned_crews']}) exceed total available crews ({scarcity['total_spraying_crews']})."
        )

    # 3. Save to SQLite database
    plan_id = save_approved_plan(
        plan_result=result,
        plan_name=payload.plan_name,
        approved_by=payload.approved_by,
    )

    return {
        "status": "Approved",
        "plan_id": plan_id,
        "plan_name": payload.plan_name,
        "approved_by": payload.approved_by,
        "approved_at": datetime.utcnow().isoformat() + "Z",
        "critical_deficits_count": overview["critical_supply_wards_count"],
        "message": f"Plan successfully approved and recorded in official registry (ID: {plan_id}).",
    }


@app.get("/api/allocation/audit-logs")
def audit_logs(limit: int = Query(100, ge=1, le=500)):
    """Retrieves chronological audit trail of all approved plans and redistribution transfers."""
    logs = get_audit_logs(limit=limit)
    return {"logs": logs, "total_records": len(logs)}


@app.post("/api/allocation/redistribute")
def redistribute_resources(payload: RedistributionRequest):
    """
    Approves and records an inter-ward transfer of eligible surplus supplies (saline bags or kits).
    """
    transfer_id = record_redistribution(
        resource_type=payload.resource_type,
        source_ward_id=payload.source_ward_id,
        destination_ward_id=payload.destination_ward_id,
        quantity=payload.quantity,
        reason=payload.reason,
        status="Approved",
        user=payload.user,
    )
    return {
        "status": "Transferred",
        "transfer_id": transfer_id,
        "resource_type": payload.resource_type,
        "source_ward_id": payload.source_ward_id,
        "destination_ward_id": payload.destination_ward_id,
        "quantity": payload.quantity,
        "message": f"Successfully authorized transfer of {payload.quantity} units to {payload.destination_ward_id}.",
    }


@app.post("/api/allocation/counterfactual")
def counterfactual_simulation(payload: CounterfactualRequest):
    """
    ML Counterfactual Simulation: Evaluates outbreak reduction and resource savings
    achievable by deploying spraying crews and larvicide in a targeted ward.
    """
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    try:
        impact = _RESOURCE_ENGINE.simulate_counterfactual_intervention(
            ward_id=payload.ward_id,
            crews_assigned=payload.crews_assigned,
            larvicide_coverage_pct=payload.larvicide_coverage_pct,
        )
        return impact
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/allocation/export/pdf")
def export_pdf(
    stock_percentage: float = Query(100.0, ge=30.0, le=100.0),
    total_crews: int = Query(150, ge=0, le=1000),
):
    """Generates and streams an official Government ReportLab PDF report."""
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    result = _RESOURCE_ENGINE.run_allocation_engine(
        stock_percentage=stock_percentage,
        total_spraying_crews=total_crews,
    )
    pdf_bytes = generate_pdf_report(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ades_bidai_resource_plan_{int(stock_percentage)}pct.pdf"
        },
    )


@app.get("/api/allocation/export/html", response_class=HTMLResponse)
def export_html(
    stock_percentage: float = Query(100.0, ge=30.0, le=100.0),
    total_crews: int = Query(150, ge=0, le=1000),
):
    """Generates a complete standalone HTML report formatted with Jinja2."""
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    result = _RESOURCE_ENGINE.run_allocation_engine(
        stock_percentage=stock_percentage,
        total_spraying_crews=total_crews,
    )
    html_content = generate_html_report(result)
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/api/allocation/notifications")
def get_notifications(
    stock_percentage: float = Query(100.0, ge=30.0, le=100.0),
    total_crews: int = Query(150, ge=0, le=1000),
):
    """Generates deterministic SMS and WhatsApp broadcast templates for field teams."""
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    result = _RESOURCE_ENGINE.run_allocation_engine(
        stock_percentage=stock_percentage,
        total_spraying_crews=total_crews,
    )
    notifications = generate_notification_templates(result)
    return {"notifications": notifications, "count": len(notifications)}


# ===========================================================================
# PHASE 2: HOSPITAL SURGE & CROSS-WARD OVERFLOW ROUTING ENDPOINTS
# ===========================================================================
@app.get("/api/hospital-routing/current")
def get_current_hospital_routing(
    stock_percentage: float = Query(100.0, ge=30.0, le=100.0, description="Available regional bed capacity percentage"),
):
    """
    Executes City-Constrained Priority-Based Greedy Hospital Bed Overflow Routing.
    Returns:
    - scenario_metadata
    - ward_results (all 60 wards with initial & net deficits, spare beds, utilization, warnings)
    - city_results (Dhaka North, Dhaka South, Chattogram, Gazipur, Narayanganj metrics)
    - routing_assignments (source, dest, routed overflow, utilization before/after)
    - regional_summary (aggregate KPIs)
    - critical_warnings (ward and city surge alerts)
    - dispatch_notices (deterministic local notice templates)
    - validation_results (accounting identities verification)
    """
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    if hasattr(stock_percentage, "default"):
        stock_percentage = stock_percentage.default

    result = _RESOURCE_ENGINE.run_hospital_routing(
        stock_percentage=float(stock_percentage),
        scenario_name="Current Baseline Hospital Routing Plan",
    )
    return result


@app.post("/api/hospital-routing/simulate")
def simulate_hospital_routing(payload: HospitalSimulationRequest):
    """
    Interactive Simulator for Hospital Bed Demand and Usable Capacity.
    Allows administrators to adjust bed demand, usable capacity, and scarcity controls.
    Does NOT modify the original dataset or overwrite approved routing plans.
    """
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    result = _RESOURCE_ENGINE.run_hospital_routing(
        stock_percentage=payload.stock_percentage,
        custom_bed_demand=payload.custom_bed_demand,
        custom_bed_capacity=payload.custom_bed_capacity,
        scenario_name=payload.scenario_name,
    )
    return result


@app.post("/api/hospital-routing/approve")
def approve_hospital_routing(payload: HospitalApprovalRequest):
    """
    Validates and persists the administrator-approved hospital overflow routing plan to SQLite.
    Creates immutable audit logs and records individual routing assignments.
    """
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    # 1. Run routing engine to get canonical result
    result = _RESOURCE_ENGINE.run_hospital_routing(
        stock_percentage=payload.stock_percentage,
        custom_bed_demand=payload.custom_bed_demand,
        custom_bed_capacity=payload.custom_bed_capacity,
        scenario_name=payload.plan_name,
    )

    # 2. Persist to SQLite database
    plan_id = save_approved_hospital_plan(
        routing_result=result,
        plan_name=payload.plan_name,
        approved_by=payload.approved_by,
        stock_percentage=payload.stock_percentage,
    )

    reg = result["regional_summary"]
    return {
        "status": "Approved",
        "plan_id": plan_id,
        "plan_name": payload.plan_name,
        "approved_by": payload.approved_by,
        "approved_at": datetime.utcnow().isoformat() + "Z",
        "total_routed_overflow": reg["total_routed_overflow"],
        "unresolved_net_deficit": reg["total_unresolved_bed_deficit"],
        "shortage_resolution_percentage": reg["overall_shortage_resolution_percentage"],
        "message": f"Hospital routing plan successfully approved and recorded in official registry (Plan ID: {plan_id}).",
    }


@app.get("/api/hospital-routing/approved-plans")
def get_approved_hospital_routing_plans(limit: int = Query(50, ge=1, le=200)):
    """Retrieves all administrator-approved hospital routing plans from SQLite."""
    plans = get_approved_hospital_plans(limit=limit)
    return {"plans": plans, "total_records": len(plans)}


@app.get("/api/hospital-routing/notices")
def get_hospital_dispatch_notices(
    stock_percentage: float = Query(100.0, ge=30.0, le=100.0),
    city: Optional[str] = Query(None, description="Optional city filter"),
):
    """Returns deterministic offline template-based dispatch notices."""
    if _RESOURCE_ENGINE is None:
        raise HTTPException(status_code=503, detail="Resource engine not initialized.")

    if hasattr(stock_percentage, "default"):
        stock_percentage = stock_percentage.default
    if hasattr(city, "default"):
        city = city.default

    result = _RESOURCE_ENGINE.run_hospital_routing(stock_percentage=float(stock_percentage))
    notices = result.get("dispatch_notices", [])
    if city:
        notices = [n for n in notices if n.get("city", "").lower() == str(city).strip().lower()]
    return {
        "status": "success",
        "data": {
            "notices": notices,
            "count": len(notices),
        }
    }


@app.post("/api/hospital-routing/revalidate")
def revalidate_approved_plans():
    """Marks approved plans as requiring revalidation when underlying hospital capacity or demand shifts."""
    count = revalidate_hospital_plans(reason="Administrator triggered revalidation check")
    return {
        "status": "Revalidation Required",
        "plans_affected": count,
        "message": f"{count} approved hospital routing plan(s) marked for administrative revalidation.",
    }


# ===========================================================================
# Static Frontend Mount for Offline Execution
# ===========================================================================
frontend_dist = os.path.join(ROOT, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_react_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
