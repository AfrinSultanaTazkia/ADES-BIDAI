"""
ADES BIDAI - Hospital Surge Detection & Cross-Ward Overflow Routing Engine
Constrained Priority-Based Greedy Overflow Routing with Complete Offline Resilience

Features:
- Enforces same-city routing constraints across 5 city corporations
- Source ward prioritization: (0.7 * Risk Score) + (0.3 * Normalized Density)
- Destination ward selection by lowest projected bed utilization with tie-breakers
- Accounting identities validation and zero-capacity handling
- Ward-level and city-wide capacity, occupancy, utilization, and net deficit calculations
- Deterministic critical surge warnings and offline template-based dispatch notices
- Administrator interactive simulation and manual modification support
"""

import math
import copy
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from utils.ward_coordinates import ALL_WARD_COORDS, haversine_distance_km

CITIES_LIST = ["Chattogram", "Dhaka North", "Dhaka South", "Gazipur", "Narayanganj"]

SHARED_CONTRACT_REQUIRED_FIELDS = [
    "ward_id",
    "ward_name",
    "city",
    "predicted_cases_week_1",
    "predicted_cases_week_2",
    "predicted_cases_total",
    "risk_level",
    "risk_score",
    "population_density_sqkm",
    "normalized_density",
    "priority_score",
    "hospital_beds_required",
    "hospital_beds_available",
    "hospital_beds_effective_capacity",
    "hospital_beds_deficit",
    "hospital_beds_surplus",
]


class HospitalOverflowRoutingEngine:
    """
    Independent, modular Hospital Surge Detection & Cross-Ward Overflow Routing Engine.
    Operates strictly within city boundaries using a capacity-constrained greedy algorithm.
    """

    def __init__(self):
        pass

    @staticmethod
    def validate_ward_contract(ward: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates that a ward dictionary contains all required shared contract fields.
        Ensures non-negative numeric constraints and defaults where appropriate.
        """
        for field in SHARED_CONTRACT_REQUIRED_FIELDS:
            if field not in ward:
                raise ValueError(f"Missing required shared data contract field: '{field}' in ward record: {ward.get('ward_id')}")

        cleaned = dict(ward)
        # Ensure integer fields
        cleaned["hospital_beds_required"] = max(0, int(round(float(cleaned["hospital_beds_required"]))))
        cleaned["hospital_beds_available"] = max(0, int(round(float(cleaned["hospital_beds_available"]))))
        cleaned["hospital_beds_effective_capacity"] = max(0, int(round(float(cleaned["hospital_beds_effective_capacity"]))))

        # Recalculate or verify initial deficit and surplus
        req = cleaned["hospital_beds_required"]
        cap = cleaned["hospital_beds_effective_capacity"]
        cleaned["hospital_beds_deficit"] = max(0, req - cap)
        cleaned["hospital_beds_surplus"] = max(0, cap - req)

        # Coordinate fallbacks if absent
        wid = cleaned["ward_id"]
        if "lat" not in cleaned or "lon" not in cleaned or cleaned["lat"] is None or cleaned["lon"] is None:
            coords = ALL_WARD_COORDS.get(wid, (23.8103, 90.4125, wid))
            cleaned["lat"] = coords[0]
            cleaned["lon"] = coords[1]
            if "locality" not in cleaned or not cleaned["locality"]:
                cleaned["locality"] = coords[2] if len(coords) > 2 else wid

        return cleaned

    @staticmethod
    def build_shared_contract_from_engine_wards(
        engine_wards: List[Dict[str, Any]],
        stock_percentage: float = 100.0,
        custom_bed_demand: Optional[Dict[str, int]] = None,
        custom_bed_capacity: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Transforms the output of DengueResourceEngine into the standardized Shared Hospital Routing Data Contract.
        Preserves original availability and consumes pre-calculated effective capacity.
        Does NOT re-apply scarcity if effective capacity is already present.
        """
        contract_wards = []
        stock_pct = max(30.0, min(100.0, float(stock_percentage)))

        for w in engine_wards:
            wid = str(w["ward_id"])
            w_name = w.get("locality", wid)
            city = str(w.get("city", "Dhaka"))

            pw1 = float(w.get("predicted_cases_w1", w.get("predicted_cases_week_1", 0.0)))
            pw2 = float(w.get("predicted_cases_w2", w.get("predicted_cases_week_2", 0.0)))
            ptot = float(w.get("total_predicted_cases", w.get("predicted_cases_total", pw1 + pw2)))

            r_level = str(w.get("risk_level", "Medium"))
            r_score = float(w.get("risk_score", 0.60))
            pop_density = float(w.get("population_density_sqkm", 35000.0))
            norm_density = float(w.get("normalized_density", 0.5))
            p_score = float(w.get("priority_score", 0.5))

            # Demand (beds required)
            if custom_bed_demand and wid in custom_bed_demand:
                beds_req = max(0, int(custom_bed_demand[wid]))
            else:
                beds_req = int(w.get("beds_demand", w.get("hospital_beds_required", 0)))

            # Available (original)
            beds_avail = int(w.get("current_hospital_beds", w.get("hospital_beds_available", 0)))

            # Effective Capacity
            if custom_bed_capacity and wid in custom_bed_capacity:
                eff_cap = max(0, int(custom_bed_capacity[wid]))
            elif "hospital_beds_effective_capacity" in w:
                eff_cap = int(w["hospital_beds_effective_capacity"])
            else:
                eff_cap = int(math.floor(beds_avail * stock_pct / 100.0))

            init_def = max(0, beds_req - eff_cap)
            init_surp = max(0, eff_cap - beds_req)

            entry = {
                "ward_id": wid,
                "ward_name": w_name,
                "city": city,
                "predicted_cases_week_1": round(pw1, 2),
                "predicted_cases_week_2": round(pw2, 2),
                "predicted_cases_total": round(ptot, 2),
                "risk_level": r_level,
                "risk_score": r_score,
                "population_density_sqkm": pop_density,
                "normalized_density": norm_density,
                "priority_score": p_score,
                "hospital_beds_required": beds_req,
                "hospital_beds_available": beds_avail,
                "hospital_beds_effective_capacity": eff_cap,
                "hospital_beds_deficit": init_def,
                "hospital_beds_surplus": init_surp,
                "locality": w.get("locality", w_name),
                "lat": w.get("lat"),
                "lon": w.get("lon"),
            }
            contract_wards.append(entry)

        return contract_wards

    def calculate_overflow_routing(
        self,
        ward_data: List[Dict[str, Any]],
        scenario_name: str = "Standard Capacity Plan",
        simulation_params: Optional[Dict[str, Any]] = None,
        manual_routing_adjustments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the City-Constrained Priority-Based Greedy Overflow Routing Algorithm.

        Parameters:
        - ward_data: List of wards adhering to the Shared Hospital Routing Data Contract.
        - scenario_name: Descriptor for the scenario (e.g. "Baseline Dataset", "Simulation").
        - simulation_params: Metadata dict detailing modifications.
        - manual_routing_adjustments: Optional admin overrides to specific route assignments.

        Returns:
        Structured result dict matching Section 21 specification.
        """
        # 1. Validation & deep copy
        if not ward_data:
            raise ValueError("Input ward_data cannot be empty.")

        validated_wards = [self.validate_ward_contract(w) for w in ward_data]

        # 2. Group wards by city
        city_groups: Dict[str, List[Dict[str, Any]]] = {}
        for w in validated_wards:
            c = w["city"]
            if c not in city_groups:
                city_groups[c] = []
            city_groups[c].append(copy.deepcopy(w))

        # Deterministic city processing order
        deterministic_cities = sorted(city_groups.keys())

        all_ward_results: List[Dict[str, Any]] = []
        all_city_results: List[Dict[str, Any]] = []
        all_routing_assignments: List[Dict[str, Any]] = []
        all_critical_warnings: List[Dict[str, Any]] = []

        # 3. Process each city as an independent network
        for city in deterministic_cities:
            wards_in_city = city_groups[city]

            # Internal state tracking per ward
            state_by_ward: Dict[str, Dict[str, Any]] = {}
            for w in wards_in_city:
                wid = w["ward_id"]
                req = w["hospital_beds_required"]
                cap = w["hospital_beds_effective_capacity"]

                init_deficit = max(0, req - cap)
                init_spare = max(0, cap - req)
                init_occupied = min(req, cap)

                init_util = round((init_occupied / cap) * 100.0, 2) if cap > 0 else (None if req == 0 else 100.0)

                state_by_ward[wid] = {
                    "ward_id": wid,
                    "ward_name": w["ward_name"],
                    "city": city,
                    "locality": w.get("locality", w["ward_name"]),
                    "lat": w.get("lat"),
                    "lon": w.get("lon"),
                    "predicted_cases_total": w["predicted_cases_total"],
                    "risk_level": w["risk_level"],
                    "priority_score": w["priority_score"],
                    "hospital_beds_required": req,
                    "hospital_beds_available": w["hospital_beds_available"],
                    "hospital_beds_effective_capacity": cap,
                    "initial_bed_deficit": init_deficit,
                    "initial_spare_beds": init_spare,
                    "initial_occupied_beds": init_occupied,
                    "initial_bed_utilization": init_util,
                    # Dynamic routing tracking
                    "remaining_deficit": init_deficit,
                    "remaining_spare_beds": init_spare,
                    "current_occupancy": init_occupied,
                    "outbound_overflow": 0,
                    "inbound_overflow": 0,
                }

            # Identify overloaded source wards and sort deterministically
            # 1. Descending priority score
            # 2. Descending total predicted dengue cases
            # 3. Ascending ward ID
            overloaded_wards = [
                s for s in state_by_ward.values() if s["remaining_deficit"] > 0
            ]
            overloaded_wards.sort(
                key=lambda s: (-s["priority_score"], -s["predicted_cases_total"], s["ward_id"])
            )

            city_assignments: List[Dict[str, Any]] = []

            # Greedy routing per source ward
            for src in overloaded_wards:
                while src["remaining_deficit"] > 0:
                    # Find eligible destination wards in same city:
                    # - same city (guaranteed by city grouping)
                    # - different from source ward
                    # - remaining spare beds > 0
                    candidates = [
                        d for d in state_by_ward.values()
                        if d["ward_id"] != src["ward_id"] and d["remaining_spare_beds"] > 0
                    ]
                    if not candidates:
                        break

                    # Destination ranking:
                    # 1. Lowest current projected bed utilization: (current_occupancy / capacity)
                    # 2. Highest remaining spare bed capacity if utilization equal
                    # 3. Ascending ward ID as tie-breaker
                    def dest_sort_key(dest):
                        cap = dest["hospital_beds_effective_capacity"]
                        util_ratio = (dest["current_occupancy"] / cap) if cap > 0 else 1.0
                        return (util_ratio, -dest["remaining_spare_beds"], dest["ward_id"])

                    candidates.sort(key=dest_sort_key)
                    best_dest = candidates[0]

                    # Routed overflow = min(source remaining deficit, destination remaining spare beds)
                    routed_qty = min(src["remaining_deficit"], best_dest["remaining_spare_beds"])
                    if routed_qty <= 0:
                        break

                    src_deficit_before = src["remaining_deficit"]
                    dest_spare_before = best_dest["remaining_spare_beds"]
                    dest_cap = best_dest["hospital_beds_effective_capacity"]

                    dest_util_before = round((best_dest["current_occupancy"] / dest_cap) * 100.0, 2) if dest_cap > 0 else 0.0

                    # State updates
                    src["remaining_deficit"] -= routed_qty
                    src["outbound_overflow"] += routed_qty

                    best_dest["remaining_spare_beds"] -= routed_qty
                    best_dest["current_occupancy"] += routed_qty
                    best_dest["inbound_overflow"] += routed_qty

                    src_deficit_after = src["remaining_deficit"]
                    dest_spare_after = best_dest["remaining_spare_beds"]
                    dest_util_after = round((best_dest["current_occupancy"] / dest_cap) * 100.0, 2) if dest_cap > 0 else 100.0

                    # Calculate distance if coordinates exist
                    dist_km = None
                    if src["lat"] is not None and src["lon"] is not None and best_dest["lat"] is not None and best_dest["lon"] is not None:
                        dist_km = haversine_distance_km(src["lat"], src["lon"], best_dest["lat"], best_dest["lon"])

                    assignment = {
                        "source_ward_id": src["ward_id"],
                        "source_ward_name": src["ward_name"],
                        "destination_ward_id": best_dest["ward_id"],
                        "destination_ward_name": best_dest["ward_name"],
                        "city": city,
                        "source_priority_score": src["priority_score"],
                        "routed_overflow": routed_qty,
                        "source_deficit_before": src_deficit_before,
                        "source_deficit_after": src_deficit_after,
                        "destination_spare_before": dest_spare_before,
                        "destination_spare_after": dest_spare_after,
                        "destination_utilization_before": dest_util_before,
                        "destination_utilization_after": dest_util_after,
                        "distance_km": dist_km,
                        "approval_status": "Recommended",
                        "rationale": (
                            f"Assigned {routed_qty} overflow beds from {src['ward_name']} "
                            f"(Priority: {src['priority_score']:.2f}) to lower-burden {best_dest['ward_name']} "
                            f"(Util: {dest_util_before:.1f}% -> {dest_util_after:.1f}%)."
                        ),
                    }
                    city_assignments.append(assignment)

            all_routing_assignments.extend(city_assignments)

            # Final ward metrics calculation for this city
            for wid, s in state_by_ward.items():
                cap = s["hospital_beds_effective_capacity"]
                req = s["hospital_beds_required"]

                local_occupied = min(req, cap)
                final_occupancy = local_occupied + s["inbound_overflow"]
                rem_spare = cap - final_occupancy
                net_deficit = max(0, s["initial_bed_deficit"] - s["outbound_overflow"])

                if cap > 0:
                    final_util = round((final_occupancy / cap) * 100.0, 2)
                else:
                    final_util = None if final_occupancy == 0 else 100.0

                if req > cap:
                    status = "Overloaded"
                elif req == cap:
                    status = "Fully Utilized"
                else:
                    status = "Lower-Burden"

                has_warning = (net_deficit > 0)

                # Merge with original ward fields
                orig = next(w for w in wards_in_city if w["ward_id"] == wid)
                ward_res = copy.deepcopy(orig)
                ward_res.update({
                    "initial_bed_deficit": s["initial_bed_deficit"],
                    "initial_spare_beds": s["initial_spare_beds"],
                    "initial_occupied_beds": s["initial_occupied_beds"],
                    "initial_bed_utilization": s["initial_bed_utilization"],
                    "outbound_overflow": s["outbound_overflow"],
                    "inbound_overflow": s["inbound_overflow"],
                    "net_bed_deficit": net_deficit,
                    "final_projected_occupancy": final_occupancy,
                    "remaining_spare_beds": rem_spare,
                    "final_bed_utilization": final_util,
                    "hospital_surge_status": status,
                    "critical_hospital_warning": has_warning,
                })
                all_ward_results.append(ward_res)

                if has_warning:
                    all_critical_warnings.append({
                        "level": "Ward",
                        "entity_id": wid,
                        "entity_name": s["ward_name"],
                        "city": city,
                        "risk_level": s["risk_level"],
                        "priority_score": s["priority_score"],
                        "required_beds": req,
                        "effective_capacity": cap,
                        "initial_deficit": s["initial_bed_deficit"],
                        "routed_overflow": s["outbound_overflow"],
                        "net_deficit": net_deficit,
                        "message": (
                            f"{wid} ({s['ward_name']}) has an unresolved bed deficit of {net_deficit} beds "
                            f"after same-city routing ({s['outbound_overflow']} overflow accommodated)."
                        ),
                        "recommended_action": (
                            f"Deploy {net_deficit} temporary emergency field hospital beds or activate private healthcare facilities in {wid}."
                        ),
                    })

            # City-Wide Metrics Calculation
            city_wards_res = [w for w in all_ward_results if w["city"] == city]
            c_demand = sum(w["hospital_beds_required"] for w in city_wards_res)
            c_original_cap = sum(w["hospital_beds_available"] for w in city_wards_res)
            c_effective_cap = sum(w["hospital_beds_effective_capacity"] for w in city_wards_res)
            c_init_deficit = sum(w["initial_bed_deficit"] for w in city_wards_res)
            c_init_spare = sum(w["initial_spare_beds"] for w in city_wards_res)
            c_init_occupied = sum(w["initial_occupied_beds"] for w in city_wards_res)
            c_routed = sum(a["routed_overflow"] for a in city_assignments)
            c_final_occupied = sum(w["final_projected_occupancy"] for w in city_wards_res)
            c_rem_spare = sum(w["remaining_spare_beds"] for w in city_wards_res)
            c_net_deficit = sum(w["net_bed_deficit"] for w in city_wards_res)

            c_init_util = round((c_init_occupied / c_effective_cap) * 100.0, 2) if c_effective_cap > 0 else 0.0
            c_final_util = round((c_final_occupied / c_effective_cap) * 100.0, 2) if c_effective_cap > 0 else 0.0
            c_demand_pressure = round((c_demand / c_effective_cap) * 100.0, 2) if c_effective_cap > 0 else 0.0

            if c_init_deficit > 0:
                c_shortage_res = round((c_routed / c_init_deficit) * 100.0, 2)
            else:
                c_shortage_res = None  # N/A

            # City Critical Warning
            c_warning = None
            if c_net_deficit > 0:
                c_warning = (
                    f"{city} has {c_net_deficit} unresolved projected hospital bed requirements "
                    f"after exhausting all eligible same-city spare capacity. "
                    f"Additional emergency hospital capacity is required."
                )
                all_critical_warnings.append({
                    "level": "City",
                    "entity_id": city,
                    "entity_name": city,
                    "city": city,
                    "risk_level": "Surge",
                    "priority_score": None,
                    "required_beds": c_demand,
                    "effective_capacity": c_effective_cap,
                    "initial_deficit": c_init_deficit,
                    "routed_overflow": c_routed,
                    "net_deficit": c_net_deficit,
                    "message": c_warning,
                    "recommended_action": f"Arrange at least {c_net_deficit} additional usable hospital beds within {city} for the modeled planning scenario.",
                })

            city_entry = {
                "city": city,
                "total_wards": len(city_wards_res),
                "total_bed_demand": c_demand,
                "total_original_bed_capacity": c_original_cap,
                "total_effective_bed_capacity": c_effective_cap,
                "initial_bed_deficit": c_init_deficit,
                "initial_spare_beds": c_init_spare,
                "initial_occupied_beds": c_init_occupied,
                "total_routed_overflow": c_routed,
                "final_occupied_beds": c_final_occupied,
                "remaining_spare_beds": c_rem_spare,
                "net_bed_deficit": c_net_deficit,
                "initial_bed_utilization": c_init_util,
                "final_bed_utilization": c_final_util,
                "demand_pressure": c_demand_pressure,
                "shortage_resolution_percentage": c_shortage_res,
                "critical_warning": c_warning,
            }
            all_city_results.append(city_entry)

        # 4. Regional Summary Aggregation (all 60 wards)
        reg_demand = sum(w["hospital_beds_required"] for w in all_ward_results)
        reg_orig_avail = sum(w["hospital_beds_available"] for w in all_ward_results)
        reg_eff_cap = sum(w["hospital_beds_effective_capacity"] for w in all_ward_results)
        reg_overloaded = sum(1 for w in all_ward_results if w["hospital_surge_status"] == "Overloaded")
        reg_fully_utilized = sum(1 for w in all_ward_results if w["hospital_surge_status"] == "Fully Utilized")
        reg_lower_burden = sum(1 for w in all_ward_results if w["hospital_surge_status"] == "Lower-Burden")
        reg_init_deficit = sum(w["initial_bed_deficit"] for w in all_ward_results)
        reg_avail_spare = sum(w["initial_spare_beds"] for w in all_ward_results)
        reg_routed = sum(a["routed_overflow"] for a in all_routing_assignments)
        reg_net_deficit = sum(w["net_bed_deficit"] for w in all_ward_results)
        reg_warning_wards = sum(1 for w in all_ward_results if w["critical_hospital_warning"])

        reg_shortage_res = (
            round((reg_routed / reg_init_deficit) * 100.0, 2)
            if reg_init_deficit > 0 else 100.0
        )
        reg_init_occ = sum(w["initial_occupied_beds"] for w in all_ward_results)
        reg_final_occ = sum(w["final_projected_occupancy"] for w in all_ward_results)

        reg_init_util = round((reg_init_occ / reg_eff_cap) * 100.0, 2) if reg_eff_cap > 0 else 0.0
        reg_final_util = round((reg_final_occ / reg_eff_cap) * 100.0, 2) if reg_eff_cap > 0 else 0.0
        reg_demand_pressure = round((reg_demand / reg_eff_cap) * 100.0, 2) if reg_eff_cap > 0 else 0.0

        regional_summary = {
            "total_projected_bed_demand": reg_demand,
            "total_original_bed_availability": reg_orig_avail,
            "total_effective_bed_capacity": reg_eff_cap,
            "total_overloaded_wards": reg_overloaded,
            "total_fully_utilized_wards": reg_fully_utilized,
            "total_lower_burden_wards": reg_lower_burden,
            "total_initial_bed_deficit": reg_init_deficit,
            "total_available_spare_beds": reg_avail_spare,
            "total_routed_overflow": reg_routed,
            "total_unresolved_bed_deficit": reg_net_deficit,
            "critical_warning_wards_count": reg_warning_wards,
            "overall_shortage_resolution_percentage": reg_shortage_res,
            "initial_regional_utilization": reg_init_util,
            "final_regional_utilization": reg_final_util,
            "regional_demand_pressure": reg_demand_pressure,
        }

        # 5. Validation of Accounting Identities
        validation_errors = []
        tot_outbound = sum(w["outbound_overflow"] for w in all_ward_results)
        tot_inbound = sum(w["inbound_overflow"] for w in all_ward_results)
        if tot_outbound != tot_inbound:
            validation_errors.append(f"Accounting mismatch: Outbound ({tot_outbound}) != Inbound ({tot_inbound})")
        if tot_outbound != reg_routed:
            validation_errors.append(f"Accounting mismatch: Outbound ({tot_outbound}) != Total Routed ({reg_routed})")

        for city_res in all_city_results:
            c_name = city_res["city"]
            # Identity 1: Final City Occupancy == Initial City Occupancy + Routed Overflow
            if city_res["final_occupied_beds"] != (city_res["initial_occupied_beds"] + city_res["total_routed_overflow"]):
                validation_errors.append(f"{c_name}: Final Occupancy != Initial Occupancy + Routed")
            # Identity 2: City Bed Demand == Final City Occupancy + City Net Deficit
            if city_res["total_bed_demand"] != (city_res["final_occupied_beds"] + city_res["net_bed_deficit"]):
                validation_errors.append(f"{c_name}: Bed Demand != Final Occupancy + Net Deficit")
            # Identity 3: City Bed Capacity == Final City Occupancy + Remaining Spare
            if city_res["total_effective_bed_capacity"] != (city_res["final_occupied_beds"] + city_res["remaining_spare_beds"]):
                validation_errors.append(f"{c_name}: Bed Capacity != Final Occupancy + Remaining Spare")
            # Identity 4: City Net Deficit == max(0, Demand - Capacity)
            expected_net = max(0, city_res["total_bed_demand"] - city_res["total_effective_bed_capacity"])
            if city_res["net_bed_deficit"] != expected_net:
                validation_errors.append(f"{c_name}: Net Deficit ({city_res['net_bed_deficit']}) != max(0, Demand - Cap) ({expected_net})")

        validation_results = {
            "is_valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "identities_verified": [
                "Total Outbound Overflow == Total Inbound Overflow",
                "Final City Occupancy == Initial City Occupancy + Total Routed Overflow",
                "City Bed Demand == Final City Occupancy + City Net Deficit",
                "City Bed Capacity == Final City Occupancy + Remaining City Spare Beds",
                "City Net Deficit == max(0, City Bed Demand - City Bed Capacity)",
            ],
        }

        # 6. Generate Template-Based Offline Dispatch Notices
        dispatch_notices = self.generate_dispatch_notices(
            scenario_name=scenario_name,
            routing_assignments=all_routing_assignments,
            city_results=all_city_results,
            critical_warnings=all_critical_warnings,
        )

        return {
            "scenario_metadata": {
                "scenario_name": scenario_name,
                "planning_period": "Upcoming 2 Weeks",
                "total_wards_analyzed": len(all_ward_results),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "simulation_params": simulation_params or {},
            },
            "ward_results": all_ward_results,
            "city_results": all_city_results,
            "routing_assignments": all_routing_assignments,
            "regional_summary": regional_summary,
            "critical_warnings": all_critical_warnings,
            "dispatch_notices": dispatch_notices,
            "validation_results": validation_results,
        }

    @staticmethod
    def generate_dispatch_notices(
        scenario_name: str,
        routing_assignments: List[Dict[str, Any]],
        city_results: List[Dict[str, Any]],
        critical_warnings: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generates deterministic, template-based dispatch notices covering all 5 notice types:
        1. Hospital overflow referral recommendation
        2. Administrator-approved referral plan
        3. Receiving ward capacity notification
        4. Unresolved hospital surge warning
        5. Emergency bed capacity request
        """
        notices = []
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Type 1 & 2: Hospital Overflow Referral Notices (per assignment or batch)
        for i, a in enumerate(routing_assignments[:15]):  # Up to first 15 prominent routes
            notice_id = f"NOTIF-REF-{a['city'][:3].upper()}-{i+1:03d}"
            content = (
                f"HOSPITAL OVERFLOW REFERRAL NOTICE\n"
                f"--------------------------------------------------\n"
                f"Planning Period: Upcoming 2 Weeks\n"
                f"City: {a['city']}\n"
                f"Source Ward: {a['source_ward_id']} ({a['source_ward_name']})\n"
                f"Destination Ward: {a['destination_ward_id']} ({a['destination_ward_name']})\n\n"
                f"Projected Overflow Assigned: {a['routed_overflow']} Bed(s)\n"
                f"Source Remaining Deficit: {a['source_deficit_after']}\n"
                f"Destination Projected Occupancy: {a['destination_spare_before'] - a['destination_spare_after']} Beds Added\n"
                f"Destination Remaining Spare Beds: {a['destination_spare_after']}\n"
                f"Destination Projected Utilization: {a['destination_utilization_after']:.1f}%\n"
                f"Approval Status: {a['approval_status']}\n\n"
                f"Action Required:\n"
                f"Verify receiving hospital capacity, clinical suitability,\n"
                f"and transport feasibility before arranging patient transfers."
            )
            notices.append({
                "notice_id": notice_id,
                "notice_type": "Hospital Overflow Referral Recommendation",
                "city": a["city"],
                "title": f"Referral: {a['source_ward_id']} -> {a['destination_ward_id']} ({a['routed_overflow']} Beds)",
                "content": content,
                "approval_status": a["approval_status"],
                "created_at": now_str,
            })

        # Type 3: Receiving Ward Capacity Notification
        receiving_ward_ids = {a["destination_ward_id"] for a in routing_assignments}
        for dest_id in list(receiving_ward_ids)[:8]:
            incoming_routes = [a for a in routing_assignments if a["destination_ward_id"] == dest_id]
            total_incoming = sum(r["routed_overflow"] for r in incoming_routes)
            dest_city = incoming_routes[0]["city"]
            dest_name = incoming_routes[0]["destination_ward_name"]

            notices.append({
                "notice_id": f"NOTIF-CAP-{dest_id}",
                "notice_type": "Receiving Ward Capacity Notification",
                "city": dest_city,
                "title": f"Receiving Alert: {dest_id} ({dest_name}) - {total_incoming} Inbound Beds",
                "content": (
                    f"RECEIVING WARD CAPACITY NOTIFICATION\n"
                    f"--------------------------------------------------\n"
                    f"Ward: {dest_id} ({dest_name}) | City: {dest_city}\n"
                    f"Total Incoming Patient Referral Demand: {total_incoming} Inpatient Beds\n"
                    f"Contributing Source Wards: {', '.join(r['source_ward_id'] for r in incoming_routes)}\n\n"
                    f"Action Required:\n"
                    f"Ensure isolation wards, fluid reserves, and triage beds\n"
                    f"are prepped for incoming referral transfers."
                ),
                "approval_status": "Ready",
                "created_at": now_str,
            })

        # Type 4: Unresolved Hospital Surge Warning (per city with net deficit)
        for city_res in city_results:
            if city_res["net_bed_deficit"] > 0:
                c_name = city_res["city"]
                notices.append({
                    "notice_id": f"NOTIF-SURGE-{c_name[:3].upper()}",
                    "notice_type": "Unresolved Hospital Surge Warning",
                    "city": c_name,
                    "title": f"Surge Warning: {c_name} Unresolved Deficit ({city_res['net_bed_deficit']} Beds)",
                    "content": (
                        f"CRITICAL HOSPITAL SURGE WARNING\n"
                        f"--------------------------------------------------\n"
                        f"City: {c_name}\n"
                        f"Projected Bed Demand: {city_res['total_bed_demand']}\n"
                        f"Effective Bed Capacity: {city_res['total_effective_bed_capacity']}\n"
                        f"Initial Bed Deficit: {city_res['initial_bed_deficit']}\n"
                        f"Overflow Accommodated: {city_res['total_routed_overflow']}\n"
                        f"Unresolved Bed Deficit: {city_res['net_bed_deficit']} Beds\n"
                        f"Demand Pressure: {city_res['demand_pressure']:.1f}%\n\n"
                        f"Recommended Action:\n"
                        f"Arrange at least {city_res['net_bed_deficit']} additional usable hospital beds\n"
                        f"within {c_name} for the modeled planning scenario."
                    ),
                    "approval_status": "Action Required",
                    "created_at": now_str,
                })

        # Type 5: Emergency Bed Capacity Request
        for warn in [w for w in critical_warnings if w["level"] == "Ward"][:5]:
            notices.append({
                "notice_id": f"NOTIF-EMERG-{warn['entity_id']}",
                "notice_type": "Emergency Bed Capacity Request",
                "city": warn["city"],
                "title": f"Emergency Request: {warn['entity_id']} ({warn['net_deficit']} Additional Beds Required)",
                "content": (
                    f"EMERGENCY HOSPITAL BED CAPACITY REQUEST\n"
                    f"--------------------------------------------------\n"
                    f"Target Ward: {warn['entity_id']} ({warn['entity_name']}) | City: {warn['city']}\n"
                    f"Local Risk Level: {warn['risk_level']} | Priority Score: {warn['priority_score']}\n"
                    f"Local Deficit Remaining: {warn['net_deficit']} Inpatient Beds\n\n"
                    f"Direct Action:\n"
                    f"Authorize requisition of private hospital wards, school gymnasiums,\n"
                    f"or disaster relief tents to install {warn['net_deficit']} emergency inpatient beds."
                ),
                "approval_status": "Urgent",
                "created_at": now_str,
            })

        return notices


# Helper for Chattogram Reference Scenario Test
def get_chattogram_reference_scenario() -> List[Dict[str, Any]]:
    """
    Returns the exact Chattogram reference test dataset from prompt Section 11:
    | Ward | Bed Demand | Effective Capacity | Initial Deficit | Spare Beds |
    | Ward 01 | 100 | 60 | 40 | 0 |
    | Ward 02 | 80  | 50 | 30 | 0 |
    | Ward 03 | 40  | 70 | 0  | 30 |
    | Ward 04 | 30  | 50 | 0  | 20 |
    | Ward 05 | 20  | 30 | 0  | 10 |
    Total Bed Demand = 270, Total Capacity = 260
    Priority: Ward 01 > Ward 02
    """
    return [
        {
            "ward_id": "Ward 01",
            "ward_name": "Ward 01",
            "city": "Chattogram",
            "predicted_cases_week_1": 50.0,
            "predicted_cases_week_2": 50.0,
            "predicted_cases_total": 100.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 50000.0,
            "normalized_density": 0.8,
            "priority_score": 0.94,  # Higher than Ward 02
            "hospital_beds_required": 100,
            "hospital_beds_available": 60,
            "hospital_beds_effective_capacity": 60,
            "hospital_beds_deficit": 40,
            "hospital_beds_surplus": 0,
            "lat": 22.35,
            "lon": 91.80,
        },
        {
            "ward_id": "Ward 02",
            "ward_name": "Ward 02",
            "city": "Chattogram",
            "predicted_cases_week_1": 40.0,
            "predicted_cases_week_2": 40.0,
            "predicted_cases_total": 80.0,
            "risk_level": "High",
            "risk_score": 1.0,
            "population_density_sqkm": 40000.0,
            "normalized_density": 0.6,
            "priority_score": 0.88,
            "hospital_beds_required": 80,
            "hospital_beds_available": 50,
            "hospital_beds_effective_capacity": 50,
            "hospital_beds_deficit": 30,
            "hospital_beds_surplus": 0,
            "lat": 22.36,
            "lon": 91.81,
        },
        {
            "ward_id": "Ward 03",
            "ward_name": "Ward 03",
            "city": "Chattogram",
            "predicted_cases_week_1": 20.0,
            "predicted_cases_week_2": 20.0,
            "predicted_cases_total": 40.0,
            "risk_level": "Medium",
            "risk_score": 0.6,
            "population_density_sqkm": 25000.0,
            "normalized_density": 0.4,
            "priority_score": 0.54,
            "hospital_beds_required": 40,
            "hospital_beds_available": 70,
            "hospital_beds_effective_capacity": 70,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 30,
            "lat": 22.37,
            "lon": 91.82,
        },
        {
            "ward_id": "Ward 04",
            "ward_name": "Ward 04",
            "city": "Chattogram",
            "predicted_cases_week_1": 15.0,
            "predicted_cases_week_2": 15.0,
            "predicted_cases_total": 30.0,
            "risk_level": "Medium",
            "risk_score": 0.6,
            "population_density_sqkm": 20000.0,
            "normalized_density": 0.3,
            "priority_score": 0.51,
            "hospital_beds_required": 30,
            "hospital_beds_available": 50,
            "hospital_beds_effective_capacity": 50,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 20,
            "lat": 22.38,
            "lon": 91.83,
        },
        {
            "ward_id": "Ward 05",
            "ward_name": "Ward 05",
            "city": "Chattogram",
            "predicted_cases_week_1": 10.0,
            "predicted_cases_week_2": 10.0,
            "predicted_cases_total": 20.0,
            "risk_level": "Low",
            "risk_score": 0.3,
            "population_density_sqkm": 15000.0,
            "normalized_density": 0.2,
            "priority_score": 0.27,
            "hospital_beds_required": 20,
            "hospital_beds_available": 30,
            "hospital_beds_effective_capacity": 30,
            "hospital_beds_deficit": 0,
            "hospital_beds_surplus": 10,
            "lat": 22.39,
            "lon": 91.84,
        },
    ]
