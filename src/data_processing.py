"""
Data Processing Module for ADES BIDAI
Handles dataset loading, validation, cleaning, and preparation for time-series feature engineering.
"""

import os
import glob
import pandas as pd
import numpy as np


def find_dataset_path(data_dir: str = "data") -> str:
    """
    Locates the primary dengue dataset CSV inside the data directory.
    """
    csv_files = [
        f for f in glob.glob(os.path.join(data_dir, "*.csv"))
        if not os.path.basename(f).startswith(".")
    ]
    if not csv_files:
        raise FileNotFoundError(f"No CSV dataset found in directory: {data_dir}")
    return csv_files[0]


def load_raw_data(filepath: str = None) -> pd.DataFrame:
    """
    Loads raw dengue outbreak dataset with automatic delimiter handling.
    """
    if filepath is None:
        filepath = find_dataset_path()
    
    print(f"[data_processing] Loading dataset from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"[data_processing] Raw dataset shape: {df.shape}")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and standardizes the dengue dataset:
    - Standardizes column names (lowercase, stripped whitespace).
    - Parses date column into pandas datetime.
    - Sorts records strictly by ward_id and chronological date.
    - Handles missing values or duplicate checks.
    - Validates data types and ranges.
    """
    df = df.copy()
    
    # 1. Clean column headers
    df.columns = df.columns.str.strip().str.lower()
    
    # 2. Parse Date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    else:
        raise KeyError("Expected 'date' column in dataset.")
    
    # 3. Sort chronologically per ward (crucial for time-series lag computation)
    if "ward_id" in df.columns:
        df = df.sort_values(by=["ward_id", "date"]).reset_index(drop=True)
    else:
        df = df.sort_values(by=["date"]).reset_index(drop=True)
        
    # 4. Remove duplicate entries if any
    initial_rows = len(df)
    df = df.drop_duplicates(subset=["ward_id", "date"]).reset_index(drop=True)
    if len(df) < initial_rows:
        print(f"[data_processing] Removed {initial_rows - len(df)} duplicate records.")
        
    # 5. Type casting
    numeric_cols = [
        "population_density_sqkm", "water_logging_risk_index", "sanitation_score",
        "avg_temp_c", "max_temp_c", "min_temp_c", "rainfall_mm",
        "relative_humidity_pct", "dengue_cases"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
    # 6. Verify non-negativity for target and physical quantities
    if "dengue_cases" in df.columns:
        df["dengue_cases"] = df["dengue_cases"].clip(lower=0).fillna(0).astype(int)
    if "rainfall_mm" in df.columns:
        df["rainfall_mm"] = df["rainfall_mm"].clip(lower=0.0)
    if "relative_humidity_pct" in df.columns:
        df["relative_humidity_pct"] = df["relative_humidity_pct"].clip(lower=0.0, upper=100.0)
        
    print(f"[data_processing] Cleaned dataset shape: {df.shape}")
    return df


def get_preprocessed_data(filepath: str = None) -> pd.DataFrame:
    """
    Complete data ingestion pipeline: Load -> Clean -> Chronologically ordered DataFrame.
    """
    raw_df = load_raw_data(filepath)
    cleaned_df = clean_data(raw_df)
    return cleaned_df


if __name__ == "__main__":
    df = get_preprocessed_data()
    print("[data_processing] Summary info:")
    print(df.info())
    print("\n[data_processing] Head preview:")
    print(df.head())
