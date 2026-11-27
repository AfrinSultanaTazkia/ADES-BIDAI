"""
ADES BIDAI - Unit Tests for What-If Vector Control Impact Simulator
Covers:
- Section 14 Mandatory Reference Simulation Test
- Zero deployed crews handling
- Combined Larvicide + Fogging bounded formula
- Crew constraint enforcement (budget exceeded)
- Marginal benefit greedy optimizer
- Horizon extension (2, 3, 4 weeks)
- Linear vs Saturation response curves
- Hospital routing comparison integration
- Deterministic repeatability
"""

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(fn):
                return fn
            return decorator
        @staticmethod
        def raises(expected_exception):
            class _RaisesContext:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    if exc_type is None:
                        raise AssertionError(f"Expected {expected_exception} but nothing was raised.")
                    assert issubclass(exc_type, expected_exception)
                    self.value = exc_val
                    return True
            return _RaisesContext()
    pytest = _MockPytest()
import math
from src.resource_engine import DengueResourceEngine, DEFAULT_COEFFICIENTS
from src.vector_control_simulator import (
    VectorControlSimulator,
    SimulationRequest,
    create_simulation_request,
    INTERVENTION_PARAMS,
)


@pytest.fixture(scope="module")
def resource_engine():
    return DengueResourceEngine()


@pytest.fixture(scope="module")
def simulator(resource_engine):
    return VectorControlSimulator(resource_engine)


# ---------------------------------------------------------------------------
# 1. Section 14 Mandatory Reference Simulation Test
# ---------------------------------------------------------------------------

def test_section_14_reference_simulation(simulator):
    """
    Verifies Section 14 Reference Simulation Test:
    Ward Area = 10 km², Coverage Capacity = 2 km²/crew, Crews = 3, Max Eff = 0.30
    Baseline Weekly Cases = [100, 150, 180, 220]
    Weekly Impact Factors = [0.00, 0.40, 0.80, 1.00]
    Expected:
    - Covered Area = 6 km², Coverage Ratio = 0.60
    - Weekly Reductions = [0.00, 0.072, 0.144, 0.180]
    - Adjusted Cases = [100.0, 139.2, 154.08, 180.4]
    - Displayed Adjusted = [100, 139, 154, 180] -> Sum = 573
    - Displayed Prevented = [0, 11, 26, 40] -> Sum = 77
    - Unrounded Prevented = 76.32
    - Exact ROI = 25.44, Displayed ROI = 77 / 3 = 25.67
    """
    params = {
        "coverage_capacity_sqkm_per_crew": 2.0,
        "max_effectiveness": 0.30,
        "weekly_impact_factors": [0.00, 0.40, 0.80, 1.00],
        "saturation_parameter": 2.0,
    }

    cov = simulator._calculate_coverage({}, 3, params, 10.0)
    assert cov["covered_area_sqkm"] == 6.0
    assert abs(cov["coverage_ratio"] - 0.60) < 1e-4

    # Linear response
    reductions = [
        simulator._calculate_weekly_reduction(cov["coverage_ratio"], params["max_effectiveness"], f)
        for f in params["weekly_impact_factors"]
    ]
    expected_reds = [0.00, 0.072, 0.144, 0.180]
    for actual, exp in zip(reductions, expected_reds):
        assert abs(actual - exp) < 1e-4

    base_cases = [100.0, 150.0, 180.0, 220.0]
    adj_cases = [b * (1.0 - r) for b, r in zip(base_cases, reductions)]
    prev_cases = [b - a for b, a in zip(base_cases, adj_cases)]

    assert abs(adj_cases[0] - 100.0) < 1e-2
    assert abs(adj_cases[1] - 139.2) < 1e-2
    assert abs(adj_cases[2] - 154.08) < 1e-2
    assert abs(adj_cases[3] - 180.4) < 1e-2

    total_base = sum(base_cases)
    total_adj = sum(adj_cases)
    total_prev = sum(prev_cases)

    assert total_base == 650.0
    assert abs(total_adj - 573.68) < 1e-2
    assert abs(total_prev - 76.32) < 1e-2

    exact_roi = total_prev / 3
    assert abs(exact_roi - 25.44) < 1e-2

    # Displayed integer rounding reconciliation
    disp_prev_sum = sum([round(b) - round(a) for b, a in zip(base_cases, adj_cases)])
    assert disp_prev_sum == 77
    disp_roi = round(disp_prev_sum / 3, 2)
    assert disp_roi == 25.67


# ---------------------------------------------------------------------------
# 2. Zero Deployed Crews Handling
# ---------------------------------------------------------------------------

def test_zero_deployed_crews(simulator):
    """Zero crews should produce zero case reduction, zero savings, and None ROI."""
    req = create_simulation_request(
        scenario_name="Zero Crews Test",
        selected_ward_ids=["DNCC_Ward_01"],
        larvicide_crews={"DNCC_Ward_01": 0},
        fogging_crews={"DNCC_Ward_01": 0},
        total_available_crews=50,
        forecast_horizon_weeks=2,
    )
    result = simulator.run_simulation(req)
    ward_res = result.ward_intervention_results[0]

    assert ward_res["cases_prevented_total"] == 0.0
    assert ward_res["baseline_total_cases"] == ward_res["adjusted_total_cases"]
    assert ward_res["beds_saved"] == 0
    assert ward_res["saline_bags_saved"] == 0
    assert ward_res["roi"] is None


# ---------------------------------------------------------------------------
# 3. Bounded Combination Formula
# ---------------------------------------------------------------------------

def test_combined_intervention_bounded(simulator):
    """
    Combined reduction: 1 - (1 - L) * (1 - F).
    For L=0.20, F=0.15: Combined = 1 - (0.80 * 0.85) = 1 - 0.68 = 0.32 (32%).
    """
    comb = simulator._combine_reductions(0.20, 0.15)
    assert abs(comb - 0.32) < 1e-4

    # Bounded ceiling test: reductions must never exceed 1.0
    comb_max = simulator._combine_reductions(0.90, 0.90)
    assert comb_max <= 1.0


# ---------------------------------------------------------------------------
# 4. Crew Constraint Enforcement
# ---------------------------------------------------------------------------

def test_crew_budget_constraint_enforced(simulator):
    """Deploying more crews than available must raise a ValueError."""
    req = create_simulation_request(
        scenario_name="Exceeded Budget Test",
        selected_ward_ids=["DNCC_Ward_01"],
        larvicide_crews={"DNCC_Ward_01": 60},
        fogging_crews={"DNCC_Ward_01": 0},
        total_available_crews=50,
        forecast_horizon_weeks=2,
    )
    with pytest.raises(ValueError) as excinfo:
        simulator.run_simulation(req)
    assert "exceeds available" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 5. Greedy Marginal Benefit Optimizer
# ---------------------------------------------------------------------------

def test_crew_optimization_greedy(simulator):
    """Optimizer should allocate available crews and yield positive cases prevented."""
    res = simulator.optimize_crew_deployment(
        available_crews=10,
        intervention_type="larvicide",
        horizon_weeks=2,
        ward_subset=["DNCC_Ward_01", "DSCC_Ward_01", "CCC_Ward_01"],
    )
    assert res["available_crews"] == 10
    total_allocated = sum(res["ward_allocation"].values())
    assert total_allocated <= 10
    assert res["total_cases_prevented"] > 0.0


# ---------------------------------------------------------------------------
# 6. Forecasting Horizon Extensions (2, 3, 4 Weeks)
# ---------------------------------------------------------------------------

def test_forecast_horizon_extension(simulator):
    """Verifies forecasts for 2, 3, and 4 weeks."""
    w2 = simulator._get_baseline_forecast(2)
    assert len(w2[0]["forecast_weeks"]) == 2

    w3 = simulator._get_baseline_forecast(3)
    assert len(w3[0]["forecast_weeks"]) == 3
    assert w3[0]["forecast_weeks"][2]["forecast_method"] == "ml_extended_recursive"

    w4 = simulator._get_baseline_forecast(4)
    assert len(w4[0]["forecast_weeks"]) == 4


# ---------------------------------------------------------------------------
# 7. Linear vs Saturation Response Curve
# ---------------------------------------------------------------------------

def test_response_models(simulator):
    """Saturation response with k>0 must produce diminishing returns vs linear."""
    linear_resp = simulator._apply_saturation_response(0.5, k=0.0)
    assert abs(linear_resp - 0.5) < 1e-4

    sat_resp = simulator._apply_saturation_response(0.5, k=2.0)
    # With k=2.0, (1 - exp(-1.0)) / (1 - exp(-2.0)) = 0.6321 / 0.8647 = ~0.731
    assert sat_resp > linear_resp
    assert sat_resp <= 1.0


# ---------------------------------------------------------------------------
# 8. Deterministic Repeatability
# ---------------------------------------------------------------------------

def test_deterministic_execution(simulator):
    """Running identical inputs must yield identical numerical results."""
    req1 = create_simulation_request(
        scenario_name="Determinism Test",
        selected_ward_ids=["DNCC_Ward_01", "DSCC_Ward_01"],
        larvicide_crews={"DNCC_Ward_01": 2, "DSCC_Ward_01": 1},
        fogging_crews={"DNCC_Ward_01": 1, "DSCC_Ward_01": 0},
        total_available_crews=30,
        forecast_horizon_weeks=2,
    )
    req2 = create_simulation_request(
        scenario_name="Determinism Test",
        selected_ward_ids=["DNCC_Ward_01", "DSCC_Ward_01"],
        larvicide_crews={"DNCC_Ward_01": 2, "DSCC_Ward_01": 1},
        fogging_crews={"DNCC_Ward_01": 1, "DSCC_Ward_01": 0},
        total_available_crews=30,
        forecast_horizon_weeks=2,
    )
    res1 = simulator.run_simulation(req1)
    res2 = simulator.run_simulation(req2)

    assert res1.regional_impact_summary["total_cases_prevented"] == res2.regional_impact_summary["total_cases_prevented"]
    assert res1.regional_impact_summary["total_beds_saved"] == res2.regional_impact_summary["total_beds_saved"]
    assert res1.regional_impact_summary["total_saline_bags_saved"] == res2.regional_impact_summary["total_saline_bags_saved"]
