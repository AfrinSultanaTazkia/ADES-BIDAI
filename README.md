# ADES BIDAI (এডিস বিদায়)
### AI-Based Dengue Outbreak Prediction and Alert System

"মশার খবর আগেই, সুরক্ষা থাকবে সাথেই।"

---

## What is ADES BIDAI?

Dengue fever has emerged as one of the most pressing urban public health challenges in Bangladesh. Densely populated metropolitan centers like Dhaka and Chattogram experience severe seasonal outbreaks that overwhelm hospitals, strain medical resources, and endanger lives. Traditional public health responses are largely reactive: vector control teams and fogging operations are usually mobilized only after hospitals report an influx of patients. Because the dengue transmission cycle takes several weeks to develop, responding only after clinical cases peak is often too late to prevent widespread community spread.

ADES BIDAI (meaning "Farewell Aedes") is an artificial intelligence-driven epidemiological surveillance and early-warning platform designed to shift municipal response from reactive treatment to proactive prevention. By analyzing multi-week historical weather patterns, environmental vulnerability factors, and disease surveillance data across 60 urban wards in Bangladesh, the system forecasts dengue outbreak risk 2 to 4 weeks before clinical cases peak.

The system serves multiple stakeholders:

- Municipal City Corporations: Helps city authorities optimize mosquito control logistics by directing larvicide spraying, drain clearance, and fogging crews to high-risk wards weeks in advance.
- Public Health Authorities and Hospitals: Provides hospital administrators with an early outlook on patient loads so they can manage bed capacity, fluid supplies, and diagnostic kits before wards become overwhelmed.
- Community Leaders and Residents: Offers neighborhood-level transparency so citizens can eliminate standing water around their homes and take protective measures before mosquito populations surge.

---

## How Does It Work?

ADES BIDAI translates meteorological and urban environmental signals into actionable public health risk indicators through three core stages:

1. Processing Environmental and Surveillance Data:
The system continuously ingests weekly observations of rainfall, temperature, relative humidity, population density, drainage bottlenecks (water logging risk), and sanitation conditions. Rather than treating each week in isolation, it computes multi-week lagged and rolling metrics to capture how past weather influences present conditions.

2. Estimating Future Outbreak Risk:
The underlying machine learning model evaluates the relationship between past environmental conditions and subsequent dengue case surges. Because Aedes mosquitoes require standing water to lay eggs and dengue virus replication inside the mosquito takes time, rainfall that occurred 2 to 4 weeks prior is far more predictive of case surges than rainfall today. The model generates both an estimated case count and a categorical risk level for each ward.

3. Exploring Ward-Level Risks on the Dashboard:
Users interact with the system through a centralized web dashboard. City health officials can select any monitored city or ward to inspect current spatial risk maps, test weather scenarios using interactive simulation controls, examine multi-week rainfall lag progression, and review the primary environmental drivers responsible for a ward's risk designation.

---

## Main Features

- Interactive Ward-Level Spatial Risk Mapping:
Visualizes all 60 monitored wards across 5 Bangladeshi city corporations on an interactive map. Each ward is color-coded by its predicted risk level (Low, Medium, High, or Critical), allowing decision-makers to immediately spot geographic risk clusters.

- Multi-Week Forward Risk Forecasting:
Provides 2-week and 4-week outbreak forecasts for every ward. These horizons align directly with the biological development timeline of Aedes mosquitoes, giving municipal teams sufficient lead time to intervene before larvae reach adult biting stages.

- Environmental and Weather Scenario Simulation:
Allows users to adjust temperature, rainfall, and relative humidity inputs dynamically using interface controls. Health officials can simulate hypothetical monsoon scenarios—such as an unexpected 50 mm rainfall spike—to assess how sensitive a ward is to weather shifts.

- Multi-Week Weather Lag Progression Analysis:
Tracks the longitudinal relationship between rainfall occurring 1, 2, 3, and 4 weeks prior and subsequent dengue cases. Interactive trend charts clearly illustrate the delayed surge effect for every neighborhood.

- Explainable Risk Driver Attribution:
Every prediction is accompanied by an automated breakdown of the primary factors driving the risk score, such as heavy rainfall 3 weeks prior, severe local drainage blockages, low sanitation ratings, or high residential crowding.

- Multi-Ward Vulnerability Comparison:
Enables side-by-side comparisons of structural risk factors across different wards, helping authorities understand why two adjacent neighborhoods may experience different outbreak intensities under the same weather conditions.

- Local, High-Speed Offline Inference:
Runs entirely on local hardware with zero external API dependencies. Serialized model inference executes in under 15 milliseconds, ensuring continuous availability even in environments with limited internet connectivity.

---

## Dataset and Coverage

ADES BIDAI is built upon a 10-year historical disease surveillance and meteorological dataset covering the period from January 2016 through December 2025.

### Geographic Scope and Breakdown

The dataset encompasses 60 urban wards across 5 major city corporations in Bangladesh, totaling 31,320 weekly observations (522 consecutive weeks per ward):

- Dhaka North City Corporation (DNCC): 20 wards (DNCC_Ward_01 through DNCC_Ward_20), 10,440 records
- Dhaka South City Corporation (DSCC): 20 wards (DSCC_Ward_01 through DSCC_Ward_20), 10,440 records
- Chattogram City Corporation (CCC): 10 wards (CCC_Ward_01 through CCC_Ward_10), 5,220 records
- Gazipur City Corporation (GCC): 5 wards (GCC_Ward_01 through GCC_Ward_05), 2,610 records
- Narayanganj City Corporation (NCC): 5 wards (NCC_Ward_01 through NCC_Ward_05), 2,610 records

### Tracked Features

For every ward-week, the dataset includes:

- Date and Ward Identifiers: Weekly observation date, city name, and ward identifier.
- Meteorological Metrics: Weekly cumulative rainfall (mm), average temperature (°C), maximum and minimum temperatures (°C), and relative humidity (%).
- Static Urban Vulnerability Indicators: Population density (people per sq km), water logging risk index (measuring drainage bottleneck severity), and sanitation score (measuring waste management quality).
- Epidemiological Target: Weekly recorded dengue cases per ward.

---

## How the AI Prediction Works

### Epidemiological Basis and Feature Engineering

Rainfall does not cause an immediate surge in dengue cases on the day it rains. The delay between precipitation and hospital admissions is governed by the biological life cycle of the Aedes aegypti mosquito and the dengue virus:

1. Water Accumulation and Larval Emergence (Days 0 to 14): Stagnant water pools create breeding sites. Eggs hatch into larvae and develop into adult mosquitoes over 7 to 14 days.
2. Blood Feeding and Viral Incubation (Days 14 to 26): Adult female mosquitoes take blood meals from infected individuals. The virus undergoes extrinsic incubation within the mosquito for 8 to 12 days before the mosquito becomes infectious.
3. Human Incubation to Clinical Admission (Days 26 to 33): After an infectious bite, human intrinsic incubation takes 4 to 7 days before symptoms become severe enough to require medical attention.

Because of this 3 to 4-week chain, the feature engineering pipeline constructs:

- Multi-Week Rainfall Lags: Individual rainfall values shifted by 1, 2, 3, and 4 weeks per ward without looking forward in time.
- Multi-Week Temperature and Humidity Lags: Lags across 1, 2, and 3 weeks to capture thermal conditions influencing vector survival.
- Rolling Precipitation Metrics: 2-week and 4-week rolling sums and means to measure cumulative breeding pool saturation.
- Vulnerability Interaction Terms: Products of rainfall lags with drainage bottlenecks and poor sanitation, reflecting how stagnant water persists longer in underserved areas.
- Vector Climate Suitability Index: A composite Gaussian temperature suitability curve paired with a logistic humidity threshold.
- Seasonality Encodings: Monsoon indicator flags and cyclical sine-cosine transformations of week and month.

### Model Selection: HistGradientBoosting

Three distinct modeling approaches were evaluated on the dataset:

1. Ridge Regression: A linear regularized baseline. It achieved an MAE of 1.057, an RMSE of 1.858, and an R-squared of 0.768, with a risk tier accuracy of 79.81%. Because dengue dynamics involve sharp biological thresholds (temperatures above which mosquitoes breed rapidly and below which viral incubation halts), linear assumptions struggle during sudden seasonal transitions.
2. Random Forest Regressor: An ensemble of decision trees. It achieved an MAE of 0.868, an RMSE of 1.631, an R-squared of 0.822, and a risk tier accuracy of 84.92%. While accurate, its larger serialized file size and higher memory footprint made it less suitable for instant local deployment.
3. HistGradientBoosting Regressor (Selected): Scikit-learn's histogram-based gradient boosting algorithm. It achieved the best overall performance with an MAE of 0.827, an RMSE of 1.554, an R-squared of 0.838, and a risk tier accuracy of 85.59%.

HistGradientBoosting was chosen because it natively handles non-linear vector thresholds, offers built-in regularized tree growth to avoid overfitting on smaller ward subsets, executes sub-15-millisecond inference, and requires no external heavy runtime dependencies.

### Chronological Validation Strategy

In disease forecasting, random train-test splits (shuffling rows across time) create severe data leakage. If a model is trained on data from Wednesday, tested on Tuesday, and trained on Thursday of the same outbreak season, it learns future patterns and displays artificially inflated accuracy that collapses in real-world deployment.

To prevent leakage, ADES BIDAI uses a strict chronological split:

- Training Set (2016–2023): The model learns solely from historical data spanning January 2016 to December 2023 (80% of the dataset, 24,960 records).
- Holdout Test Set (2024–2025): The model is evaluated strictly on the future two years from January 2024 to December 2025 (20% of the dataset, 6,240 records).

Testing on an entirely unseen future time window ensures that reported metrics reflect how the system would perform if deployed in the real world.

### Benchmark Evaluation Results

| Model | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | R-Squared (R²) | Risk Tier Classification Accuracy | Status |
|---|---|---|---|---|---|
| Ridge Baseline | 1.057 | 1.858 | 0.768 | 79.81% | Baseline |
| Random Forest | 0.868 | 1.631 | 0.822 | 84.92% | Evaluated |
| HistGradientBoosting | 0.827 | 1.554 | 0.838 | 85.59% | Selected Winner |

Understanding the metrics:
- An MAE of 0.827 means that across all test weeks, the model's case prediction deviated from actual hospital admissions by an average of less than 1 patient per ward.
- The 85.59% accuracy represents risk-tier classification accuracy: how correctly the system categorizes unseen weeks into Low, Medium, High, or Critical threat levels.

---

## Understanding Dengue Risk Levels

Rather than expecting municipal teams to interpret raw statistical probabilities, ADES BIDAI classifies predictions into four standardized public health risk tiers.

The thresholds are derived mathematically from the distribution of historical cases (the 50th, 75th, and 90th percentiles of the training data):

- Low Risk (Fewer than 1.5 cases per week):
Represents baseline or sporadic mosquito activity. No active outbreak is detected. Municipal teams maintain standard routine monitoring and general citizen awareness.

- Medium Risk (1.5 to 4.0 cases per week):
Indicates emerging vector activity and localized breeding site formation. Health authorities should issue early warnings to ward sanitation inspectors and conduct targeted inspections of construction sites and unmanaged drainage canals.

- High Risk (4.0 to 10.0 cases per week):
Signifies an active local outbreak surge. Municipalities should immediately deploy targeted larvicide treatment, clear drainage blockages, and schedule evening fogging in identified transmission pockets.

- Critical Risk (10.0 or more cases per week):
Represents a severe epidemic surge. Triggers emergency municipal coordination, city-wide clean-up campaigns, mobilization of fever clinics, and alerts to nearby hospital emergency departments to expand bed capacity.

---

## Technology Behind the Project

Each component of the technology stack was chosen for reliability, execution speed, and independence from external paid services:

- Python: The foundational programming language used for data ingestion, feature generation, model training, and web services.
- Scikit-learn: Powers the machine learning pipeline, including model training, regularized gradient boosting, chronological validation, and metric scoring.
- Pandas and NumPy: Manages structured tabular manipulation, time-series shifts for multi-week lags, rolling statistics, and numeric transformations.
- FastAPI and Uvicorn: Delivers an asynchronous, high-throughput REST backend that serves model predictions, ward histories, and environmental correlations over HTTP.
- Streamlit: Provides the reactive user interface, rendering interactive dark-slate dashboard views, responsive filter panels, and analytical tabs.
- Plotly and Pydeck: Generates interactive geospatial maps with dark basemaps, dual-axis lag curves, and driver attribution charts.
- Joblib: Handles model serialization and deserialization, enabling instant model loading into memory with zero retraining overhead at runtime.

---

## Running the Project

### Prerequisites

- Python 3.10 or higher (compatible with Python 3.10 through 3.14)
- Git and pip package manager

### 1. Clone the Repository

```bash
git clone https://github.com/AfrinSultanaTazkia/ADES-BIDAI.git
cd ADES-BIDAI
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Dataset Placement

The surveillance dataset is already included in the repository at:
`data/google_sheet_dengue_dataset.csv`

### 4. Launching the System

#### Option A: One-Click Startup (Windows)
Double-click `run.bat` in the repository root. This script configures environment threads and launches the Streamlit surveillance dashboard on port 8501.

#### Option B: Full Stack Launch (Recommended for API + Frontend)

Open two terminal windows:

Terminal 1 - Start the FastAPI Backend:
```bash
python api.py
```
The API starts at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

Terminal 2 - Start the Streamlit Dashboard:
```bash
streamlit run app.py --server.port 8501
```
The dashboard opens in your browser at `http://localhost:8501`.

#### Option C: Dashboard-Only Mode (Local Fallback)

If you only wish to view and interact with the user interface without running the API server:
```bash
streamlit run app.py
```
The dashboard automatically detects that the API is offline and falls back to loading data and precomputed metrics directly from the local files.

#### Optional: Retraining the Model

To retrain the model from scratch on the dataset:
```bash
python src/train_model.py
```
This script executes the chronological split, trains Ridge, Random Forest, and HistGradientBoosting models, selects the best performer, and writes the updated model artifact and metrics to the `models/` directory.

---

## Understanding the Results and Limitations

To maintain scientific integrity and prevent over-reliance on automated systems, users should understand the following operational constraints:

- Predictions Are Estimates, Not Guarantees:
Machine learning models identify probabilistic trends based on past observations. Actual case counts can be influenced by unrecorded interventions, such as sudden neighborhood-wide cleanups, changes in resident behaviors, or variations in hospital reporting rates.

- Historical Surveillance Constraints:
The model is trained on historical data from 2016 through 2025 across five Bangladeshi urban centers. It is calibrated specifically for urban Bangladeshi climate patterns and municipal infrastructure; it is not intended for direct application to rural areas or other countries without recalibration.

- No Live Meteorological Integration:
The current implementation runs on historical records and interactive user-specified scenario simulations. It does not pull automated real-time feeds from live weather APIs. Future production phases could incorporate automated weather feed connections.

- Centroid-Based Ward Coordinates:
Because official ward boundary GeoJSON shapefiles were not openly available for all 60 wards, the dashboard visualizes wards using geographic centroid coordinates rather than multi-polygon boundaries.

- Approximate Confidence Intervals:
The dashboard displays confidence bounds calculated using an empirical factor based on the model's test MAE (approximately plus or minus 1.5 times MAE, adjusted for forecast horizon). These serve as useful operational ranges for decision-makers rather than formal bootstrap intervals.

---

## API Access

The FastAPI backend provides 10 structured REST endpoints for programmatic access:

| HTTP Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Returns service health status and current UTC server time. |
| GET | `/api/summary` | Delivers aggregate platform KPIs including total recorded cases, ward count, latest observation date, average climate conditions, and active high or critical ward counts. |
| GET | `/api/wards` | Lists all 60 wards with geographic coordinates, locality name, city corporation, latest predicted cases, and assigned risk tier. |
| GET | `/api/ward/{ward_id}` | Returns comprehensive details for a specific ward, including 2-week and 4-week forecasts with confidence intervals, 12-week historical trend, current environmental indicators, and identified risk drivers. |
| GET | `/api/predict` | Generates a forward prediction for a given `ward_id` and configurable `horizon` (in weeks, between 1 and 12). |
| GET | `/api/weather/{ward_id}` | Supplies the last 4 weeks of meteorological observations and lagged precipitation values for the specified ward. |
| GET | `/api/metrics` | Returns out-of-sample evaluation metrics (MAE, RMSE, R², and Risk Tier Accuracy) for all candidate models from the test period. |
| GET | `/api/historical` | Provides weekly aggregated dengue cases across all monitored wards for a configurable lookback window (default: 52 weeks). |
| GET | `/api/comparison` | Accepts a comma-separated list of ward IDs (for example, `?wards=DNCC_Ward_01,DSCC_Ward_05`) and returns side-by-side environmental and risk metrics. |
| GET | `/api/environmental` | Returns Pearson correlation coefficients, sampled environmental scatter data, and monthly case averages for epidemiological analysis. |

Full interactive API documentation with request schemas and test consoles is available at `http://localhost:8000/docs` whenever the backend is running.

---

## Project Structure

```
ADES-BIDAI/
|-- app.py                     Main Streamlit dashboard interface and visualization tabs
|-- api.py                     FastAPI REST backend serving predictions and surveillance endpoints
|-- run.bat                    One-click launch script for Windows environments
|-- requirements.txt           Python package dependencies
|-- README.md                  Project documentation and operational guide
|-- ARCHITECTURE.md            In-depth system and epidemiological data flow documentation
|-- data/
|   |-- google_sheet_dengue_dataset.csv    Official 10-year surveillance dataset (31,320 rows)
|   |-- dashboard_precomputed.json         Cached ward aggregates for instantaneous dashboard startup
|-- models/
|   |-- dengue_outbreak_model.joblib       Serialized HistGradientBoosting model artifact
|   |-- metrics_summary.json               Benchmark evaluation results across candidate models
|-- src/
|   |-- data_processing.py     Dataset loading, column standardization, and cleaning routines
|   |-- feature_engineering.py Multi-week lag generator, rolling statistics, and vulnerability terms
|   |-- train_model.py         Chronological train-test splitting and model benchmark evaluation
|   |-- prediction.py          High-speed local inference engine and risk driver extraction
`-- utils/
    `-- ward_coordinates.py    Geographic centroid coordinates and localities for all 60 wards
```

---

## AI Disclosure and Responsible Use

ADES BIDAI was built with an emphasis on transparency, reproducibility, and safety:

- Local Machine Learning Architecture: The prediction engine relies strictly on a local scikit-learn HistGradientBoosting regressor. No external Large Language Models (LLMs) or generative AI APIs are used to produce case forecasts or risk levels.
- Zero Inference API Cost: All computations, feature transformations, and inferences run locally on the host machine. The system does not incur token charges, subscription fees, or cloud computation costs during operation.
- Purpose and Clinical Boundaries: This platform is designed exclusively as an epidemiological surveillance and municipal decision-support system. It is intended to assist public health authorities in prioritizing vector control measures and raising community awareness. It is not a clinical diagnostic tool, does not handle patient health records, and should never be used to replace professional medical advice.
