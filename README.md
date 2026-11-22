# 🦟 এডিস বিদায় (ADES BIDAI) — AI-Based Dengue Outbreak Prediction & Alert System

> **"সময়মতো খবর রাখি, ডেঙ্গুকে বিদায় জানাই।"** | Predict. Prevent. Protect.

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.67-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 Project Overview

ADES BIDAI is an AI-powered dengue outbreak early-warning platform that predicts ward-level dengue risk **2–4 weeks ahead** using historical disease surveillance data, weather patterns, and environmental vulnerability indicators across **60 wards in 5 Bangladeshi cities**.

**Hackathon:** Phase 1 Preliminary Round 2026
**Team:** Afrin Sultana Tazkia

---

## 🏆 Key Features

| Feature | Description |
|---------|-------------|
| 🤖 ML Prediction | HistGradientBoosting model (MAE: 0.827, R²: 0.838) |
| ⏱️ 2–4 Week Forecast | Multi-week lag features capture vector breeding cycles |
| 🗺️ Risk Map | Interactive ward-level scatter map (Low/Medium/High/Critical) |
| 📊 9 Dashboard Pages | Full analytical suite with real data |
| 🔌 REST API | FastAPI backend with 10 endpoints |
| ⚡ Zero Retraining | Serialized model loads once, inference <10ms |
| 💰 Zero Cost | No external APIs, no cloud services, fully local |

---

## 🏙️ Dataset Coverage

| City Corporation | Code | Wards | Dataset Rows |
|-----------------|------|-------|-------------|
| Dhaka North | DNCC | 20 | 10,920 |
| Dhaka South | DSCC | 15 | 8,190 |
| Chattogram | CCC | 10 | 5,460 |
| Gazipur | GCC | 8 | 4,368 |
| Narayanganj | NCC | 7 | 3,822 |
| **Total** | | **60** | **31,320** |

**Time Span:** 2016-01-04 → 2025-12-29 (522 weeks per ward)

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit 1.67 |
| Backend API | FastAPI + Uvicorn |
| ML Model | scikit-learn HistGradientBoosting |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly Express & Graph Objects |
| Model Storage | joblib serialization |
| Map | Plotly scatter_map (OpenStreetMap) |

---

## ⚙️ Installation

### Prerequisites
- Python 3.10+ (tested on 3.14)
- pip

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/AfrinSultanaTazkia/ADES-BIDAI.git
cd ADES-BIDAI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place dataset in data/ folder
# File: data/google_sheet_dengue_dataset.csv
# (The official hackathon dataset)
```

---

## 🚀 Running the Application

### Option A: One-Click Launch (Windows)
```
Double-click: run.bat
```
This starts both the API backend and Streamlit frontend.

### Option B: Manual Launch (2 terminals)

**Terminal 1 — Start API Backend:**
```bash
python api.py
# API running at: http://localhost:8000
# Interactive docs: http://localhost:8000/docs
```

**Terminal 2 — Start Dashboard:**
```bash
python -m streamlit run app.py --server.port 8501
# Dashboard at: http://localhost:8501
```

### Option C: Dashboard Only (no API, local fallback mode)
```bash
python -m streamlit run app.py
# Uses local data loading if API unavailable
```

---

## 🔄 Training the Model

The trained model is already included at `models/dengue_outbreak_model.joblib`.

To retrain (e.g., with updated data):
```bash
python src/train_model.py
# Trains on 2016-2023, evaluates on 2024-2025
# Saves: models/dengue_outbreak_model.joblib
#        models/metrics_summary.json
```

---

## 🔌 API Endpoints

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/summary` | Dashboard KPIs (cases, wards, weather) |
| GET | `/api/wards` | All 60 wards with predicted risk |
| GET | `/api/ward/{ward_id}` | Single ward detail + 12-week history |
| GET | `/api/predict?ward_id=X&horizon=2` | 2 or 4-week prediction |
| GET | `/api/weather/{ward_id}` | Last 4 weeks weather data |
| GET | `/api/metrics` | Real model evaluation metrics |
| GET | `/api/historical?weeks=52` | Weekly aggregated case trend |
| GET | `/api/comparison?wards=W1,W2` | Multi-ward comparison |
| GET | `/api/environmental` | Rainfall/temp/humidity correlations |

**Interactive API docs:** http://localhost:8000/docs

---

## 📊 Model Performance

| Model | MAE | RMSE | R² | Tier Accuracy |
|-------|-----|------|----|---------------|
| Ridge Baseline | 1.057 | 1.858 | 0.768 | 79.81% |
| RandomForest | 0.868 | 1.631 | 0.822 | 84.92% |
| **HistGradientBoosting ✅** | **0.827** | **1.554** | **0.838** | **85.59%** |

**Validation strategy:** Strictly chronological split (2016–2023 train, 2024–2025 test). No random splits.

---

## 🏘️ Risk Tier Classification

| Tier | Cases/Week | Color | Action |
|------|-----------|-------|--------|
| 🟢 Low | < 1.5 | Green | Monitor |
| 🟡 Medium | 1.5 – 4.0 | Orange | Prepare |
| 🔴 High | 4.0 – 10.0 | Red | Respond |
| 🟣 Critical | ≥ 10.0 | Purple | Emergency |

Thresholds derived from training data quantiles (q50, q75, q90).

---

## 📐 Feature Engineering

Key engineered features capturing the **2–4 week vector breeding cycle**:

| Feature | Rationale |
|---------|-----------|
| `rainfall_lag_1w` to `_4w` | Aedes larval emergence (7–14 days) + extrinsic incubation (8–12 days) |
| `rainfall_roll_sum_4w` | Cumulative breeding pool saturation |
| `composite_vulnerability_index` | Water-logging × sanitation interaction |
| `vector_climate_suitability` | Gaussian optimal temp (28.5°C) × logistic humidity |
| `is_monsoon` | Seasonal risk flag for June–October |

---

## 🤖 AI Disclosure

This project uses AI/ML (HistGradientBoosting Regressor from scikit-learn).
- **No external LLM APIs** were used for predictions.
- **No external weather APIs** are connected (historical dataset only).
- **Zero API cost** during inference — all predictions are local.
- Predictions are for **awareness and planning** only, not clinical diagnosis.

---

## ⚠️ Limitations

1. No real-time weather data integration (uses historical patterns only)
2. Ward coordinates are centroids, not actual boundaries (no GeoJSON available)
3. Confidence intervals are approximated (±1.5×MAE), not bootstrap-exact
4. Cannot predict novel outbreak drivers outside training distribution
5. Model trained on Bangladesh urban surveillance data — not generalizable globally

---

## 📁 Project Structure

```
ADES-BIDAI/
├── app.py                    # Main Dashboard (Page 1)
├── api.py                    # FastAPI Backend
├── run.bat                   # One-click launcher
├── requirements.txt
├── README.md
├── ARCHITECTURE.md
├── data/
│   └── google_sheet_dengue_dataset.csv   # Official dataset
├── models/
│   ├── dengue_outbreak_model.joblib      # Trained model artifact
│   └── metrics_summary.json              # Evaluation results
├── src/
│   ├── data_processing.py    # CSV loading + cleaning
│   ├── feature_engineering.py # Multi-week lag pipeline
│   ├── train_model.py        # Chronological ML training
│   └── prediction.py         # Inference engine
├── utils/
│   └── ward_coordinates.py   # 60 ward lat/lon centroids
├── pages/
│   ├── 01_Risk_Map.py        # Ward risk visualization
│   ├── 02_Outbreak_Prediction.py # Prediction explorer
│   ├── 03_Weather_Monitoring.py  # Weather analysis
│   ├── 04_Ward_Comparison.py     # Multi-ward compare
│   ├── 05_Model_Performance.py   # ML metrics
│   ├── 06_Environmental_Analysis.py # Correlations
│   ├── 07_Prevention_Awareness.py   # Health guidance
│   └── 08_About_Project.py          # Project info
└── .streamlit/
    └── config.toml
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ for public health in Bangladesh | ADES BIDAI © 2026*
