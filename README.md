# 🦟 ADES BIDAI: AI-Powered Urban Dengue Outbreak Surveillance

> **Hackathon Phase 1: 24-Hour Remote Qualifier**  
> **Challenge**: AI for Urban Dengue Outbreak Early-Warning System  
> **Team**: ADES BIDAI  

---

## 🌟 Overview

Dengue outbreaks overwhelm hospitals in Dhaka and Chattogram every year because mosquito control is traditionally reactive—deploying spraying teams only after hospital admissions surge.

**ADES BIDAI** bridges the **2-to-4-week vector breeding clock**. Stagnant rainwater trapped in drainage bottlenecks takes 7 to 14 days for *Aedes aegypti* eggs to mature into adult mosquitoes, followed by viral incubation and human symptom onset. By programmatically ingesting weather metrics, computing multi-week grouped lags, and factoring in hyper-local ward vulnerabilities (drainage bottlenecks, sanitation, crowding), ADES BIDAI gives municipal health officers an actionable **2-to-4-week early-warning window** to target high-risk wards *before* outbreaks peak.

---

## 🚀 Reproducible Local Setup (Launch in ≤ 3 Minutes)

### Prerequisites
- Python 3.10+ (Tested on Python 3.10, 3.11, 3.12, 3.14)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/AfrinSultanaTazkia/ADES-BIDAI.git
cd ADES-BIDAI
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit Dashboard
```bash
streamlit run app.py
```
The interactive surveillance dashboard will immediately open in your browser at:
`http://localhost:8501`

---

## 📁 Project Architecture & Structure

```text
ADES-BIDAI/
├── data/
│   ├── google_sheet_dengue_dataset.csv   # Longitudinal dataset (31,320 rows, 60 wards, 10 years)
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── data_processing.py                # Dataset loading, cleaning, validation & date parsing
│   ├── feature_engineering.py            # Multi-week weather lags (1-4w), rolling sums, vulnerability terms
│   ├── train_model.py                    # Chronological validation split (2016-23 / 2024-25), model benchmarking
│   └── prediction.py                     # Serialized local inference engine & dynamic quantile risk tiering
├── models/
│   ├── dengue_outbreak_model.joblib      # Serialized production model artifact (< 8ms inference)
│   ├── metrics_summary.json              # Out-of-time evaluation benchmark results
│   └── .gitkeep
├── utils/
│   ├── __init__.py
│   └── .gitkeep
├── assets/
│   └── .gitkeep
├── app.py                                # Full Streamlit Web Dashboard with driver breakdown & lag chart
├── requirements.txt                      # Pinned production dependencies
├── README.md                             # Setup guide, technical documentation & AI disclosure
├── ARCHITECTURE.md                       # Comprehensive system architecture & data flow specification
└── .gitignore                            # Clean Git configuration
```

---

## 🔬 Machine Learning Pipeline & Out-of-Time Performance

### Chronological Train-Test Split (Zero Lookahead Leakage)
To prevent temporal data leakage inherent in randomized cross-validation, the model was evaluated on a strictly chronological holdout test set:
- **Training Period**: `2016-02-01` to `2023-12-25` (24,780 records; 8 full years)
- **Holdout Validation Period**: `2024-01-01` to `2025-12-29` (6,300 records; 2 full unseen years)

### Benchmark Comparison on Unseen 2024–2025 Data

| Model Candidate | MAE (Cases) | RMSE | \(R^2\) Score | Risk Tier Accuracy (%) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Ridge Regression (Baseline)** | 1.057 | 1.858 | 0.768 | 79.81% | Linear Baseline |
| **Random Forest Regressor** | 0.868 | 1.631 | 0.822 | 84.92% | Ensemble Tree |
| 🏆 **HistGradientBoosting** | **0.827** | **1.554** | **0.838** | **85.59%** | **Selected Production Model** |

- **Average Prediction Error (MAE)**: Only **0.827 cases** (less than 1 patient per ward).
- **Variance Explained (\(R^2\))**: **83.8%** on unseen future years.
- **Risk Tier Accuracy**: **85.59%** across Low, Medium, High, and Critical alert categories.

---

## 🎯 Public Health Operational Risk Tiers

Risk tiers are dynamically mapped using training distribution quantiles:

| Tier | Predicted Cases | Municipal Public Health Response Protocol |
| :---: | :---: | :--- |
| 🟢 **LOW** | `< 1.5` | Baseline routine surveillance; standard household awareness |
| 🟡 **MEDIUM** | `1.5 – 3.9` | Targeted larvicide application in known drainage hot-spots |
| 🟠 **HIGH** | `4.0 – 9.9` | Coordinated neighborhood fogging & hospital bed capacity staging |
| 🔴 **CRITICAL** | `≥ 10.0` | Emergency epidemic cluster alert; emergency saline & testing mobilization |

---

## 💡 Compute & Cost Efficiency Highlights (Criterion 6)

1. **Serialized Local Inference**: Pre-trained model artifact serialized via `joblib.dump()`. UI startup and prediction take **< 8 ms** with zero in-app retraining overhead.
2. **Double-Layered Caching**:
   - `@st.cache_resource` for the model artifact.
   - `@st.cache_data` for precomputed feature tables.
3. **Zero External API Costs**: 100% self-contained local compute. No external weather or LLM billing dependencies during routine surveillance operations.

---

## 🤖 AI Assistants & External Tool Disclosure (Criterion 8)

In full compliance with **Evaluation Criterion 8 (Git History & AI Disclosure)**, below is the transparent disclosure of AI assistance and external tools utilized during the 24-hour hackathon build:

- **AI Coding Assistant**: Google Antigravity / Gemini CLI was utilized for code scaffolding, boilerplate generation, architecture diagram drafting in Mermaid, and documentation formatting.
- **External APIs**: **Zero** external paid commercial APIs were consumed during development or runtime. All computation, training, and inference occur 100% locally.
- **Open-Source Libraries**: Python, Pandas, NumPy, Scikit-Learn, Joblib, Streamlit, and Plotly.

---

*Developed for the AI for Urban Dengue Outbreak Challenge 2026.*
