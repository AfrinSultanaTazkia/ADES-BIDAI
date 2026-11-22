# ADES BIDAI — System Architecture

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         ADES BIDAI                              │
│         AI-Based Dengue Outbreak Prediction & Alert System      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐     HTTP REST      ┌──────────────────────────┐
│  Streamlit   │ ◄────────────────► │  FastAPI Backend         │
│  Dashboard   │   localhost:8000   │  api.py                  │
│  app.py +    │                    │  - /api/summary          │
│  pages/*.py  │                    │  - /api/wards            │
│  port 8501   │                    │  - /api/predict          │
└──────┬───────┘                    │  - /api/weather          │
       │                            │  - /api/metrics          │
       │ Fallback (local mode)      │  - /api/environmental    │
       ▼                            └──────────┬───────────────┘
┌──────────────┐                              │
│  src/ modules│ ◄────────────────────────────┘
│  - data_proc │  loads at startup
│  - feat_eng  │
│  - prediction│
└──────┬───────┘
       │
       ▼
┌──────────────┐    ┌────────────────────────────────┐
│   data/      │    │  models/                       │
│   *.csv      │    │  dengue_outbreak_model.joblib  │
│  31,320 rows │    │  metrics_summary.json          │
└──────────────┘    └────────────────────────────────┘
```

---

## 2. Data Flow

```
                        DATA PIPELINE
                        ============

📂 Raw CSV
(google_sheet_dengue_dataset.csv)
   │
   ▼
🧹 src/data_processing.py
   ├── Column standardization (lowercase, strip)
   ├── Date parsing → pd.Timestamp
   ├── Chronological sort: [ward_id, date]
   ├── Duplicate removal
   ├── Type casting (numeric coerce)
   └── Non-negativity clipping (dengue_cases ≥ 0, rainfall_mm ≥ 0)
   │
   ▼
⚙️ src/feature_engineering.py
   ├── Multi-week rainfall lags [1w, 2w, 3w, 4w] per ward_id
   │   └── groupby('ward_id').shift(n) — NO data leakage
   ├── Rolling statistics (2w/4w mean+sum) with shift(1) guard
   ├── Temperature lags [1w, 2w, 3w] per ward
   ├── Humidity lags [1w, 2w, 3w] per ward
   ├── Interaction features (rain × waterlog, rain × unsanitary)
   ├── Composite vulnerability index
   ├── Vector climate suitability (Gaussian + logistic)
   ├── Calendar features (month, week, monsoon flag, cyclical sin/cos)
   └── Drop 4-row burn-in per ward (NaN from 4-week lag)
   │
   ▼
🤖 src/train_model.py
   ├── Chronological split (strict, no shuffle)
   │   ├── Train: 2016-01-01 → 2023-12-31
   │   └── Test:  2024-01-01 → 2025-12-29
   ├── 3 models compared: Ridge, RandomForest, HistGradientBoosting
   ├── Evaluation: MAE, RMSE, R², Tier Accuracy
   ├── Winner selection: HistGradientBoosting
   └── Save: models/dengue_outbreak_model.joblib
   │
   ▼
🎯 src/prediction.py
   ├── Load model once (cached)
   ├── Predict on feature vectors
   ├── Clip negative predictions to 0
   ├── Map to risk tier via dynamic quantile thresholds
   └── Extract rule-based risk drivers
   │
   ▼
📊 Streamlit Dashboard + FastAPI
```

---

## 3. Feature Engineering — Epidemiological Rationale

### Why Multi-Week Lags?

The **Aedes aegypti dengue transmission cycle** operates on a 2–4 week time horizon:

| Phase | Duration | Feature |
|-------|----------|---------|
| Egg hatching → larvae → pupae | 7–14 days | `rainfall_lag_2w` |
| Adult emergence + blood meal | 2–3 days | `rainfall_lag_2w` |
| Extrinsic incubation (virus in mosquito) | 8–12 days | `rainfall_lag_3w` |
| Human infection → symptom onset | 4–7 days | `rainfall_lag_4w` |
| **Total lag from rainfall to cases** | **~3–4 weeks** | `rainfall_roll_sum_4w` |

### Feature Importance Categories

```
Category               Features                            Role
─────────────────────────────────────────────────────────────────
Rainfall Lags          rainfall_lag_1w to _4w             Core predictor
Rolling Stats          roll_mean_2w, roll_sum_4w           Breeding saturation
Temperature Lags       avg_temp_lag_1w to _3w             Climate suitability
Humidity Lags          humidity_lag_1w to _3w             Mosquito survival
Interactions           rain×waterlog, rain×unsanitary     Amplification risk
Static Ward            density, waterlog, sanitation       Structural risk
Calendar               is_monsoon, sin/cos_week            Seasonality
Derived                vector_climate_suitability         Ecological index
```

---

## 4. ML Model Selection

### Chronological Split Rationale

**Why NOT random split?**

Random splits on time-series data cause **data leakage**:
- Future observations end up in the training set
- Model learns future patterns, inflating test accuracy
- Performance estimates become meaningless

**Chronological split ensures:**
- Model only learns from the past
- Test set represents a realistic "future" deployment scenario
- Results are honest and deployable

```
Timeline:
2016      2017      2018  ...  2023      2024      2025
  │─────────────────────────────│──────────────────│
  │          TRAIN (80%)        │   TEST (20%)      │
  │       416 wks × 60 wards    │  104 wks × 60 wards │
  │        24,960 samples       │   6,240 samples  │
```

### Model Comparison

| Model | MAE ↓ | RMSE ↓ | R² ↑ | Tier Acc ↑ | Selected |
|-------|--------|---------|------|-----------|---------|
| Ridge Baseline | 1.057 | 1.858 | 0.768 | 79.81% | ❌ |
| RandomForest | 0.868 | 1.631 | 0.822 | 84.92% | ❌ |
| **HistGradientBoosting** | **0.827** | **1.554** | **0.838** | **85.59%** | ✅ |

### Why HistGradientBoosting?

1. **Best metrics** across MAE, RMSE, R², and Tier Accuracy
2. **Native missing value handling** — no imputation needed for lag burn-in
3. **Built-in regularization** — reduces overfitting on small ward subsets
4. **Fast training** — histogram-based gradient boosting is memory efficient
5. **Scikit-learn native** — zero additional dependencies

---

## 5. Risk Tier Classification

### Dynamic Quantile Thresholds

Thresholds are computed from the **training set distribution** to handle the high proportion of zero cases:

```python
q_low  = training_data.quantile(0.50)  # ~1.5 cases
q_med  = training_data.quantile(0.75)  # ~4.0 cases
q_high = training_data.quantile(0.90)  # ~10.0 cases
```

| Tier | Threshold | Epidemiological Meaning |
|------|-----------|------------------------|
| Low | < 1.5 cases/week | Sporadic baseline — standard monitoring |
| Medium | 1.5 – 4.0 | Emerging vector activity — alert mode |
| High | 4.0 – 10.0 | Active local outbreak — containment |
| Critical | ≥ 10.0 | Epidemic surge — emergency response |

---

## 6. Confidence Intervals

**Methodology:** ±1.5 × MAE (documented approximation)

```
CI_lower = max(0, predicted_cases − 1.5 × MAE)
CI_upper = predicted_cases + 1.5 × MAE
```

**Rationale:** With MAE = 0.827 and approximately normal residuals, multiplying by 1.5 approximates an 80–90% coverage interval. This is an engineering approximation, NOT a formal bootstrap CI. Disclosed as such in the UI.

---

## 7. Backend Architecture (FastAPI)

```
api.py startup:
1. Load CSV → clean → feature_engineer (cached as global DataFrames)
2. Load model artifact (cached)
3. Run predictions on latest week per ward (cached)
4. Ready to serve requests

Request handling (all in-memory, no disk I/O on each request):
GET /api/predict → lookup precomputed or run model.predict() 
GET /api/ward/{id} → filter global DataFrame, serialize
GET /api/environmental → compute correlations from global df
```

---

## 8. Cost Efficiency

| Factor | Implementation | Cost |
|--------|---------------|------|
| Inference | Pre-loaded joblib model, <10ms | $0 |
| Training | Local CPU, ~30 seconds | $0 |
| External APIs | None | $0 |
| LLMs | None | $0 |
| Cloud | None — fully local | $0 |
| Caching | @st.cache_data + @st.cache_resource | $0 |
| **Total** | | **$0** |

---

## 9. Frontend Architecture (Streamlit Multi-Page)

```
app.py (Main Dashboard)
   └── pages/
       ├── 01_Risk_Map.py         → /api/wards
       ├── 02_Outbreak_Prediction.py → /api/predict, /api/ward/{id}
       ├── 03_Weather_Monitoring.py  → /api/weather/{ward_id}
       ├── 04_Ward_Comparison.py     → /api/comparison
       ├── 05_Model_Performance.py   → /api/metrics
       ├── 06_Environmental_Analysis.py → /api/environmental
       ├── 07_Prevention_Awareness.py   → /api/wards (risk filter)
       └── 08_About_Project.py          → static + /api/metrics
```

Streamlit multi-page apps use the `pages/` directory convention — each file becomes a sidebar navigation entry automatically.

---

## 10. Reproducibility

A fresh setup requires:
```
1. git clone + pip install -r requirements.txt
2. Place dataset in data/
3. python src/train_model.py   (or use pre-saved model)
4. python api.py               (terminal 1)
5. python -m streamlit run app.py  (terminal 2)
```

Deterministic training ensured via `random_state=42` on all models.
