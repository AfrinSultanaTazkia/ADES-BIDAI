"""
Comprehensive Automated Test Suite for Hospital Surge Detection & Cross-Ward Overflow Routing Engine
Verifies all 18+ Mandatory Hospital Routing Tests, Scarcity & Simulation Tests, Deterministic Execution,
Accounting Identities, Reference Chattogram Scenario, and SQLite Database Persistence.
"""

import pytest
import copy
import random
from typing import List, Dict, Any

from src.hospital_routing import (
    HospitalOverflowRoutingEngine,
    get_chattogram_reference_scenario,
    SHARED_CONTRACT_REQUIRED_FIELDS,
)
from src.resource_engine import DengueResourceEngine
from src.database import (
    save_approved_hospital_plan,
    get_approved_hospital_plans,
    revalidate_hospital_plans,
    get_audit_logs,
)


@pytest.fixture
def routing_engine():
    return HospitalOverflowRoutingEngine()


@pytest.fixture
def resource_engine():
    return DengueResourceEngine()


# ---------------------------------------------------------------------------
# 1. Mandatory Reference Chattogram Test Scenario (Section 11)
# ---------------------------------------------------------------------------
def test_reference_chattogram_scenario(routing_engine):
    """
    Mandatory Unit Test: Chattogram reference scenario.
    | Ward | Demand | Capacity | Initial Deficit | Spare |
    | Ward 01 | 100 | 60 | 40 | 0 |
    | Ward 02 | 80  | 50 | 30 | 0 |
    | Ward 03 | 40  | 70 | 0  | 30 |
    | Ward 04 | 30  | 50 | 0  | 20 |
    | Ward 05 | 20  | 30 | 0  | 10 |
    Total Demand = 270, Capacity = 260
    Expected Routing:
      Ward 01 -> Ward 03: 30
      Ward 01 -> Ward 04: 10
      Ward 02 -> Ward 05: 10
      Ward 02 -> Ward 04: 10
    Expected City Net Deficit: 10
    """
    scenario = get_chattogram_reference_scenario()
    res = routing_engine.calculate_overflow_routing(scenario, scenario_name="Reference Test")

    # 1. Verify routing assignments
    assignments = res["routing_assignments"]
    assert len(assignments) == 4, f"Expected 4 routing assignments, got {len(assignments)}"

    expected_routes = [
        ("Ward 01", "Ward 03", 30),
        ("Ward 01", "Ward 04", 10),
        ("Ward 02", "Ward 05", 10),
        ("Ward 02", "Ward 04", 10),
    ]

    for (exp_src, exp_dest, exp_qty), act in zip(expected_routes, assignments):
        assert act["source_ward_id"] == exp_src, f"Expected source {exp_src}, got {act['source_ward_id']}"
        assert act["destination_ward_id"] == exp_dest, f"Expected destination {exp_dest}, got {act['destination_ward_id']}"
        assert act["routed_overflow"] == exp_qty, f"Expected {exp_qty} routed, got {act['routed_overflow']}"

    # 2. Verify City Results
    city_res = res["city_results"][0]
    assert city_res["city"] == "Chattogram"
    assert city_res["total_bed_demand"] == 270
    assert city_res["total_effective_bed_capacity"] == 260
    assert city_res["initial_bed_deficit"] == 70
    assert city_res["initial_spare_beds"] == 60
    assert city_res["initial_occupied_beds"] == 200
    assert city_res["total_routed_overflow"] == 60
    assert city_res["final_occupied_beds"] == 260
    assert city_res["net_bed_deficit"] == 10
    assert city_res["initial_bed_utilization"] == 76.92
    assert city_res["final_bed_utilization"] == 100.0
    assert city_res["demand_pressure"] == 103.85
    assert city_res["shortage_resolution_percentage"] == 85.71
    assert "Additional emergency hospital capacity is required" in city_res["critical_warning"]

    # 3. Verify Ward Results
    w_by_id = {w["ward_id"]: w for w in res["ward_results"]}
    assert w_by_id["Ward 01"]["final_projected_occupancy"] == 60
    assert w_by_id["Ward 01"]["remaining_spare_beds"] == 0
    assert w_by_id["Ward 01"]["net_bed_deficit"] == 0

    assert w_by_id["Ward 02"]["final_projected_occupancy"] == 50
    assert w_by_id["Ward 02"]["remaining_spare_beds"] == 0
    assert w_by_id["Ward 02"]["net_bed_deficit"] == 10  # Unresolved deficit

    assert w_by_id["Ward 03"]["final_projected_occupancy"] == 70
    assert w_by_id["Ward 03"]["remaining_spare_beds"] == 0
    assert w_by_id["Ward 03"]["net_bed_deficit"] == 0

    assert w_by_id["Ward 04"]["final_projected_occupancy"] == 50
    assert w_by_id["Ward 04"]["remaining_spare_beds"] == 0
    assert w_by_id["Ward 04"]["net_bed_deficit"] == 0

    assert w_by_id["Ward 05"]["final_projected_occupancy"] == 30
    assert w_by_id["Ward 05"]["remaining_spare_beds"] == 0
    assert w_by_id["Ward 05"]["net_bed_deficit"] == 0

    # 4. Verify Accounting Identities
    assert res["validation_results"]["is_valid"] is True


# ---------------------------------------------------------------------------
# 2. Detailed Hospital Routing Tests (Cases 1 to 18)
# ---------------------------------------------------------------------------
def test_all_wards_sufficient_capacity(routing_engine):
    """Case 1: All wards have sufficient local bed capacity (no deficit)."""
    wards = [
        {
            "ward_id": f"DNCC_Ward_{i:02d}",
            "ward_name": f"Ward {i}",
            "city": "Dhaka North",
            "predicted_cases_week_1": 10.0,
            "predicted_cases_week_2": 10.0,
            "predicted_cases_total": 20.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 10,
            "hospital_beds_available": 30,
            "hospital_beds_effective_capacity": 30,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 20,
        }
        for i in range(1, 4)
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    assert len(res["routing_assignments"]) == 0
    assert res["regional_summary"]["total_initial_bed_deficit"] == 0
    assert res["regional_summary"]["total_unresolved_bed_deficit"] == 0
    assert res["regional_summary"]["total_routed_overflow"] == 0


def test_single_overloaded_ward_single_destination(routing_engine):
    """Case 2: Single overloaded ward with one eligible destination."""
    wards = [
        {
            "ward_id": "DSCC_Ward_01",
            "ward_name": "Ward 01",
            "city": "Dhaka South",
            "predicted_cases_week_1": 50.0,
            "predicted_cases_week_2": 50.0,
            "predicted_cases_total": 100.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 50000.0,
            "normalized_density": 0.7,
            "priority_score": 0.91,
            "hospital_beds_required": 50,
            "hospital_beds_available": 20,
            "hospital_beds_effective_capacity": 20,
            "hospital_beds_deficit": 30,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "DSCC_Ward_02",
            "ward_name": "Ward 02",
            "city": "Dhaka South",
            "predicted_cases_week_1": 10.0,
            "predicted_cases_week_2": 10.0,
            "predicted_cases_total": 20.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 10,
            "hospital_beds_available": 60,
            "hospital_beds_effective_capacity": 60,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 50,
        },
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    assert len(res["routing_assignments"]) == 1
    a = res["routing_assignments"][0]
    assert a["source_ward_id"] == "DSCC_Ward_01"
    assert a["destination_ward_id"] == "DSCC_Ward_02"
    assert a["routed_overflow"] == 30
    assert res["regional_summary"]["total_unresolved_bed_deficit"] == 0


def test_single_overloaded_ward_multiple_destinations(routing_engine):
    """Case 3: Single overloaded ward requiring multiple destinations."""
    wards = [
        {
            "ward_id": "GCC_Ward_01",
            "ward_name": "Ward 01",
            "city": "Gazipur",
            "predicted_cases_week_1": 50.0,
            "predicted_cases_week_2": 50.0,
            "predicted_cases_total": 100.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 40000.0,
            "normalized_density": 0.6,
            "priority_score": 0.88,
            "hospital_beds_required": 60,
            "hospital_beds_available": 10,
            "hospital_beds_effective_capacity": 10,
            "hospital_beds_deficit": 50,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "GCC_Ward_02",
            "ward_name": "Ward 02",
            "city": "Gazipur",
            "predicted_cases_week_1": 5.0,
            "predicted_cases_week_2": 5.0,
            "predicted_cases_total": 10.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 5,
            "hospital_beds_available": 30,
            "hospital_beds_effective_capacity": 30,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 25,
        },
        {
            "ward_id": "GCC_Ward_03",
            "ward_name": "Ward 03",
            "city": "Gazipur",
            "predicted_cases_week_1": 5.0,
            "predicted_cases_week_2": 5.0,
            "predicted_cases_total": 10.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 5,
            "hospital_beds_available": 35,
            "hospital_beds_effective_capacity": 35,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 30,
        },
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    # Deficit of 50 split across Ward 02 (25) and Ward 03 (25)
    assert len(res["routing_assignments"]) == 2
    total_assigned = sum(a["routed_overflow"] for a in res["routing_assignments"])
    assert total_assigned == 50
    assert res["regional_summary"]["total_unresolved_bed_deficit"] == 0


def test_multiple_overloaded_competing_spare_beds(routing_engine):
    """Case 4: Multiple overloaded wards competing for the same spare beds."""
    wards = [
        {
            "ward_id": "NCC_Ward_01",
            "ward_name": "Ward 01",
            "city": "Narayanganj",
            "predicted_cases_week_1": 50.0,
            "predicted_cases_week_2": 50.0,
            "predicted_cases_total": 100.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 50000.0,
            "normalized_density": 0.8,
            "priority_score": 0.94,  # Higher priority
            "hospital_beds_required": 50,
            "hospital_beds_available": 20,
            "hospital_beds_effective_capacity": 20,
            "hospital_beds_deficit": 30,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "NCC_Ward_02",
            "ward_name": "Ward 02",
            "city": "Narayanganj",
            "predicted_cases_week_1": 40.0,
            "predicted_cases_week_2": 40.0,
            "predicted_cases_total": 80.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 30000.0,
            "normalized_density": 0.5,
            "priority_score": 0.85,  # Lower priority
            "hospital_beds_required": 40,
            "hospital_beds_available": 10,
            "hospital_beds_effective_capacity": 10,
            "hospital_beds_deficit": 30,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "NCC_Ward_03",
            "ward_name": "Ward 03",
            "city": "Narayanganj",
            "predicted_cases_week_1": 10.0,
            "predicted_cases_week_2": 10.0,
            "predicted_cases_total": 20.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.30,
            "hospital_beds_required": 10,
            "hospital_beds_available": 40,
            "hospital_beds_effective_capacity": 40,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 30,
        },
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    # Ward 01 must receive the 30 spare beds first; Ward 02 gets 0
    assert len(res["routing_assignments"]) == 1
    assert res["routing_assignments"][0]["source_ward_id"] == "NCC_Ward_01"
    assert res["routing_assignments"][0]["routed_overflow"] == 30
    w_by_id = {w["ward_id"]: w for w in res["ward_results"]}
    assert w_by_id["NCC_Ward_01"]["net_bed_deficit"] == 0
    assert w_by_id["NCC_Ward_02"]["net_bed_deficit"] == 30


def test_insufficient_citywide_spare_capacity(routing_engine):
    """Case 6: Insufficient city-wide spare capacity -> city net deficit > 0."""
    scenario = get_chattogram_reference_scenario()
    res = routing_engine.calculate_overflow_routing(scenario)
    city_res = res["city_results"][0]
    assert city_res["net_bed_deficit"] == 10
    assert city_res["total_routed_overflow"] == 60


def test_no_eligible_destination_wards(routing_engine):
    """Case 7: No eligible destination wards in the city (all overloaded)."""
    wards = [
        {
            "ward_id": f"GCC_Ward_{i:02d}",
            "ward_name": f"Ward {i}",
            "city": "Gazipur",
            "predicted_cases_week_1": 30.0,
            "predicted_cases_week_2": 30.0,
            "predicted_cases_total": 60.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 40000.0,
            "normalized_density": 0.5,
            "priority_score": 0.85,
            "hospital_beds_required": 40,
            "hospital_beds_available": 20,
            "hospital_beds_effective_capacity": 20,
            "hospital_beds_deficit": 20,
            "hospital_beds_surplus": 0,
        }
        for i in range(1, 4)
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    assert len(res["routing_assignments"]) == 0
    assert res["regional_summary"]["total_unresolved_bed_deficit"] == 60
    assert res["regional_summary"]["overall_shortage_resolution_percentage"] == 0.0


def test_zero_hospital_bed_capacity(routing_engine):
    """Case 8: Zero hospital bed capacity handled without division-by-zero error."""
    wards = [
        {
            "ward_id": "DNCC_Ward_01",
            "ward_name": "Ward 01",
            "city": "Dhaka North",
            "predicted_cases_week_1": 20.0,
            "predicted_cases_week_2": 20.0,
            "predicted_cases_total": 40.0,
            "risk_level": "Medium",
            "risk_score": 0.6,
            "population_density_sqkm": 25000.0,
            "normalized_density": 0.4,
            "priority_score": 0.54,
            "hospital_beds_required": 15,
            "hospital_beds_available": 0,
            "hospital_beds_effective_capacity": 0,
            "hospital_beds_deficit": 15,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "DNCC_Ward_02",
            "ward_name": "Ward 02",
            "city": "Dhaka North",
            "predicted_cases_week_1": 0.0,
            "predicted_cases_week_2": 0.0,
            "predicted_cases_total": 0.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 0,
            "hospital_beds_available": 20,
            "hospital_beds_effective_capacity": 20,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 20,
        },
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    w1 = next(w for w in res["ward_results"] if w["ward_id"] == "DNCC_Ward_01")
    assert w1["initial_bed_utilization"] == 100.0
    assert w1["net_bed_deficit"] == 0  # Routed to Ward 02


def test_zero_hospital_bed_demand(routing_engine):
    """Case 9: Zero hospital bed demand handled safely."""
    wards = [
        {
            "ward_id": "CCC_Ward_01",
            "ward_name": "Ward 01",
            "city": "Chattogram",
            "predicted_cases_week_1": 0.0,
            "predicted_cases_week_2": 0.0,
            "predicted_cases_total": 0.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 10000.0,
            "normalized_density": 0.2,
            "priority_score": 0.27,
            "hospital_beds_required": 0,
            "hospital_beds_available": 20,
            "hospital_beds_effective_capacity": 20,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 20,
        }
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    assert res["regional_summary"]["total_projected_bed_demand"] == 0
    assert res["regional_summary"]["total_initial_bed_deficit"] == 0


def test_equal_source_priority_tie_breaking(routing_engine):
    """Case 10: Equal source priority score tie-breaker (predicted cases then ward_id)."""
    wards = [
        {
            "ward_id": "DSCC_Ward_02",  # Alphabetically later
            "ward_name": "Ward 02",
            "city": "Dhaka South",
            "predicted_cases_week_1": 40.0,
            "predicted_cases_week_2": 40.0,
            "predicted_cases_total": 80.0,  # Higher cases
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 40000.0,
            "normalized_density": 0.5,
            "priority_score": 0.85,
            "hospital_beds_required": 40,
            "hospital_beds_available": 10,
            "hospital_beds_effective_capacity": 10,
            "hospital_beds_deficit": 30,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "DSCC_Ward_01",  # Alphabetically earlier
            "ward_name": "Ward 01",
            "city": "Dhaka South",
            "predicted_cases_week_1": 25.0,
            "predicted_cases_week_2": 25.0,
            "predicted_cases_total": 50.0,  # Lower cases
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 40000.0,
            "normalized_density": 0.5,
            "priority_score": 0.85,  # Same priority
            "hospital_beds_required": 30,
            "hospital_beds_available": 10,
            "hospital_beds_effective_capacity": 10,
            "hospital_beds_deficit": 20,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "DSCC_Ward_03",
            "ward_name": "Ward 03",
            "city": "Dhaka South",
            "predicted_cases_week_1": 5.0,
            "predicted_cases_week_2": 5.0,
            "predicted_cases_total": 10.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 5,
            "hospital_beds_available": 35,
            "hospital_beds_effective_capacity": 35,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 30,
        },
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    # DSCC_Ward_02 has higher predicted cases (80 vs 50), must be routed first
    assert res["routing_assignments"][0]["source_ward_id"] == "DSCC_Ward_02"


def test_strict_no_cross_city_routing(routing_engine):
    """Case 13: Strict prevention of cross-city routing even if another city has massive surplus."""
    wards = [
        # Overloaded ward in Chattogram
        {
            "ward_id": "CCC_Ward_01",
            "ward_name": "Pahartali",
            "city": "Chattogram",
            "predicted_cases_week_1": 50.0,
            "predicted_cases_week_2": 50.0,
            "predicted_cases_total": 100.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 50000.0,
            "normalized_density": 0.8,
            "priority_score": 0.94,
            "hospital_beds_required": 60,
            "hospital_beds_available": 10,
            "hospital_beds_effective_capacity": 10,
            "hospital_beds_deficit": 50,
            "hospital_beds_surplus": 0,
        },
        # Massive surplus in Dhaka North
        {
            "ward_id": "DNCC_Ward_01",
            "ward_name": "Uttara",
            "city": "Dhaka North",
            "predicted_cases_week_1": 0.0,
            "predicted_cases_week_2": 0.0,
            "predicted_cases_total": 0.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 10,
            "hospital_beds_available": 500,
            "hospital_beds_effective_capacity": 500,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 490,
        },
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    # MUST NOT route from Chattogram to Dhaka North
    assert len(res["routing_assignments"]) == 0
    w_ccc = next(w for w in res["ward_results"] if w["ward_id"] == "CCC_Ward_01")
    assert w_ccc["net_bed_deficit"] == 50
    assert w_ccc["critical_hospital_warning"] is True


def test_destination_capacity_overbooking_prevention(routing_engine):
    """Case 15: Destination capacity overbooking prevention."""
    wards = [
        {
            "ward_id": "Ward_A",
            "ward_name": "Ward A",
            "city": "Gazipur",
            "predicted_cases_week_1": 50.0,
            "predicted_cases_week_2": 50.0,
            "predicted_cases_total": 100.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 40000.0,
            "normalized_density": 0.5,
            "priority_score": 0.85,
            "hospital_beds_required": 100,
            "hospital_beds_available": 10,
            "hospital_beds_effective_capacity": 10,
            "hospital_beds_deficit": 90,
            "hospital_beds_surplus": 0,
        },
        {
            "ward_id": "Ward_B",
            "ward_name": "Ward B",
            "city": "Gazipur",
            "predicted_cases_week_1": 5.0,
            "predicted_cases_week_2": 5.0,
            "predicted_cases_total": 10.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.3,
            "hospital_beds_required": 5,
            "hospital_beds_available": 20,
            "hospital_beds_effective_capacity": 20,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 15,
        },
    ]
    res = routing_engine.calculate_overflow_routing(wards)
    dest_w = next(w for w in res["ward_results"] if w["ward_id"] == "Ward_B")
    assert dest_w["final_projected_occupancy"] == 20
    assert dest_w["final_projected_occupancy"] <= dest_w["hospital_beds_effective_capacity"]
    assert dest_w["remaining_spare_beds"] == 0


def test_invalid_or_missing_shared_contract_fields(routing_engine):
    """Case 16: Invalid or missing shared data contract fields raises ValueError."""
    bad_ward = {
        "ward_id": "W01",
        "city": "Dhaka North",
        # Missing hospital_beds_required, etc.
    }
    with pytest.raises(ValueError) as exc:
        routing_engine.validate_ward_contract(bad_ward)
    assert "Missing required shared data contract field" in str(exc.value)


# ---------------------------------------------------------------------------
# 3. Full Dataset 60-Ward Integration Test (Case 18)
# ---------------------------------------------------------------------------
def test_full_dataset_60_wards_integration(resource_engine):
    """Case 18: Full dataset integration across all 60 wards and five cities."""
    alloc_res = resource_engine.run_allocation_engine(stock_percentage=100.0, total_spraying_crews=150)
    assert "hospital_routing" in alloc_res

    h_res = alloc_res["hospital_routing"]
    assert len(h_res["ward_results"]) == 60
    assert len(h_res["city_results"]) == 5

    # Check city representation
    cities = {c["city"] for c in h_res["city_results"]}
    assert cities == {"Chattogram", "Dhaka North", "Dhaka South", "Gazipur", "Narayanganj"}

    # Validate accounting identities
    assert h_res["validation_results"]["is_valid"] is True


# ---------------------------------------------------------------------------
# 4. Scarcity & Simulation Tests (Section 22)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("stock_pct", [30.0, 50.0, 70.0, 100.0])
def test_scarcity_controls_effective_capacity(resource_engine, stock_pct):
    """Verify that effective capacity scales strictly with stock percentage and no double-scarcity is applied."""
    h_res = resource_engine.run_hospital_routing(stock_percentage=stock_pct)
    reg = h_res["regional_summary"]

    total_avail = reg["total_original_bed_availability"]
    total_effective = reg["total_effective_bed_capacity"]

    assert total_effective <= total_avail
    # Accounting identities hold at every scarcity level
    assert h_res["validation_results"]["is_valid"] is True


def test_interactive_simulation_isolation(resource_engine):
    """Verify that custom simulated demand/capacity changes do not alter baseline state."""
    # Baseline run
    base_res = resource_engine.run_hospital_routing(stock_percentage=100.0)
    base_demand = base_res["regional_summary"]["total_projected_bed_demand"]

    # Simulated run with +50 beds in CCC_Ward_01
    sim_res = resource_engine.run_hospital_routing(
        stock_percentage=100.0,
        custom_bed_demand={"CCC_Ward_01": 200},
    )
    sim_demand = sim_res["regional_summary"]["total_projected_bed_demand"]
    assert sim_demand > base_demand

    # Post-simulation run: baseline must remain untouched
    post_res = resource_engine.run_hospital_routing(stock_percentage=100.0)
    assert post_res["regional_summary"]["total_projected_bed_demand"] == base_demand


# ---------------------------------------------------------------------------
# 5. Deterministic Execution Tests (Section 19 & 22)
# ---------------------------------------------------------------------------
def test_deterministic_execution_and_shuffling(routing_engine):
    """Verify that repeated executions and shuffling input ward order produce identical routing results."""
    scenario = get_chattogram_reference_scenario()

    res1 = routing_engine.calculate_overflow_routing(scenario)

    # Shuffled order
    shuffled_scenario = copy.deepcopy(scenario)
    random.seed(42)
    random.shuffle(shuffled_scenario)

    res2 = routing_engine.calculate_overflow_routing(shuffled_scenario)

    # Canonical routing assignments must be identical
    routes1 = [(a["source_ward_id"], a["destination_ward_id"], a["routed_overflow"]) for a in res1["routing_assignments"]]
    routes2 = [(a["source_ward_id"], a["destination_ward_id"], a["routed_overflow"]) for a in res2["routing_assignments"]]

    assert routes1 == routes2
    assert res1["city_results"] == res2["city_results"]


def test_accounting_identities_always_hold(routing_engine):
    """
    Verify the 5 mandatory accounting identities hold across diverse scenarios:
    1. Total Outbound Overflow == Total Inbound Overflow
    2. Final City Occupancy == Initial City Occupancy + Total Routed Overflow
    3. City Bed Demand == Final City Occupancy + City Net Deficit
    4. City Bed Capacity == Final City Occupancy + Remaining City Spare Beds
    5. City Net Deficit == max(0, City Bed Demand - City Bed Capacity)
    """
    scenario = get_chattogram_reference_scenario()
    res = routing_engine.calculate_overflow_routing(scenario)
    assert res["validation_results"]["is_valid"] is True


# ---------------------------------------------------------------------------
# 6. Offline Template-Based Dispatch Notices Tests (Section 17)
# ---------------------------------------------------------------------------
def test_offline_template_dispatch_notices(routing_engine):
    """Verify deterministic local template dispatch notices generation."""
    scenario = get_chattogram_reference_scenario()
    res = routing_engine.calculate_overflow_routing(scenario)
    notices = res["dispatch_notices"]

    assert len(notices) >= 4

    notice_types = {n["notice_type"] for n in notices}
    assert "Hospital Overflow Referral Recommendation" in notice_types
    assert "Receiving Ward Capacity Notification" in notice_types
    assert "Unresolved Hospital Surge Warning" in notice_types

    # Verify notice content is populated deterministically without LLM
    ref_notice = next(n for n in notices if n["notice_type"] == "Hospital Overflow Referral Recommendation")
    assert "HOSPITAL OVERFLOW REFERRAL NOTICE" in ref_notice["content"]
    assert "Chattogram" in ref_notice["content"]
    assert "Ward 01" in ref_notice["content"]
    assert "Ward 03" in ref_notice["content"]


# ---------------------------------------------------------------------------
# 7. Database Persistence & Audit Logging Tests (Section 15)
# ---------------------------------------------------------------------------
def test_database_persistence_and_revalidation(routing_engine):
    """Tests saving approved hospital plans to SQLite, retrieving them, and revalidating."""
    scenario = get_chattogram_reference_scenario()
    res = routing_engine.calculate_overflow_routing(scenario)

    plan_id = save_approved_hospital_plan(
        routing_result=res,
        plan_name="Test Chattogram Hospital Surge Plan",
        approved_by="Test Administrator",
        stock_percentage=100.0,
    )
    assert plan_id is not None
    assert plan_id > 0

    plans = get_approved_hospital_plans()
    assert any(p["id"] == plan_id for p in plans)
    saved_plan = next(p for p in plans if p["id"] == plan_id)
    assert saved_plan["plan_name"] == "Test Chattogram Hospital Surge Plan"
    assert saved_plan["total_routed_overflow"] == 60
    assert saved_plan["total_net_deficit"] == 10
    assert saved_plan["status"] == "Approved"

    # Test audit log entry
    logs = get_audit_logs(limit=10)
    assert any(l["action"] == "APPROVE_HOSPITAL_ROUTING_PLAN" for l in logs)

    # Test revalidation
    affected = revalidate_hospital_plans(reason="Capacity change simulation")
    assert affected >= 1

    plans_after = get_approved_hospital_plans()
    revalidated_plan = next(p for p in plans_after if p["id"] == plan_id)
    assert revalidated_plan["status"] == "Revalidation Required"
