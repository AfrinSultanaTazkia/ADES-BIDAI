# ADES BIDAI (এডিস বিদায়)
### AI-Based Dengue Outbreak Prediction and Alert System

"মশার খবর আগেই, সুরক্ষা থাকবে সাথেই।"

---

## What is ADES BIDAI?

Dengue fever has emerged as one of the most pressing urban public health challenges in Bangladesh. Densely populated metropolitan centers like Dhaka North, Dhaka South, Chattogram, Gazipur, and Narayanganj experience severe seasonal outbreaks that overwhelm hospitals, strain medical supply chains, and endanger lives. Traditional public health responses are largely reactive: vector control teams and fogging operations are usually mobilized only after hospitals report an influx of patients. Because the dengue transmission cycle takes several weeks to develop, responding only after clinical cases peak is often too late to prevent widespread community spread.

ADES BIDAI (meaning "Farewell Aedes", engineered under the platform codename BLUEPINE) is an artificial intelligence-driven epidemiological surveillance, constrained resource allocation, and hospital surge overflow routing platform. It is designed to shift municipal response from reactive containment to proactive prevention. By analyzing ten years of historical weather patterns, environmental vulnerability factors, and disease surveillance data across 60 urban wards in Bangladesh, the system forecasts dengue outbreak risk 2 to 4 weeks before clinical cases peak, calculates precise supply and bed requirements, and automatically balances patient surges across municipal hospitals.

The platform serves multiple key stakeholders:

- Municipal City Corporations: Helps city health departments optimize mosquito control logistics by directing larvicide spraying, drain clearance, and vector-control crew teams to high-risk wards weeks in advance using marginal benefit optimization.
- Public Health Authorities and Hospitals: Provides hospital administrators with ward-by-ward forecasts of patient loads, saline bag consumption, and diagnostic kit requirements, paired with an automatic same-city overflow routing engine to prevent emergency department gridlock.
- Disaster Management and Field Health Officers: Generates deterministic emergency dispatch orders and field hospital advisories when city-wide bed demand exceeds local healthcare infrastructure capacity.
- Community Leaders and Residents: Offers neighborhood-level transparency so citizens can eliminate standing water around their homes and take protective measures before mosquito populations surge.

---

## How Does It Work?

ADES BIDAI translates meteorological, urban environmental, and clinical signals into actionable public health interventions through four core stages:

1. Processing Environmental and Surveillance Data:
The system continuously ingests weekly observations of rainfall, temperature, relative humidity, population density, drainage bottlenecks (water logging risk), and sanitation conditions across all 60 wards. Rather than treating each week in isolation, it computes multi-week lagged and rolling metrics to capture how past weather influences present conditions.

2. Estimating Future Outbreak Risk:
The underlying machine learning model evaluates the relationship between past environmental conditions and subsequent dengue case surges. Because Aedes mosquitoes require standing water to lay eggs and dengue virus replication inside the mosquito takes time, rainfall that occurred 2 to 4 weeks prior is far more predictive of case surges than rainfall today. The model generates both an estimated case count and a standardized risk level for each ward.

3. Constrained Resource and Vector Crew Optimization:
Forecasted case surges feed directly into a constrained resource allocation engine. The system calculates ward-level requirements for intravenous saline fluids, rapid diagnostic test kits, hospital beds, and vector-control intervention crews based on clinical incidence rates and urban density weighting.

4. Hospital Surge Detection and Cross-Ward Overflow Routing:
When projected hospital bed demand in an overloaded ward exceeds its usable local bed capacity, the system automatically detects the deficit and calculates optimal patient transfer routes to lower-burden wards within the exact same administrative city corporation. Transfers are prioritized by ward vulnerability and assigned to destinations with the lowest current bed utilization, balancing patient load without physically moving hospital beds.

5. Exploring Wards and Coordinating Operations:
Users interact with the system through a centralized web dashboard and REST API. City health officials can inspect spatial risk maps, run interactive surge stress tests, evaluate multi-destination routing matrices, review deterministic dispatch notices, and persist approved intervention plans.

---

## Main Features

- Interactive Ward-Level Spatial Risk Mapping:
Visualizes all 60 monitored wards across 5 Bangladeshi city corporations on an interactive map. Each ward is color-coded by its predicted risk level (Low, Medium, High, or Critical), allowing decision-makers to immediately spot geographic risk clusters.

- Multi-Week Forward Risk Forecasting:
Provides 2-week and 4-week outbreak forecasts for every ward. These horizons align directly with the biological development timeline of Aedes mosquitoes, giving municipal teams sufficient lead time to intervene before larvae reach adult biting stages.

- Hospital Surge and Cross-Ward Overflow Routing:
Automatically identifies overloaded wards where projected concurrent hospital bed demand exceeds usable local capacity. A city-constrained greedy routing algorithm routes overflow patients to lower-burden wards within the same city corporation, prioritizing destinations with the lowest projected bed utilization while strictly enforcing mathematical accounting identities.

- Constrained Medical Supply Allocation Engine:
Calculates ward-level requirements for intravenous saline fluid bags and NS1/IgM rapid diagnostic kits under regional supply constraints. The algorithm guarantees proportional equity during severe material scarcity.

- Vector-Control Crew Optimization:
Assigns municipal larviciding and fogging crews using a marginal benefit greedy algorithm that evaluates ward priority scores and urban density, maximizing epidemiological containment per deployed worker.

- Interactive Surge Stress Simulator:
Enables public health directors to run real-time what-if simulations using adjustable sliders for demand surge multipliers (0.5x to 2.5x), city bed scarcity factors (20% to 100%), and hospitalization ratios (5 to 30 beds per 100 cases).

- Deterministic Dispatch Notices Engine:
Generates five standardized, production-ready operational notices (Source Ward Transfer Orders, Destination Hospital Inbound Alerts, Municipal Authority Summaries, Field Hospital Activation Advisories, and Bilingual Patient Family Notices) without relying on external generative LLM APIs.

- Local SQLite Persistence and Audit Trail:
Maintains an immutable database record of approved hospital routing plans, transfer legs, simulation parameters, and official sign-offs, with complete revalidation capabilities to ensure data integrity.

- Local, High-Speed Offline Execution:
Runs entirely on local hardware with zero external cloud or LLM API dependencies. Model inference executes in under 15 milliseconds, and the complete React dashboard is pre-bundled and served locally via FastAPI.

---

## Dataset and Coverage

ADES BIDAI is built upon a 10-year historical disease surveillance, meteorological, and clinical logistics dataset covering the period from January 2016 through December 2025.

### Geographic Scope and Breakdown

The dataset encompasses 60 urban wards across 5 major city corporations in Bangladesh, totaling 31,320 weekly observations (522 consecutive weeks per ward):

- Dhaka North City Corporation (DNCC): 20 wards (DNCC_Ward_01 through DNCC_Ward_20), 10,440 records
- Dhaka South City Corporation (DSCC): 20 wards (DSCC_Ward_01 through DSCC_Ward_20), 10,440 records
- Chattogram City Corporation (CCC): 10 wards (CCC_Ward_01 through CCC_Ward_10), 5,220 records
- Gazipur City Corporation (GCC): 5 wards (GCC_Ward_01 through GCC_Ward_05), 2,610 records
- Narayanganj City Corporation (NCC): 5 wards (NCC_Ward_01 through NCC_Ward_05), 2,610 records

### Tracked Features

For every ward-week, the dataset records:

- Date and Ward Identifiers: Weekly observation date, city name, and standardized ward code.
- Meteorological Metrics: Weekly cumulative rainfall (mm), average temperature (°C), maximum and minimum temperatures (°C), and relative humidity (%).
- Static Urban Vulnerability Indicators: Population density (people per sq km), water logging risk index (measuring drainage bottleneck severity), and sanitation score (measuring waste management quality).
- Clinical and Logistics Metrics: Weekly recorded dengue cases, required intravenous saline bags, diagnostic kits needed, and concurrent hospital bed requirements.

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
Represents a severe epidemic surge. Triggers emergency municipal coordination, city-wide clean-up campaigns, mobilization of fever clinics, and alerts to nearby hospital emergency departments to activate cross-ward overflow routing.

---

## Technology Behind the Project

Each component of the technology stack was chosen for reliability, execution speed, and complete offline capability:

- Python: The foundational programming language used for data ingestion, feature generation, model training, optimization engines, and backend web services.
- Scikit-learn: Powers the machine learning pipeline, including model training, regularized gradient boosting, chronological validation, and metric scoring.
- Pandas and NumPy: Manages structured tabular manipulation, time-series shifts for multi-week lags, rolling statistics, and numeric transformations.
- FastAPI and Uvicorn: Delivers an asynchronous, high-throughput REST backend that serves model predictions, resource allocations, hospital routing matrices, and static UI bundles.
- React.js + Vite: Powers the responsive Government Admin Dashboard, compiled into pre-bundled offline static assets.
- Tailwind CSS: Provides a modern, accessible interface styling system.
- Recharts: Renders dynamic SVG hospital capacity charts, demand-vs-capacity comparisons, and before-and-after utilization trends.
- Streamlit: Supplies an alternative rapid-prototyping interface for exploratory spatial visualization.
- SQLite and SQLAlchemy: Provides local persistence for approved hospital routing plans and audit records with zero database server installation requirements.
- Joblib: Handles model serialization and deserialization, enabling instant model loading into memory with zero retraining overhead at runtime.

---

## Running the Project

### Prerequisites

- Python 3.10 or higher (compatible with Python 3.10 through 3.14)
- Node.js 18+ (only if rebuilding the frontend; pre-bundled assets are included)
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

Confirm that the official surveillance and logistics dataset is present at:
`data/bangladesh_dengue_large_dataset_onsite - bangladesh_dengue_large_dataset.csv` (or `data/google_sheet_dengue_dataset.csv`).

### 4. Launching the System

#### Option A: Unified Local Server (Recommended for All Features)

Launch the FastAPI backend server:
```bash
python api.py
```
This single process serves:
- The full interactive React Government Admin Dashboard at: `http://localhost:8000`
- The interactive REST API documentation (Swagger UI) at: `http://localhost:8000/docs`
- All dengue forecasting, resource allocation, and hospital surge overflow routing endpoints.

#### Option B: Exploratory Streamlit Dashboard

In a separate terminal, launch the Streamlit interface:
```bash
streamlit run app.py --server.port 8501
```
The Streamlit view opens in your browser at `http://localhost:8501`.

#### Option C: One-Click Startup (Windows)
Double-click `run.bat` in the repository root to configure environment threads and start the system.

### 5. Running Automated Verification Tests

The platform includes an automated pytest suite covering model validation, resource allocation constraints, and the hospital overflow routing engine:
```bash
pytest tests/
```
All 39 tests (including the mandatory Chattogram 5-ward benchmark scenario and formal accounting identity assertions) execute locally in under 3 seconds.

---

## Understanding the Results and Limitations

To maintain scientific integrity and prevent over-reliance on automated systems, users should understand the following operational constraints:

- Predictions Are Estimates, Not Guarantees:
Machine learning models identify probabilistic trends based on past observations. Actual case counts can be influenced by unrecorded interventions, such as sudden neighborhood-wide cleanups, changes in resident behaviors, or variations in hospital reporting rates.

- Historical Surveillance Constraints:
The model is trained on historical data from 2016 through 2025 across five Bangladeshi urban centers. It is calibrated specifically for urban Bangladeshi climate patterns and municipal infrastructure; it is not intended for direct application to rural areas or other countries without recalibration.

- No Live Meteorological Integration:
The current implementation runs on historical records and interactive user-specified scenario simulations. It does not pull automated real-time feeds from live weather APIs.

- Same-City Patient Transfer Boundary:
Hospital overflow routing strictly operates within the boundaries of each individual city corporation. It does not route patients between different cities (e.g., from Chattogram to Dhaka), reflecting real-world administrative and transit constraints.

- Centroid-Based Ward Coordinates:
Because official ward boundary GeoJSON shapefiles were not openly available for all 60 wards, the dashboard visualizes wards using geographic centroid coordinates rather than multi-polygon boundaries.

- Approximate Confidence Intervals:
The dashboard displays confidence bounds calculated using an empirical factor based on the model's test MAE (approximately plus or minus 1.5 times MAE, adjusted for forecast horizon). These serve as useful operational ranges for decision-makers rather than formal bootstrap intervals.

---

## API Access

The FastAPI backend provides 16 structured REST endpoints for programmatic access:

| HTTP Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Returns service health status and current UTC server time. |
| GET | `/api/summary` | Delivers aggregate platform KPIs including total recorded cases, ward count, and active risk tiers. |
| GET | `/api/wards` | Lists all 60 wards with geographic coordinates, city corporation, latest predicted cases, and assigned risk tier. |
| GET | `/api/ward/{ward_id}` | Returns comprehensive details for a specific ward, including forecasts, confidence intervals, and risk drivers. |
| GET | `/api/predict` | Generates a forward prediction for a given `ward_id` and configurable `horizon` (1 to 12 weeks). |
| GET | `/api/weather/{ward_id}` | Supplies the last 4 weeks of meteorological observations and lagged precipitation values. |
| GET | `/api/metrics` | Returns out-of-sample evaluation metrics (MAE, RMSE, R², and Risk Tier Accuracy) from the test period. |
| GET | `/api/historical` | Provides weekly aggregated dengue cases across all monitored wards for a configurable lookback window. |
| GET | `/api/comparison` | Accepts a comma-separated list of ward IDs and returns side-by-side environmental and risk metrics. |
| GET | `/api/environmental` | Returns Pearson correlation coefficients, sampled environmental scatter data, and monthly case averages. |
| GET | `/api/hospital-routing/current` | Computes baseline hospital surge detection, cross-ward routing matrices, and accounting balances for all 60 wards. |
| POST | `/api/hospital-routing/simulate` | Executes what-if stress tests with custom surge multipliers, bed scarcity factors, and bed requirement ratios. |
| POST | `/api/hospital-routing/approve` | Formally approves and persists a hospital routing plan into local SQLite storage with official audit notes. |
| GET | `/api/hospital-routing/approved-plans` | Retrieves historical approved hospital routing plans and their detailed transfer legs. |
| GET | `/api/hospital-routing/notices` | Generates 5 deterministic template-based operational dispatch orders and advisories for a specified city. |
| POST | `/api/hospital-routing/revalidate` | Reloads a stored plan and re-executes all 5 accounting identities to verify historical data integrity. |

Full interactive API documentation with request schemas and test consoles is available at `http://localhost:8000/docs` whenever the backend is running.

---

## Project Structure

```
ADES-BIDAI/
|-- app.py                              Streamlit surveillance and exploratory dashboard
|-- api.py                              FastAPI backend serving REST endpoints and bundling React UI
|-- run.bat                             One-click launch script for Windows environments
|-- requirements.txt                    Python package dependencies
|-- README.md                           Project documentation and operational guide
|-- ARCHITECTURE.md                     In-depth system and epidemiological data flow documentation
|-- data/
|   |-- bangladesh_dengue_large_dataset_onsite - bangladesh_dengue_large_dataset.csv  Official 10-year dataset (31,320 rows)
|   |-- google_sheet_dengue_dataset.csv Historical surveillance records
|   `-- dashboard_precomputed.json      Cached ward aggregates for instantaneous startup
|-- models/
|   |-- dengue_outbreak_model.joblib    Serialized HistGradientBoosting model artifact
|   `-- metrics_summary.json            Benchmark evaluation results across candidate models
|-- src/
|   |-- data_processing.py              Dataset loading, column standardization, and cleaning routines
|   |-- feature_engineering.py          Multi-week lag generator, rolling statistics, and vulnerability terms
|   |-- train_model.py                  Chronological train-test splitting and model benchmark evaluation
|   |-- prediction.py                   High-speed local inference engine and risk driver extraction
|   |-- resource_engine.py              Constrained medical supplies and crew allocation engine
|   |-- hospital_routing.py             Hospital surge detection and cross-ward greedy routing core
|   `-- database.py                     SQLite persistence models, approval workflow, and plan audit
|-- frontend/                           Production React 18 dashboard
|   |-- src/
|   |   |-- App.jsx                     Complete government admin dashboard with hospital surge tab
|   |   `-- main.jsx                    Application entry point
|   |-- dist/                           Compiled static web assets served directly by FastAPI
|   |-- package.json                    Frontend dependencies (Tailwind CSS, Lucide, Recharts)
|   `-- vite.config.js                  Vite bundler configuration
|-- tests/
|   |-- conftest.py                     Test configuration and path resolution
|   |-- test_resource_engine.py         Unit tests for resource allocation and scarcity
|   `-- test_hospital_overflow_routing.py 23 comprehensive tests for hospital surge and routing
`-- utils/
    `-- ward_coordinates.py             Geographic centroid coordinates and localities for all 60 wards
```

---

## AI Disclosure and Responsible Use

ADES BIDAI was built with an emphasis on transparency, reproducibility, and safety:

- Local Machine Learning Architecture: The prediction engine relies strictly on a local scikit-learn HistGradientBoosting regressor. No external Large Language Models (LLMs) or generative AI APIs are used to produce case forecasts or risk levels.
- Zero Cloud API Cost: All computations, feature transformations, resource allocations, and routing optimizations run locally on the host machine. The system does not incur token charges, subscription fees, or cloud computation costs during operation.
- Purpose and Clinical Boundaries: This platform is designed exclusively as an epidemiological surveillance and municipal decision-support system. It is intended to assist public health authorities in prioritizing vector control measures, managing hospital capacity, and raising community awareness. It is not a clinical diagnostic tool, does not handle patient health records, and should never be used to replace professional medical advice.
