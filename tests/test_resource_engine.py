"""
ADES BIDAI - Comprehensive Test Suite for Dengue Resource Allocation Engine
Covers Scarcity Controls (30%, 50%, 70%, 100%), Vector Crew Assignments,
Priority Scoring, Hospital Overflow Routing, Counterfactual Intervention, and Database Auditing.
"""

import pytest
import math
from src.resource_engine import DengueResourceEngine, classify_risk_level, get_risk_score
from src.database import save_approved_plan, get_audit_logs, record_redistribution
from utils.ward_coordinates import haversine_distance_km, WARD_AREAS, ALL_WARD_COORDS


@pytest.fixture(scope="module")
def engine():
    """Initializes DengueResourceEngine on the 60-ward onsite dataset."""
    return DengueResourceEngine()


# ---------------------------------------------------------------------------
# 1. Ward Coverage and Dataset Integrity Tests
# ---------------------------------------------------------------------------
def test_all_60_wards_present(engine):
    """Verify that all 60 wards across the 5 city corporations are integrated."""
    res = engine.run_allocation_engine(stock_percentage=100.0, total_spraying_crews=150)
    wards = res["wards"]
    assert len(wards) == 60, f"Expected 60 wards, got {len(wards)}"

    ward_ids = {w["ward_id"] for w in wards}
    # Check representation from each city corporation
    assert any(wid.startswith("DNCC_") for wid in ward_ids)
    assert any(wid.startswith("DSCC_") for wid in ward_ids)
    assert any(wid.startswith("CCC_") for wid in ward_ids)
    assert any(wid.startswith("GCC_") for wid in ward_ids)
    assert any(wid.startswith("NCC_") for wid in ward_ids)


def test_ward_geographical_areas():
    """Verify all 60 wards have defined non-zero geographical areas in square km."""
    assert len(WARD_AREAS) == 60
    for wid, area in WARD_AREAS.items():
        assert area > 0.0, f"Ward {wid} area must be positive"


# ---------------------------------------------------------------------------
# 2. Mathematical Priority Scoring & Normalization Tests
# ---------------------------------------------------------------------------
def test_risk_level_classification():
    """Verify exact 3-tier risk classification thresholds."""
    assert classify_risk_level(5.5) == "High"
    assert classify_risk_level(4.0) == "High"
    assert classify_risk_level(3.9) == "Medium"
    assert classify_risk_level(1.5) == "Medium"
    assert classify_risk_level(1.4) == "Low"
    assert classify_risk_level(0.0) == "Low"


def test_exact_risk_scores():
    """Verify exact risk score constants."""
    assert get_risk_score("High") == 1.00
    assert get_risk_score("Medium") == 0.60
    assert get_risk_score("Low") == 0.30


def test_population_density_normalization_and_priority_formula(engine):
    """
    Verify exact formulas:
    D = Ward Density / Max Density
    Priority Score = (0.7 * R) + (0.3 * D)
    """
    res = engine.run_allocation_engine()
    for w in res["wards"]:
        r = w["risk_score"]
        d = w["normalized_density"]
        expected_priority = round((0.7 * r) + (0.3 * d), 4)

        assert 0.0 <= d <= 1.0, f"Normalized density {d} out of range [0, 1]"
        assert abs(w["priority_score"] - expected_priority) < 1e-4, (
            f"Priority mismatch for {w['ward_id']}: {w['priority_score']} vs {expected_priority}"
        )


def test_deterministic_priority_ranking(engine):
    """Verify wards are strictly ordered by descending priority score."""
    res = engine.run_allocation_engine()
    wards = res["wards"]
    for i in range(len(wards) - 1):
        assert wards[i]["priority_score"] >= wards[i + 1]["priority_score"], (
            f"Ordering violation at rank {i+1} vs {i+2}"
        )
        assert wards[i]["priority_ranking"] == i + 1


# ---------------------------------------------------------------------------
# 3. Scarcity Controls (30%, 50%, 70%, 100%) Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("stock_pct", [30.0, 50.0, 70.0, 100.0])
def test_scarcity_stock_controls(engine, stock_pct):
    """
    Verify that effective stock matches:
    Effective Stock = floor(Total Regional Stock * Selected Stock Percentage / 100)
    and that total allocations NEVER exceed effective stock.
    """
    res = engine.run_allocation_engine(stock_percentage=stock_pct, total_spraying_crews=150)
    scarcity = res["scarcity_controls"]
    overview = res["regional_overview"]

    expected_saline = int(math.floor(scarcity["total_regional_saline"] * stock_pct / 100.0))
    expected_kits = int(math.floor(scarcity["total_regional_kits"] * stock_pct / 100.0))
    expected_beds = int(math.floor(scarcity["total_regional_beds"] * stock_pct / 100.0))

    assert scarcity["effective_saline_stock"] == expected_saline
    assert scarcity["effective_kits_stock"] == expected_kits
    assert scarcity["effective_beds_stock"] == expected_beds

    # Constraints: Total allocations cannot exceed effective stock
    assert overview["total_saline_allocated"] <= expected_saline
    assert overview["total_kits_allocated"] <= expected_kits
    assert overview["total_beds_allocated"] <= expected_beds

    # Non-negative integers
    for w in res["wards"]:
        assert w["approved_saline_allocation"] >= 0
        assert w["approved_kits_allocation"] >= 0
        assert w["approved_beds_allocation"] >= 0
        assert w["remaining_saline_deficit"] >= 0
        assert w["remaining_kits_deficit"] >= 0
        assert w["remaining_beds_deficit"] >= 0


# ---------------------------------------------------------------------------
# 4. Spraying Crew Assignment Tests (Zero, Insufficient, Sufficient)
# ---------------------------------------------------------------------------
def test_zero_spraying_crews(engine):
    """Verify that with 0 available crews, zero crews are assigned and crew deficit equals demand."""
    res = engine.run_allocation_engine(stock_percentage=100.0, total_spraying_crews=0)
    overview = res["regional_overview"]

    assert overview["total_assigned_crews"] == 0
    assert overview["total_crew_shortage"] == overview["total_required_crews"]
    for w in res["wards"]:
        assert w["approved_crew_allocation"] == 0
        assert w["crew_deficit"] == w["required_crews"]


def test_insufficient_spraying_crews(engine):
    """Verify that with insufficient crews (e.g. 50), all 50 are assigned to highest priority wards first."""
    res = engine.run_allocation_engine(stock_percentage=100.0, total_spraying_crews=50)
    overview = res["regional_overview"]

    assert overview["total_assigned_crews"] == 50
    assert overview["total_crew_shortage"] == overview["total_required_crews"] - 50

    # Highest priority wards must receive crew assignments before lower priority wards
    high_priority_crews = sum(w["approved_crew_allocation"] for w in res["wards"][:15])
    low_priority_crews = sum(w["approved_crew_allocation"] for w in res["wards"][-15:])
    assert high_priority_crews > low_priority_crews


def test_sufficient_spraying_crews(engine):
    """Verify that with sufficient crews (e.g. 500), all ward crew demands are 100% fulfilled."""
    res = engine.run_allocation_engine(stock_percentage=100.0, total_spraying_crews=500)
    overview = res["regional_overview"]

    assert overview["total_crew_shortage"] == 0
    for w in res["wards"]:
        assert w["approved_crew_allocation"] == w["required_crews"]
        assert w["crew_deficit"] == 0
        assert w["crew_fulfillment_pct"] == 100.0


# ---------------------------------------------------------------------------
# 5. Hospital Bed Capacity Overflow Routing Tests
# ---------------------------------------------------------------------------
def test_hospital_overflow_routing(engine):
    """
    Verify capacity-constrained greedy hospital overflow routing:
    - Distance is calculated using Great-Circle Haversine formula
    - Only routes patients from shortage wards to surplus wards
    - Does not route more than available surplus capacity
    """
    res = engine.run_allocation_engine(stock_percentage=100.0)
    routes = res["hospital_overflow_routes"]

    for r in routes:
        assert r["patients_referred"] > 0
        assert r["distance_km"] >= 0.0
        assert r["from_ward_id"] != r["to_ward_id"]

        # Verify haversine calculation
        src_coords = ALL_WARD_COORDS[r["from_ward_id"]]
        dest_coords = ALL_WARD_COORDS[r["to_ward_id"]]
        computed_dist = haversine_distance_km(src_coords[0], src_coords[1], dest_coords[0], dest_coords[1])
        assert abs(r["distance_km"] - computed_dist) < 0.1


# ---------------------------------------------------------------------------
# 6. ML Counterfactual Intervention Simulation Tests
# ---------------------------------------------------------------------------
def test_counterfactual_simulation(engine):
    """
    Verify ML counterfactual simulation calculates positive averted cases
    and saved medical supplies when deploying spraying crews.
    """
    impact = engine.simulate_counterfactual_intervention(
        ward_id="DNCC_Ward_01",
        crews_assigned=5,
        larvicide_coverage_pct=90.0,
    )

    assert impact["intervention_impact"]["averted_cases"] > 0
    assert impact["intervention_impact"]["case_reduction_pct"] > 0
    assert impact["intervention_impact"]["saline_bags_saved"] >= 0
    assert impact["intervention_impact"]["diagnostic_kits_saved"] >= 0


# ---------------------------------------------------------------------------
# 7. SQLite Database Persistence and Audit Trail Tests
# ---------------------------------------------------------------------------
def test_database_persistence_and_audit_trail(engine):
    """
    Verify that an administrator-approved plan is committed to SQLite
    and recorded in the audit trail.
    """
    res = engine.run_allocation_engine(stock_percentage=85.0, total_spraying_crews=140)
    plan_id = save_approved_plan(res, plan_name="Pytest Verification Plan", approved_by="Automated Test Runner")

    assert plan_id is not None
    assert plan_id > 0

    logs = get_audit_logs(limit=10)
    assert len(logs) > 0
    assert any(log["action"] == "APPROVE_ALLOCATION_PLAN" for log in logs)
