"""
ADES BIDAI - What-If Vector Control Impact Simulator
Scenario-based dengue case reduction simulation with multi-intervention support.

Features:
- Larvicide & fogging intervention modelling with area-based coverage
- Saturation response curve (bounded exponential)
- Deterministic bounded combination of interventions
- 2-4 week forecast horizon (ML + recursive extension)
- Greedy crew deployment optimizer
- Full hospital routing comparison (baseline vs adjusted)
- Offline dispatch notice generation (template-based)
- Local SQLite persistence via database.py
"""

import math
import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.resource_engine import (
    DengueResourceEngine,
    DEFAULT_COEFFICIENTS,
    classify_risk_level,
    get_risk_score,
)
from src.hospital_routing import HospitalOverflowRoutingEngine
from utils.ward_coordinates import ALL_WARD_COORDS, WARD_AREAS

# ---------------------------------------------------------------------------
# Intervention Parameter Configuration (versioned, fully local)
# ---------------------------------------------------------------------------

INTERVENTION_PARAMS: Dict[str, Dict[str, Any]] = {
    "larvicide": {
        # Area coverage capacity per crew — matches DEFAULT_COEFFICIENTS["crew_coverage_sqkm"]
        "coverage_capacity_sqkm_per_crew": DEFAULT_COEFFICIENTS["crew_coverage_sqkm"],  # 1.5
        "max_effectiveness": 0.30,
        # Week 1-4 ramp-up factors (index 0 = week 1, index 3 = week 4)
        "weekly_impact_factors": [0.00, 0.40, 0.80, 1.00],
        "impact_delay": 1,       # weeks before first measurable impact
        "impact_duration": 4,    # weeks of sustained effectiveness
        "saturation_parameter": 2.0,
        "parameter_version": "1.0",
        "assumption_status": "configured_simulation_assumption",
    },
    "fogging": {
        "coverage_capacity_sqkm_per_crew": DEFAULT_COEFFICIENTS["crew_coverage_sqkm"],  # 1.5
        "max_effectiveness": 0.25,
        "weekly_impact_factors": [0.00, 0.80, 0.50, 0.20],
        "impact_delay": 0,
        "impact_duration": 3,
        "saturation_parameter": 1.5,
        "parameter_version": "1.0",
        "assumption_status": "configured_simulation_assumption",
    },
}

SIMULATOR_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Request / Result Data Structures
# ---------------------------------------------------------------------------

@dataclass
class SimulationRequest:
    scenario_id: str
    scenario_name: str
    # 2, 3, or 4 weeks
    forecast_horizon_weeks: int
    # Week 1 means deployment starts in the first forecast week
    deployment_start_week: int
    selected_ward_ids: List[str]
    larvicide_crews: Dict[str, int]      # ward_id -> crew count
    fogging_crews: Dict[str, int]        # ward_id -> crew count
    total_available_crews: int
    stock_percentage: float
    # Optional override — merges on top of INTERVENTION_PARAMS
    intervention_params: Optional[Dict[str, Any]] = None
    # "linear" disables saturation curve (k effectively -> 0)
    response_model: str = "saturation"


@dataclass
class SimulationResult:
    scenario_metadata: Dict[str, Any]
    ward_intervention_results: List[Dict[str, Any]]
    regional_impact_summary: Dict[str, Any]
    crew_deployment_plan: Dict[str, Any]
    intervention_roi_rankings: List[Dict[str, Any]]
    potential_roi_rankings: List[Dict[str, Any]]
    resource_demand_comparison: List[Dict[str, Any]]
    hospital_routing_comparison: Dict[str, Any]
    critical_warnings: List[str]
    dispatch_notices: List[str]
    assumptions_and_limitations: List[str]


# ---------------------------------------------------------------------------
# Core Simulator Engine
# ---------------------------------------------------------------------------

class VectorControlSimulator:
    """
    What-If Vector Control Impact Simulator.
    Runs area-based, saturation-response dengue case reduction scenarios
    for user-specified larvicide and fogging crew deployments across wards.
    """

    def __init__(self, resource_engine: DengueResourceEngine):
        self.engine = resource_engine
        self.routing_engine = HospitalOverflowRoutingEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_simulation(self, request: SimulationRequest) -> SimulationResult:
        """
        Executes the full What-If Simulation pipeline.
        Returns a fully populated SimulationResult (all offline, deterministic).
        """
        # 1. Validate crews constraint
        total_deployed = (
            sum(request.larvicide_crews.values()) +
            sum(request.fogging_crews.values())
        )
        if total_deployed > request.total_available_crews:
            raise ValueError(
                f"Total deployed crews ({total_deployed}) exceeds available "
                f"pool ({request.total_available_crews})."
            )

        # 2. Merge intervention params (allow per-request overrides)
        effective_params = copy.deepcopy(INTERVENTION_PARAMS)
        if request.intervention_params:
            for itype, overrides in request.intervention_params.items():
                if itype in effective_params:
                    effective_params[itype].update(overrides)
                else:
                    effective_params[itype] = overrides

        horizon = max(2, min(4, request.forecast_horizon_weeks))

        # 3. Build baseline ward forecast extended to horizon
        baseline_forecast = self._get_baseline_forecast(horizon)

        # Index by ward_id for fast lookup
        baseline_by_id: Dict[str, Dict] = {w["ward_id"]: w for w in baseline_forecast}

        # 4. Compute baseline hospital routing (for comparison)
        baseline_routing = self._compute_routing_for_wards(
            baseline_forecast, request.stock_percentage, "Baseline (No Intervention)"
        )

        # 5. Per-ward intervention simulation
        ward_results: List[Dict[str, Any]] = []
        for ward_id in request.selected_ward_ids:
            ward_base = baseline_by_id.get(ward_id)
            if ward_base is None:
                continue  # ward not in dataset — skip gracefully

            larv_crews = request.larvicide_crews.get(ward_id, 0)
            fog_crews = request.fogging_crews.get(ward_id, 0)

            result = self._simulate_ward(
                ward_base=ward_base,
                larvicide_crews=larv_crews,
                fogging_crews=fog_crews,
                horizon=horizon,
                deployment_start_week=request.deployment_start_week,
                params=effective_params,
                response_model=request.response_model,
            )
            ward_results.append(result)

        # 6. Compute adjusted forecasts for routing comparison
        adjusted_wards = self._build_adjusted_ward_list(
            baseline_forecast, ward_results
        )
        adjusted_routing = self._compute_routing_for_wards(
            adjusted_wards, request.stock_percentage, f"Adjusted ({request.scenario_name})"
        )

        # 7. Regional impact summary
        regional = self._compute_regional_summary(ward_results)

        # 8. Resource demand comparison (baseline vs adjusted, per ward)
        resource_comparison = self._build_resource_comparison(
            baseline_forecast, ward_results, request.selected_ward_ids
        )

        # 9. Crew deployment plan
        deployment_plan = self._build_deployment_plan(
            request, ward_results, total_deployed
        )

        # 10. ROI rankings
        actual_roi_ranking = self._rank_by_roi(ward_results)
        potential_roi_ranking = self.calculate_potential_roi_ranking(
            intervention_type="larvicide",
            horizon_weeks=horizon,
            reference_crews=1,
        )

        # 11. Hospital routing comparison
        routing_comparison = {
            "baseline": {
                "regional_summary": baseline_routing.get("regional_summary", {}),
                "critical_warnings": baseline_routing.get("critical_warnings", []),
            },
            "adjusted": {
                "regional_summary": adjusted_routing.get("regional_summary", {}),
                "critical_warnings": adjusted_routing.get("critical_warnings", []),
            },
            "delta": {
                "beds_demand_reduction": (
                    baseline_routing.get("regional_summary", {}).get("total_projected_bed_demand", 0) -
                    adjusted_routing.get("regional_summary", {}).get("total_projected_bed_demand", 0)
                ),
                "unresolved_deficit_reduction": (
                    baseline_routing.get("regional_summary", {}).get("total_unresolved_bed_deficit", 0) -
                    adjusted_routing.get("regional_summary", {}).get("total_unresolved_bed_deficit", 0)
                ),
            },
        }

        # 12. Critical warnings & dispatch notices
        critical_warnings = self._generate_critical_warnings(request, ward_results, effective_params)
        dispatch_notices = self._generate_dispatch_notices(request, ward_results)

        # 13. Assumptions
        assumptions = self._build_assumptions(effective_params, horizon)

        # 14. Scenario metadata
        now_str = datetime.utcnow().isoformat() + "Z"
        scenario_metadata = {
            "scenario_id": request.scenario_id,
            "scenario_name": request.scenario_name,
            "simulator_version": SIMULATOR_VERSION,
            "forecast_horizon_weeks": horizon,
            "planning_period": f"Upcoming {horizon} Weeks",
            "total_available_crews": request.total_available_crews,
            "total_deployed_crews": total_deployed,
            "remaining_crews": request.total_available_crews - total_deployed,
            "stock_percentage": request.stock_percentage,
            "assumption_status": "configured_simulation_assumption",
            "generated_at": now_str,
            "selected_ward_count": len(request.selected_ward_ids),
        }

        return SimulationResult(
            scenario_metadata=scenario_metadata,
            ward_intervention_results=ward_results,
            regional_impact_summary=regional,
            crew_deployment_plan=deployment_plan,
            intervention_roi_rankings=actual_roi_ranking,
            potential_roi_rankings=potential_roi_ranking,
            resource_demand_comparison=resource_comparison,
            hospital_routing_comparison=routing_comparison,
            critical_warnings=critical_warnings,
            dispatch_notices=dispatch_notices,
            assumptions_and_limitations=assumptions,
        )

    def optimize_crew_deployment(
        self,
        available_crews: int,
        intervention_type: str,
        horizon_weeks: int,
        ward_subset: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Greedy marginal-benefit crew deployment optimizer.
        Assigns each additional crew to the ward that yields the highest
        incremental case reduction at that moment (marginal benefit).
        Returns optimal allocation dict and expected total cases prevented.
        """
        horizon = max(2, min(4, horizon_weeks))
        baseline = self._get_baseline_forecast(horizon)

        wards = baseline
        if ward_subset:
            wards = [w for w in baseline if w["ward_id"] in ward_subset]

        params = INTERVENTION_PARAMS.get(intervention_type, INTERVENTION_PARAMS["larvicide"])
        allocation: Dict[str, int] = {w["ward_id"]: 0 for w in wards}

        def _marginal_benefit(ward: Dict, current_crews: int) -> float:
            """Cases prevented when adding 1 more crew to ward."""
            prev = self._simulate_ward(
                ward_base=ward,
                larvicide_crews=current_crews if intervention_type == "larvicide" else 0,
                fogging_crews=current_crews if intervention_type == "fogging" else 0,
                horizon=horizon,
                deployment_start_week=1,
                params=INTERVENTION_PARAMS,
                response_model="saturation",
            )["cases_prevented_total"]

            nxt = self._simulate_ward(
                ward_base=ward,
                larvicide_crews=current_crews + 1 if intervention_type == "larvicide" else 0,
                fogging_crews=current_crews + 1 if intervention_type == "fogging" else 0,
                horizon=horizon,
                deployment_start_week=1,
                params=INTERVENTION_PARAMS,
                response_model="saturation",
            )["cases_prevented_total"]

            return nxt - prev

        # Greedy one-by-one crew assignment
        for _ in range(available_crews):
            best_ward_id = None
            best_mb = -1.0
            for w in wards:
                wid = w["ward_id"]
                mb = _marginal_benefit(w, allocation[wid])
                if mb > best_mb:
                    best_mb = mb
                    best_ward_id = wid
            if best_ward_id is None or best_mb <= 0:
                break
            allocation[best_ward_id] += 1

        # Total prevented with optimized allocation
        total_prevented = 0.0
        for w in wards:
            wid = w["ward_id"]
            if allocation[wid] > 0:
                res = self._simulate_ward(
                    ward_base=w,
                    larvicide_crews=allocation[wid] if intervention_type == "larvicide" else 0,
                    fogging_crews=allocation[wid] if intervention_type == "fogging" else 0,
                    horizon=horizon,
                    deployment_start_week=1,
                    params=INTERVENTION_PARAMS,
                    response_model="saturation",
                )
                total_prevented += res["cases_prevented_total"]

        return {
            "intervention_type": intervention_type,
            "available_crews": available_crews,
            "ward_allocation": {wid: cnt for wid, cnt in allocation.items() if cnt > 0},
            "total_cases_prevented": round(total_prevented, 2),
            "algorithm": "marginal_benefit_greedy",
        }

    def calculate_potential_roi_ranking(
        self,
        intervention_type: str,
        horizon_weeks: int,
        reference_crews: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates every ward with `reference_crews` and ranks by ROI
        (cases prevented per crew deployed). Used for opportunity mapping.
        """
        horizon = max(2, min(4, horizon_weeks))
        baseline = self._get_baseline_forecast(horizon)

        rankings = []
        for w in baseline:
            wid = w["ward_id"]
            larv = reference_crews if intervention_type == "larvicide" else 0
            fog = reference_crews if intervention_type == "fogging" else 0
            res = self._simulate_ward(
                ward_base=w,
                larvicide_crews=larv,
                fogging_crews=fog,
                horizon=horizon,
                deployment_start_week=1,
                params=INTERVENTION_PARAMS,
                response_model="saturation",
            )
            roi = self._calculate_roi(res["cases_prevented_total"], reference_crews)
            rankings.append({
                "ward_id": wid,
                "locality": w.get("locality", wid),
                "city": w.get("city", ""),
                "risk_level": w.get("risk_level", "Low"),
                "reference_crews": reference_crews,
                "intervention_type": intervention_type,
                "cases_prevented_potential": round(res["cases_prevented_total"], 2),
                "roi": round(roi, 2) if roi is not None else None,
            })

        rankings.sort(key=lambda x: (x["roi"] or 0.0), reverse=True)
        for i, r in enumerate(rankings, 1):
            r["potential_rank"] = i

        return rankings

    # ------------------------------------------------------------------
    # Forecast Extension
    # ------------------------------------------------------------------

    def _get_baseline_forecast(self, horizon_weeks: int) -> List[Dict]:
        """
        Returns the 2-4 week ward forecast.
        Weeks 1-2: from DengueResourceEngine base forecasts (ML predictions).
        Weeks 3-4: recursive deterministic extension using seasonal growth factor.
        Growth factor = 1 + (0.05 + 0.15 * vulnerability_factor).
        """
        base = [dict(w) for w in self.engine._base_ward_forecasts]

        for w in base:
            w1 = w["predicted_cases_w1"]
            w2 = w["predicted_cases_w2"]

            # Reconstruct vulnerability factor from stored ward data
            # (same formula as resource_engine._generate_base_forecasts)
            waterlog = 0.5  # default; real values not stored separately
            sanitation = 0.5
            # Approximate: use risk_score as a proxy for vulnerability
            # risk_score: High=1.0, Medium=0.6, Low=0.3
            vuln = (w.get("risk_score", 0.6) - 0.3) / 0.7  # normalize 0.3-1.0 -> 0-1
            vuln = max(0.0, min(1.0, vuln))

            growth = 1.0 + 0.05 + 0.15 * vuln

            w["forecast_weeks"] = [
                {"week": 1, "cases": w1, "forecast_method": "ml_base"},
                {"week": 2, "cases": w2, "forecast_method": "ml_base"},
            ]

            if horizon_weeks >= 3:
                w3 = round(max(0.0, w2 * growth), 4)
                w["forecast_weeks"].append({"week": 3, "cases": w3, "forecast_method": "ml_extended_recursive"})
            else:
                w3 = w2

            if horizon_weeks >= 4:
                w4 = round(max(0.0, w3 * growth), 4)
                w["forecast_weeks"].append({"week": 4, "cases": w4, "forecast_method": "ml_extended_recursive"})

        return base

    # ------------------------------------------------------------------
    # Ward-Level Simulation
    # ------------------------------------------------------------------

    def _simulate_ward(
        self,
        ward_base: Dict,
        larvicide_crews: int,
        fogging_crews: int,
        horizon: int,
        deployment_start_week: int,
        params: Dict[str, Any],
        response_model: str,
    ) -> Dict[str, Any]:
        """
        Simulates the week-by-week impact of larvicide and fogging crews on a single ward.
        Returns a dict with all computed fields for that ward.
        """
        ward_id = ward_base["ward_id"]
        ward_area = ward_base.get("ward_area_sqkm") or WARD_AREAS.get(ward_id, 2.0)

        larv_params = params["larvicide"]
        fog_params = params["fogging"]

        # Coverage for each intervention type
        larv_cov = self._calculate_coverage(ward_base, larvicide_crews, larv_params, ward_area)
        fog_cov = self._calculate_coverage(ward_base, fogging_crews, fog_params, ward_area)

        larv_resp = (
            self._apply_saturation_response(larv_cov["coverage_ratio"], larv_params["saturation_parameter"])
            if response_model == "saturation" else larv_cov["coverage_ratio"]
        )
        fog_resp = (
            self._apply_saturation_response(fog_cov["coverage_ratio"], fog_params["saturation_parameter"])
            if response_model == "saturation" else fog_cov["coverage_ratio"]
        )

        # Week-by-week simulation
        weekly_data = []
        weekly_cases_baseline = [fw["cases"] for fw in ward_base["forecast_weeks"]]

        total_baseline = sum(weekly_cases_baseline)
        total_adjusted = 0.0
        total_prevented = 0.0

        for week_idx in range(horizon):
            week_num = week_idx + 1
            baseline_cases = weekly_cases_baseline[week_idx]

            # Only apply intervention from deployment_start_week onward
            if week_num < deployment_start_week:
                adjusted_cases = baseline_cases
                larv_reduction = 0.0
                fog_reduction = 0.0
                combined_reduction = 0.0
            else:
                # Map week_num -> impact_factor index (0-based, capped at len-1)
                impact_idx = min(week_num - deployment_start_week, len(larv_params["weekly_impact_factors"]) - 1)
                larv_impact_factor = larv_params["weekly_impact_factors"][impact_idx]

                fog_impact_idx = min(week_num - deployment_start_week, len(fog_params["weekly_impact_factors"]) - 1)
                fog_impact_factor = fog_params["weekly_impact_factors"][fog_impact_idx]

                larv_reduction = self._calculate_weekly_reduction(
                    larv_resp, larv_params["max_effectiveness"], larv_impact_factor
                )
                fog_reduction = self._calculate_weekly_reduction(
                    fog_resp, fog_params["max_effectiveness"], fog_impact_factor
                )
                combined_reduction = self._combine_reductions(larv_reduction, fog_reduction)
                adjusted_cases = round(max(0.0, baseline_cases * (1.0 - combined_reduction)), 4)

            cases_prevented_this_week = round(max(0.0, baseline_cases - adjusted_cases), 4)
            total_adjusted += adjusted_cases
            total_prevented += cases_prevented_this_week

            weekly_data.append({
                "week": week_num,
                "baseline_cases": round(baseline_cases, 4),
                "adjusted_cases": round(adjusted_cases, 4),
                "cases_prevented": round(cases_prevented_this_week, 4),
                "larvicide_reduction": round(larv_reduction, 6) if week_num >= deployment_start_week else 0.0,
                "fogging_reduction": round(fog_reduction, 6) if week_num >= deployment_start_week else 0.0,
                "combined_reduction": round(combined_reduction, 6) if week_num >= deployment_start_week else 0.0,
                "forecast_method": ward_base["forecast_weeks"][week_idx]["forecast_method"],
            })

        total_adjusted = round(total_adjusted, 4)
        total_prevented = round(total_prevented, 4)

        # Resource demand — baseline vs adjusted
        baseline_saline, baseline_kits, baseline_beds = self.engine.calculate_ward_demand(total_baseline)
        adj_saline, adj_kits, adj_beds = self.engine.calculate_ward_demand(total_adjusted)
        saline_saved = max(0, baseline_saline - adj_saline)
        kits_saved = max(0, baseline_kits - adj_kits)
        beds_saved = max(0, baseline_beds - adj_beds)

        total_crews = larvicide_crews + fogging_crews
        roi = self._calculate_roi(total_prevented, total_crews)

        risk_level = ward_base.get("risk_level", classify_risk_level(total_baseline / max(1, horizon)))

        # Coverage display
        larv_pct = round(larv_cov["coverage_ratio"] * 100, 2)
        fog_pct = round(fog_cov["coverage_ratio"] * 100, 2)

        return {
            "ward_id": ward_id,
            "locality": ward_base.get("locality", ward_id),
            "city": ward_base.get("city", ""),
            "risk_level": risk_level,
            "risk_score": ward_base.get("risk_score", get_risk_score(risk_level)),
            "ward_area_sqkm": round(ward_area, 2),
            # Crew deployment
            "larvicide_crews": larvicide_crews,
            "fogging_crews": fogging_crews,
            "total_crews_deployed": total_crews,
            # Coverage
            "larvicide_coverage_pct": larv_pct,
            "fogging_coverage_pct": fog_pct,
            "larvicide_coverage_ratio": round(larv_cov["coverage_ratio"], 4),
            "fogging_coverage_ratio": round(fog_cov["coverage_ratio"], 4),
            "larvicide_coverage_response": round(larv_resp, 4),
            "fogging_coverage_response": round(fog_resp, 4),
            # Case totals
            "baseline_total_cases": round(total_baseline, 4),
            "adjusted_total_cases": round(total_adjusted, 4),
            "cases_prevented_total": round(total_prevented, 4),
            "case_reduction_pct": round(
                (total_prevented / total_baseline * 100.0) if total_baseline > 0 else 0.0, 2
            ),
            # Resource savings
            "baseline_saline_demand": baseline_saline,
            "adjusted_saline_demand": adj_saline,
            "saline_bags_saved": saline_saved,
            "baseline_beds_demand": baseline_beds,
            "adjusted_beds_demand": adj_beds,
            "beds_saved": beds_saved,
            "baseline_kits_demand": baseline_kits,
            "adjusted_kits_demand": adj_kits,
            "diagnostic_kits_saved": kits_saved,
            # ROI
            "roi": round(roi, 4) if roi is not None else None,
            # Weekly breakdown
            "weekly_breakdown": weekly_data,
        }

    # ------------------------------------------------------------------
    # Math Helpers
    # ------------------------------------------------------------------

    def _calculate_coverage(
        self,
        ward: Dict,
        crews: int,
        params: Dict,
        ward_area: float,
    ) -> Dict[str, float]:
        """
        Computes coverage ratio = (crews * coverage_capacity) / ward_area.
        Fallback when ward_area is unavailable: use crews / required_crews.
        Returns dict with coverage_ratio (capped at 1.0) and covered_area.
        """
        cap_per_crew = params.get(
            "coverage_capacity_sqkm_per_crew",
            DEFAULT_COEFFICIENTS["crew_coverage_sqkm"],
        )
        covered_area = crews * cap_per_crew

        if ward_area and ward_area > 0:
            ratio = covered_area / ward_area
        else:
            # Fallback: use required crews denominator
            required = max(1, int(math.ceil(ward_area / cap_per_crew))) if ward_area else max(1, crews)
            ratio = crews / required

        ratio = min(1.0, max(0.0, ratio))
        return {
            "coverage_ratio": ratio,
            "covered_area_sqkm": round(covered_area, 4),
            "ward_area_sqkm": ward_area,
        }

    def _apply_saturation_response(self, coverage_ratio: float, k: float) -> float:
        """
        Bounded exponential saturation: (1 - exp(-k * r)) / (1 - exp(-k)).
        Degrades to linear when k = 0 (avoids division by zero).
        """
        r = max(0.0, min(1.0, coverage_ratio))
        if abs(k) < 1e-9:
            return r  # linear fallback
        numerator = 1.0 - math.exp(-k * r)
        denominator = 1.0 - math.exp(-k)
        if abs(denominator) < 1e-12:
            return r
        return max(0.0, min(1.0, numerator / denominator))

    def _calculate_weekly_reduction(
        self,
        coverage_response: float,
        max_effectiveness: float,
        impact_factor: float,
    ) -> float:
        """Fractional case reduction for a single week."""
        return coverage_response * max_effectiveness * impact_factor

    def _combine_reductions(self, larv_red: float, fog_red: float) -> float:
        """
        Bounded combination: 1 - (1 - larv_red) * (1 - fog_red).
        Ensures total reduction cannot exceed 100%.
        """
        combined = 1.0 - (1.0 - larv_red) * (1.0 - fog_red)
        return max(0.0, min(1.0, combined))

    def _calculate_roi(self, cases_prevented: float, total_crews: int) -> Optional[float]:
        """Cases prevented per crew deployed. None if no crews."""
        if total_crews <= 0:
            return None
        return cases_prevented / total_crews

    # ------------------------------------------------------------------
    # Summary Builders
    # ------------------------------------------------------------------

    def _compute_regional_summary(self, ward_results: List[Dict]) -> Dict[str, Any]:
        total_prevented = sum(r["cases_prevented_total"] for r in ward_results)
        total_beds_saved = sum(r["beds_saved"] for r in ward_results)
        total_saline_saved = sum(r["saline_bags_saved"] for r in ward_results)
        total_kits_saved = sum(r["diagnostic_kits_saved"] for r in ward_results)
        total_crews = sum(r["total_crews_deployed"] for r in ward_results)
        overall_roi = self._calculate_roi(total_prevented, total_crews)

        return {
            "total_cases_prevented": round(total_prevented, 2),
            "total_beds_saved": total_beds_saved,
            "total_saline_bags_saved": total_saline_saved,
            "total_diagnostic_kits_saved": total_kits_saved,
            "total_crews_deployed": total_crews,
            "overall_roi": round(overall_roi, 4) if overall_roi is not None else None,
            "wards_simulated": len(ward_results),
        }

    def _build_deployment_plan(
        self,
        request: SimulationRequest,
        ward_results: List[Dict],
        total_deployed: int,
    ) -> Dict[str, Any]:
        per_ward = []
        for wr in ward_results:
            per_ward.append({
                "ward_id": wr["ward_id"],
                "locality": wr["locality"],
                "city": wr["city"],
                "larvicide_crews": wr["larvicide_crews"],
                "fogging_crews": wr["fogging_crews"],
                "total_crews": wr["total_crews_deployed"],
                "larvicide_coverage_pct": wr["larvicide_coverage_pct"],
                "fogging_coverage_pct": wr["fogging_coverage_pct"],
            })

        return {
            "scenario_id": request.scenario_id,
            "total_available_crews": request.total_available_crews,
            "total_deployed": total_deployed,
            "remaining_crews": request.total_available_crews - total_deployed,
            "per_ward": per_ward,
        }

    def _rank_by_roi(self, ward_results: List[Dict]) -> List[Dict[str, Any]]:
        ranked = sorted(ward_results, key=lambda x: (x["roi"] or 0.0), reverse=True)
        result = []
        for i, wr in enumerate(ranked, 1):
            result.append({
                "rank": i,
                "ward_id": wr["ward_id"],
                "locality": wr["locality"],
                "city": wr["city"],
                "risk_level": wr["risk_level"],
                "larvicide_crews": wr["larvicide_crews"],
                "fogging_crews": wr["fogging_crews"],
                "cases_prevented": round(wr["cases_prevented_total"], 2),
                "roi": wr["roi"],
            })
        return result

    def _build_resource_comparison(
        self,
        baseline_forecast: List[Dict],
        ward_results: List[Dict],
        selected_ward_ids: List[str],
    ) -> List[Dict[str, Any]]:
        ward_result_by_id = {wr["ward_id"]: wr for wr in ward_results}
        baseline_by_id = {w["ward_id"]: w for w in baseline_forecast}
        comparison = []

        for ward_id in selected_ward_ids:
            wr = ward_result_by_id.get(ward_id)
            wb = baseline_by_id.get(ward_id)
            if not wr or not wb:
                continue

            comparison.append({
                "ward_id": ward_id,
                "locality": wr["locality"],
                "city": wr["city"],
                "baseline": {
                    "total_cases": round(wr["baseline_total_cases"], 2),
                    "saline_demand": wr["baseline_saline_demand"],
                    "beds_demand": wr["baseline_beds_demand"],
                    "kits_demand": wr["baseline_kits_demand"],
                },
                "adjusted": {
                    "total_cases": round(wr["adjusted_total_cases"], 2),
                    "saline_demand": wr["adjusted_saline_demand"],
                    "beds_demand": wr["adjusted_beds_demand"],
                    "kits_demand": wr["adjusted_kits_demand"],
                },
                "saved": {
                    "cases_prevented": round(wr["cases_prevented_total"], 2),
                    "saline_bags_saved": wr["saline_bags_saved"],
                    "beds_saved": wr["beds_saved"],
                    "kits_saved": wr["diagnostic_kits_saved"],
                },
            })

        return comparison

    def _build_adjusted_ward_list(
        self,
        baseline_forecast: List[Dict],
        ward_results: List[Dict],
    ) -> List[Dict]:
        """
        Returns a copy of the baseline forecast where selected wards have
        their total predicted cases replaced with adjusted values.
        """
        result_by_id = {wr["ward_id"]: wr for wr in ward_results}
        adjusted = []
        for w in baseline_forecast:
            wc = dict(w)
            wid = wc["ward_id"]
            if wid in result_by_id:
                wr = result_by_id[wid]
                # Distribute adjusted cases proportionally across week slots
                orig_total = max(0.001, wr["baseline_total_cases"])
                adj_total = wr["adjusted_total_cases"]
                ratio = adj_total / orig_total
                wc["total_predicted_cases"] = round(adj_total, 4)
                wc["predicted_cases_w1"] = round(wc["predicted_cases_w1"] * ratio, 4)
                wc["predicted_cases_w2"] = round(wc["predicted_cases_w2"] * ratio, 4)
            adjusted.append(wc)
        return adjusted

    def _compute_routing_for_wards(
        self,
        ward_forecast: List[Dict],
        stock_percentage: float,
        scenario_name: str,
    ) -> Dict[str, Any]:
        """Builds hospital routing result for a list of ward forecasts."""
        # Add beds_demand to each ward for contract building
        wards_with_demand = []
        for w in ward_forecast:
            wc = dict(w)
            total_cases = wc.get("total_predicted_cases", 0.0)
            _, _, beds_demand = self.engine.calculate_ward_demand(total_cases)
            wc["beds_demand"] = beds_demand
            wards_with_demand.append(wc)

        contract = HospitalOverflowRoutingEngine.build_shared_contract_from_engine_wards(
            wards_with_demand, stock_percentage=stock_percentage
        )
        return self.routing_engine.calculate_overflow_routing(
            contract,
            scenario_name=scenario_name,
        )

    # ------------------------------------------------------------------
    # Warnings and Notices
    # ------------------------------------------------------------------

    def _generate_critical_warnings(
        self,
        request: SimulationRequest,
        ward_results: List[Dict],
        params: Dict,
    ) -> List[str]:
        warnings = []

        for wr in ward_results:
            if wr["total_crews_deployed"] == 0:
                warnings.append(
                    f"Ward {wr['ward_id']} ({wr['locality']}): No crews deployed — zero intervention impact."
                )

            larv_cov = wr["larvicide_coverage_ratio"]
            fog_cov = wr["fogging_coverage_ratio"]

            if wr["larvicide_crews"] > 0 and larv_cov < 0.5:
                warnings.append(
                    f"Ward {wr['ward_id']} ({wr['locality']}): Larvicide coverage is only "
                    f"{round(larv_cov * 100, 1)}% — below 50% threshold for effective suppression."
                )
            if wr["fogging_crews"] > 0 and fog_cov < 0.5:
                warnings.append(
                    f"Ward {wr['ward_id']} ({wr['locality']}): Fogging coverage is only "
                    f"{round(fog_cov * 100, 1)}% — below 50% threshold for effective suppression."
                )
            if wr["risk_level"] == "High" and wr["total_crews_deployed"] == 0:
                warnings.append(
                    f"CRITICAL: High-risk ward {wr['ward_id']} ({wr['locality']}) has no crew deployment planned."
                )

        total_deployed = sum(r["total_crews_deployed"] for r in ward_results)
        if total_deployed > request.total_available_crews:
            warnings.append(
                f"ALERT: Total deployed crews ({total_deployed}) exceeds pool ({request.total_available_crews})."
            )

        return warnings

    def _generate_dispatch_notices(
        self,
        request: SimulationRequest,
        ward_results: List[Dict],
    ) -> List[str]:
        """
        Generates fully offline, template-based dispatch notices (one per ward with any crews).
        """
        DISPATCH_TEMPLATE = (
            "VECTOR CONTROL DEPLOYMENT NOTICE\n"
            "Scenario: {scenario_name}\n"
            "Ward: {ward_name} ({city})\n"
            "Risk Level: {risk_level}\n"
            "Larvicide Crews: {larvicide_crews}\n"
            "Fogging Crews: {fogging_crews}\n"
            "Coverage: {coverage_pct}%\n"
            "Baseline Cases: {baseline_cases}\n"
            "Adjusted Cases: {adjusted_cases}\n"
            "Cases Prevented: {cases_prevented}\n"
            "Beds Saved: {beds_saved}\n"
            "Saline Saved: {saline_saved}\n"
            "ROI: {roi}\n"
            "Status: {approval_status}\n"
            "NOTE: Modeled estimates under configured assumptions."
        )

        notices = []
        for wr in ward_results:
            if wr["total_crews_deployed"] == 0:
                continue

            # Combined max coverage for display
            cov_pct = round(
                max(wr["larvicide_coverage_pct"], wr["fogging_coverage_pct"]), 1
            )
            roi_display = f"{round(wr['roi'], 2)}" if wr["roi"] is not None else "N/A"

            notice = DISPATCH_TEMPLATE.format(
                scenario_name=request.scenario_name,
                ward_name=wr.get("locality", wr["ward_id"]),
                city=wr.get("city", ""),
                risk_level=wr["risk_level"],
                larvicide_crews=wr["larvicide_crews"],
                fogging_crews=wr["fogging_crews"],
                coverage_pct=cov_pct,
                baseline_cases=round(wr["baseline_total_cases"], 1),
                adjusted_cases=round(wr["adjusted_total_cases"], 1),
                cases_prevented=round(wr["cases_prevented_total"], 2),
                beds_saved=wr["beds_saved"],
                saline_saved=wr["saline_bags_saved"],
                roi=roi_display,
                approval_status="Pending",
            )
            notices.append(notice)

        return notices

    def _build_assumptions(self, params: Dict, horizon: int) -> List[str]:
        return [
            "All calculations are fully local — no network calls or external APIs used.",
            "Forecast for weeks 1-2 is ML-based (DengueResourceEngine baseline).",
            "Forecast for weeks 3-4 (if requested) is a recursive deterministic extension using seasonal growth factor.",
            f"Larvicide: max_effectiveness={params['larvicide']['max_effectiveness']}, "
            f"saturation_parameter={params['larvicide']['saturation_parameter']}, "
            f"parameter_version={params['larvicide']['parameter_version']}.",
            f"Fogging: max_effectiveness={params['fogging']['max_effectiveness']}, "
            f"saturation_parameter={params['fogging']['saturation_parameter']}, "
            f"parameter_version={params['fogging']['parameter_version']}.",
            "Coverage ratio = (crews * coverage_capacity_sqkm_per_crew) / ward_area, capped at 1.0.",
            "Combined intervention reduction uses bounded formula: 1 - (1 - larv_red) * (1 - fog_red).",
            "Saturation response: (1 - exp(-k * r)) / (1 - exp(-k)); linear when k=0.",
            "Identical inputs produce identical outputs (determinism guaranteed).",
            "Resource savings computed using DEFAULT_COEFFICIENTS from DengueResourceEngine.",
            f"Forecast horizon: {horizon} week(s). assumption_status=configured_simulation_assumption.",
        ]


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def create_simulation_request(
    scenario_name: str,
    selected_ward_ids: List[str],
    larvicide_crews: Dict[str, int],
    fogging_crews: Dict[str, int],
    total_available_crews: int,
    forecast_horizon_weeks: int = 4,
    deployment_start_week: int = 1,
    stock_percentage: float = 100.0,
    intervention_params: Optional[Dict[str, Any]] = None,
    response_model: str = "saturation",
    scenario_id: Optional[str] = None,
) -> SimulationRequest:
    """Convenience constructor with auto-generated scenario_id."""
    return SimulationRequest(
        scenario_id=scenario_id or str(uuid.uuid4()),
        scenario_name=scenario_name,
        forecast_horizon_weeks=forecast_horizon_weeks,
        deployment_start_week=deployment_start_week,
        selected_ward_ids=selected_ward_ids,
        larvicide_crews=larvicide_crews,
        fogging_crews=fogging_crews,
        total_available_crews=total_available_crews,
        stock_percentage=stock_percentage,
        intervention_params=intervention_params,
        response_model=response_model,
    )
