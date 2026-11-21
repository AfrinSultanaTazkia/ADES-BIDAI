"""
Feature Engineering Module for ADES BIDAI
Implements Step 3: Multi-Week Weather Lag Pipeline per ward_id.
- Dynamically loads dataset via src.data_processing
- Sorts chronologically by [ward_id, date]
- Calculates 1, 2, 3, 4 week rainfall lags using groupby('ward_id').shift(n)
- Calculates 2-week and 4-week rolling sum/mean for rainfall
- Calculates multi-week lags for temperature and relative humidity
- Preserves all static ward features (drainage, density, sanitation)
- Provides domain vulnerability interactions and risk tiers
"""

import os
import sys
import pandas as pd
import numpy as np

# Ensure root directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_processing import get_preprocessed_data


def assign_risk_tier(cases: float) -> str:
    """
    Categorizes predicted dengue cases into actionable public health risk tiers:
    - Low: 0 - 1 case (sporadic baseline)
    - Medium: 2 - 5 cases (emerging vector activity / local breeding)
    - High: 6 - 14 cases (active outbreak surge / containment deployment)
    - Critical: 15+ cases (severe epidemic / hospital bed alerts)
    """
    if cases < 2.0:
        return "Low"
    elif cases < 6.0:
        return "Medium"
    elif cases < 15.0:
        return "High"
    else:
        return "Critical"


def compute_multi_week_lags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the multi-week lag pipeline grouped strictly per ward_id:
    - Sorts chronologically by ward_id and date
    - Computes 1, 2, 3, 4 week lags for rainfall_mm
    - Computes 2-week and 4-week rolling sum and mean for rainfall
    - Computes 1, 2, 3 week lags for temperature and humidity
    - Retains all static ward vulnerability attributes
    """
    df = df.copy()
    
    # 1. Chronological sorting per ward
    if "ward_id" in df.columns and "date" in df.columns:
        df = df.sort_values(by=["ward_id", "date"]).reset_index(drop=True)
    else:
        raise KeyError("DataFrame must contain 'ward_id' and 'date' columns.")
        
    grouped = df.groupby("ward_id")
    
    # 2. Multi-week rainfall lags (Weeks 1 to 4)
    # Reflects the 7-14 day egg-to-adult vector clock + 8-12 day viral extrinsic incubation
    for n in [1, 2, 3, 4]:
        df[f"rainfall_lag_{n}w"] = grouped["rainfall_mm"].shift(n)
        
    # 3. Rolling sum and rolling mean for rainfall (2-week and 4-week windows)
    # shift(1) ensures we strictly use prior completed weeks without lookahead leakage
    df["rainfall_roll_mean_2w"] = grouped["rainfall_mm"].transform(
        lambda s: s.shift(1).rolling(window=2, min_periods=1).mean()
    )
    df["rainfall_roll_sum_2w"] = grouped["rainfall_mm"].transform(
        lambda s: s.shift(1).rolling(window=2, min_periods=1).sum()
    )
    df["rainfall_roll_mean_4w"] = grouped["rainfall_mm"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=1).mean()
    )
    df["rainfall_roll_sum_4w"] = grouped["rainfall_mm"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=1).sum()
    )
    df["rainfall_roll_sum_3w"] = grouped["rainfall_mm"].transform(
        lambda s: s.shift(1).rolling(window=3, min_periods=1).sum()
    )
    
    # 4. Multi-week temperature lags (Weeks 1 to 3)
    for n in [1, 2, 3]:
        df[f"avg_temp_lag_{n}w"] = grouped["avg_temp_c"].shift(n)
        
    # 5. Multi-week humidity lags (Weeks 1 to 3)
    for n in [1, 2, 3]:
        df[f"humidity_lag_{n}w"] = grouped["relative_humidity_pct"].shift(n)
        
    # 6. Temperature & humidity rolling averages
    df["avg_temp_roll_mean_3w"] = grouped["avg_temp_c"].transform(
        lambda s: s.shift(1).rolling(window=3, min_periods=1).mean()
    )
    df["humidity_roll_mean_3w"] = grouped["relative_humidity_pct"].transform(
        lambda s: s.shift(1).rolling(window=3, min_periods=1).mean()
    )
    
    return df


def compute_vulnerability_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines weather lags with static ward features:
    - water_logging_risk_index (drainage bottlenecks trapping rainwater)
    - sanitation_score (uncollected solid waste / breeding container proliferation)
    - population_density_sqkm (human host crowding)
    """
    df = df.copy()
    
    # Diurnal temperature range (mortality stressor)
    if "max_temp_c" in df.columns and "min_temp_c" in df.columns:
        df["temp_range_c"] = (df["max_temp_c"] - df["min_temp_c"]).clip(lower=0)
    else:
        df["temp_range_c"] = 0.0
        
    # Rain trapped in drainage bottlenecks
    df["rain_lag2_x_waterlog"] = df["rainfall_lag_2w"] * df["water_logging_risk_index"]
    df["rain_lag3_x_waterlog"] = df["rainfall_lag_3w"] * df["water_logging_risk_index"]
    
    # Rain in unsanitary breeding sites
    unsanitary_factor = (1.0 - df["sanitation_score"]).clip(lower=0.0)
    df["rain_lag2_x_unsanitary"] = df["rainfall_lag_2w"] * unsanitary_factor
    df["rain_lag3_x_unsanitary"] = df["rainfall_lag_3w"] * unsanitary_factor
    
    # Composite vulnerability index
    df["composite_vulnerability_index"] = (
        df["water_logging_risk_index"] * 0.5 +
        unsanitary_factor * 0.5
    )
    
    # Crowding vector-host contact multiplier
    density_norm = df["population_density_sqkm"] / 50000.0
    df["density_exposure_factor"] = density_norm * df["composite_vulnerability_index"]
    
    # Vector climate suitability index
    temp_suitability = np.exp(-0.5 * ((df["avg_temp_c"] - 28.5) / 4.0) ** 2)
    humidity_suitability = 1.0 / (1.0 + np.exp(-0.15 * (df["relative_humidity_pct"] - 65.0)))
    df["vector_climate_suitability"] = temp_suitability * humidity_suitability
    
    return df


def compute_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts cyclical calendar & monsoon seasonality features from date.
    """
    df = df.copy()
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_monsoon"] = df["month"].isin([6, 7, 8, 9, 10]).astype(int)
    
    # Cyclical encodings
    df["sin_week"] = np.sin(2 * np.pi * df["week_of_year"] / 52.0)
    df["cos_week"] = np.cos(2 * np.pi * df["week_of_year"] / 52.0)
    df["sin_month"] = np.sin(2 * np.pi * df["month"] / 12.0)
    df["cos_month"] = np.cos(2 * np.pi * df["month"] / 12.0)
    
    return df


def engineer_features(df: pd.DataFrame = None, drop_burnin: bool = True) -> pd.DataFrame:
    """
    Full Step 3 pipeline:
    Dynamically loads preprocessed dataset if not passed,
    computes multi-week weather lags, rolling statistics,
    vulnerability interactions, and calendar features.
    """
    if df is None:
        df = get_preprocessed_data()
        
    print("[feature_engineering] Executing multi-week lag feature pipeline...")
    df = compute_multi_week_lags(df)
    df = compute_vulnerability_interactions(df)
    df = compute_calendar_features(df)
    
    if "dengue_cases" in df.columns:
        df["risk_tier"] = df["dengue_cases"].apply(assign_risk_tier)
        
    # Drop first 4 burn-in weeks per ward (due to 4-week lag calculation)
    if drop_burnin:
        mask = df["rainfall_lag_4w"].notna()
        burnin_dropped = int((~mask).sum())
        df = df.loc[mask].reset_index(drop=True)
        print(f"[feature_engineering] Dropped {burnin_dropped} initial burn-in rows.")
        
    print(f"[feature_engineering] Pipeline complete. Generated shape: {df.shape}")
    return df


if __name__ == "__main__":
    featured = engineer_features()
    print("\n--- LAG FEATURE SUMMARY ---")
    lag_cols = [c for c in featured.columns if "lag" in c or "roll" in c]
    print(f"Total lag/rolling features ({len(lag_cols)}):")
    print(lag_cols)
    
    print("\n--- STATIC WARD FEATURES PRESERVED ---")
    static_cols = ["ward_id", "city", "population_density_sqkm", "water_logging_risk_index", "sanitation_score"]
    print(featured[static_cols].drop_duplicates().head(5))
    
    print("\n--- SAMPLE OUTPUT PER WARD ---")
    sample_cols = ["ward_id", "date", "rainfall_mm", "rainfall_lag_1w", "rainfall_lag_2w", "rainfall_roll_sum_4w", "dengue_cases", "risk_tier"]
    print(featured[sample_cols].head(6))
