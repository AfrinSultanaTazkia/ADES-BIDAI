"""
ADES BIDAI - SQLite Database and SQLAlchemy ORM Models
Provides persistent audit logging, allocation plan persistence, and transfer history.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "ades_bidai_allocations.db")

Base = declarative_base()


class AllocationPlan(Base):
    __tablename__ = "allocation_plans"

    id = Column(Integer, primary_key=True)
    plan_name = Column(String(100), default="National Dengue Resource Plan")
    status = Column(String(50), default="Approved")
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(100), default="Central Health Administrator")
    stock_percentage = Column(Float, default=100.0)
    total_spraying_crews = Column(Integer, default=150)
    total_predicted_cases = Column(Float, default=0.0)
    total_saline_demand = Column(Integer, default=0)
    total_saline_allocated = Column(Integer, default=0)
    total_kits_demand = Column(Integer, default=0)
    total_kits_allocated = Column(Integer, default=0)
    total_beds_demand = Column(Integer, default=0)
    total_beds_allocated = Column(Integer, default=0)
    total_crews_assigned = Column(Integer, default=0)
    critical_deficits_count = Column(Integer, default=0)

    ward_records = relationship("WardAllocationRecord", back_populates="plan", cascade="all, delete-orphan")


class WardAllocationRecord(Base):
    __tablename__ = "ward_allocation_records"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("allocation_plans.id"), nullable=False)
    ward_id = Column(String(50), nullable=False)
    locality = Column(String(100))
    city = Column(String(100))
    priority_ranking = Column(Integer)
    priority_score = Column(Float)
    risk_level = Column(String(20))
    saline_demand = Column(Integer)
    saline_allocated = Column(Integer)
    saline_deficit = Column(Integer)
    kits_demand = Column(Integer)
    kits_allocated = Column(Integer)
    kits_deficit = Column(Integer)
    beds_demand = Column(Integer)
    beds_allocated = Column(Integer)
    beds_deficit = Column(Integer)
    crews_required = Column(Integer)
    crews_assigned = Column(Integer)
    crew_deficit = Column(Integer)

    plan = relationship("AllocationPlan", back_populates="ward_records")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(100), nullable=False)
    ward_id = Column(String(50), nullable=True)
    user = Column(String(100), default="Central Health Administrator")
    details = Column(Text, nullable=False)


class RedistributionTransfer(Base):
    __tablename__ = "redistribution_transfers"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    resource_type = Column(String(50), nullable=False)
    source_ward_id = Column(String(50), nullable=False)
    destination_ward_id = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(50), default="Approved")


class HospitalRoutingPlan(Base):
    __tablename__ = "hospital_routing_plans"

    id = Column(Integer, primary_key=True)
    plan_name = Column(String(100), default="Official Hospital Overflow Routing Plan")
    status = Column(String(50), default="Approved")  # Approved, Revalidation Required, Rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(100), default="Central Health Administrator")
    stock_percentage = Column(Float, default=100.0)
    total_projected_demand = Column(Integer, default=0)
    total_effective_capacity = Column(Integer, default=0)
    total_initial_deficit = Column(Integer, default=0)
    total_routed_overflow = Column(Integer, default=0)
    total_net_deficit = Column(Integer, default=0)
    shortage_resolution_percentage = Column(Float, default=0.0)
    routing_data_json = Column(Text, nullable=False)

    routing_records = relationship("HospitalRoutingRecord", back_populates="plan", cascade="all, delete-orphan")


class HospitalRoutingRecord(Base):
    __tablename__ = "hospital_routing_records"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("hospital_routing_plans.id"), nullable=False)
    source_ward_id = Column(String(50), nullable=False)
    destination_ward_id = Column(String(50), nullable=False)
    city = Column(String(100), nullable=False)
    routed_overflow = Column(Integer, nullable=False)
    approval_status = Column(String(50), default="Approved")

    plan = relationship("HospitalRoutingPlan", back_populates="routing_records")


class VectorControlPlan(Base):
    __tablename__ = "vector_control_plans"

    id = Column(Integer, primary_key=True)
    plan_name = Column(String(100), default="Official Vector Control Deployment Plan")
    status = Column(String(50), default="Approved")
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(100), default="Central Health Administrator")
    forecast_horizon_weeks = Column(Integer, default=4)
    total_available_crews = Column(Integer, default=150)
    total_deployed_crews = Column(Integer, default=0)
    total_cases_prevented = Column(Float, default=0.0)
    total_beds_saved = Column(Integer, default=0)
    total_saline_bags_saved = Column(Integer, default=0)
    overall_roi = Column(Float, default=0.0)
    simulation_data_json = Column(Text, nullable=False)


# Engine & Session Setup
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initializes tables in sqlite database if they do not exist."""
    Base.metadata.create_all(bind=engine)


def log_audit(
    action: str,
    details: str,
    ward_id: Optional[str] = None,
    user: str = "Central Health Administrator"
) -> int:
    """Records an audit log entry in the persistent SQLite database."""
    session = SessionLocal()
    try:
        entry = AuditLog(
            action=action,
            details=details,
            ward_id=ward_id,
            user=user,
            timestamp=datetime.utcnow()
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry.id
    finally:
        session.close()


def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves chronological audit logs."""
    session = SessionLocal()
    try:
        logs = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() + "Z",
                "action": log.action,
                "ward_id": log.ward_id,
                "user": log.user,
                "details": log.details,
            }
            for log in logs
        ]
    finally:
        session.close()


def save_approved_plan(
    plan_result: Dict[str, Any],
    plan_name: str = "Official Regional Dengue Plan",
    approved_by: str = "Central Health Administrator"
) -> int:
    """Saves an administrator-approved allocation plan and its ward records into SQLite."""
    session = SessionLocal()
    try:
        overview = plan_result["regional_overview"]
        scarcity = plan_result["scarcity_controls"]

        plan = AllocationPlan(
            plan_name=plan_name,
            status="Approved",
            created_at=datetime.utcnow(),
            approved_at=datetime.utcnow(),
            approved_by=approved_by,
            stock_percentage=scarcity.get("selected_stock_percentage", 100.0),
            total_spraying_crews=scarcity.get("total_spraying_crews", 150),
            total_predicted_cases=overview.get("total_predicted_cases", 0.0),
            total_saline_demand=overview.get("total_saline_demand", 0),
            total_saline_allocated=overview.get("total_saline_allocated", 0),
            total_kits_demand=overview.get("total_kits_demand", 0),
            total_kits_allocated=overview.get("total_kits_allocated", 0),
            total_beds_demand=overview.get("total_beds_demand", 0),
            total_beds_allocated=overview.get("total_beds_allocated", 0),
            total_crews_assigned=overview.get("total_assigned_crews", 0),
            critical_deficits_count=overview.get("critical_supply_wards_count", 0),
        )
        session.add(plan)
        session.flush()

        for w in plan_result["wards"]:
            rec = WardAllocationRecord(
                plan_id=plan.id,
                ward_id=w["ward_id"],
                locality=w.get("locality", w["ward_id"]),
                city=w.get("city", "Dhaka"),
                priority_ranking=w.get("priority_ranking", 0),
                priority_score=w.get("priority_score", 0.0),
                risk_level=w.get("risk_level", "Low"),
                saline_demand=w.get("saline_demand", 0),
                saline_allocated=w.get("approved_saline_allocation", 0),
                saline_deficit=w.get("remaining_saline_deficit", 0),
                kits_demand=w.get("kits_demand", 0),
                kits_allocated=w.get("approved_kits_allocation", 0),
                kits_deficit=w.get("remaining_kits_deficit", 0),
                beds_demand=w.get("beds_demand", 0),
                beds_allocated=w.get("approved_beds_allocation", 0),
                beds_deficit=w.get("remaining_beds_deficit", 0),
                crews_required=w.get("required_crews", 0),
                crews_assigned=w.get("approved_crew_allocation", 0),
                crew_deficit=w.get("crew_deficit", 0),
            )
            session.add(rec)

        session.commit()

        # Log audit entry
        log_audit(
            action="APPROVE_ALLOCATION_PLAN",
            details=f"Plan '{plan_name}' (ID: {plan.id}) approved with {scarcity.get('selected_stock_percentage')}% stock and {scarcity.get('total_spraying_crews')} crews. Critical deficits: {overview.get('critical_supply_wards_count')}.",
            user=approved_by,
        )

        return plan.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def record_redistribution(
    resource_type: str,
    source_ward_id: str,
    destination_ward_id: str,
    quantity: int,
    reason: str,
    status: str = "Approved",
    user: str = "Central Health Administrator"
) -> int:
    """Records an inter-ward resource transfer in the audit log and transfer history table."""
    session = SessionLocal()
    try:
        transfer = RedistributionTransfer(
            resource_type=resource_type,
            source_ward_id=source_ward_id,
            destination_ward_id=destination_ward_id,
            quantity=quantity,
            reason=reason,
            status=status,
            timestamp=datetime.utcnow()
        )
        session.add(transfer)
        session.commit()
        session.refresh(transfer)

        log_audit(
            action="REDISTRIBUTION_TRANSFER",
            details=f"Transferred {quantity} units of {resource_type} from {source_ward_id} to {destination_ward_id}. Reason: {reason}",
            ward_id=destination_ward_id,
            user=user
        )

        return transfer.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_approved_hospital_plan(
    routing_result: Dict[str, Any],
    plan_name: str = "Official Hospital Overflow Routing Plan",
    approved_by: str = "Central Health Administrator",
    stock_percentage: float = 100.0,
) -> int:
    """Saves an administrator-approved hospital overflow routing plan to SQLite."""
    session = SessionLocal()
    try:
        reg = routing_result.get("regional_summary", {})
        assignments = routing_result.get("routing_assignments", [])

        plan = HospitalRoutingPlan(
            plan_name=plan_name,
            status="Approved",
            created_at=datetime.utcnow(),
            approved_at=datetime.utcnow(),
            approved_by=approved_by,
            stock_percentage=stock_percentage,
            total_projected_demand=reg.get("total_projected_bed_demand", 0),
            total_effective_capacity=reg.get("total_effective_bed_capacity", 0),
            total_initial_deficit=reg.get("total_initial_bed_deficit", 0),
            total_routed_overflow=reg.get("total_routed_overflow", 0),
            total_net_deficit=reg.get("total_unresolved_bed_deficit", 0),
            shortage_resolution_percentage=reg.get("overall_shortage_resolution_percentage", 0.0) or 0.0,
            routing_data_json=json.dumps(routing_result),
        )
        session.add(plan)
        session.flush()

        for a in assignments:
            rec = HospitalRoutingRecord(
                plan_id=plan.id,
                source_ward_id=a["source_ward_id"],
                destination_ward_id=a["destination_ward_id"],
                city=a["city"],
                routed_overflow=a["routed_overflow"],
                approval_status="Approved",
            )
            session.add(rec)

        session.commit()

        log_audit(
            action="APPROVE_HOSPITAL_ROUTING_PLAN",
            details=f"Hospital routing plan '{plan_name}' (ID: {plan.id}) approved. Routed: {reg.get('total_routed_overflow')} beds. Unresolved deficit: {reg.get('total_unresolved_bed_deficit')} beds.",
            user=approved_by,
        )

        return plan.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_approved_hospital_plans(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves list of saved hospital routing plans."""
    session = SessionLocal()
    try:
        plans = session.query(HospitalRoutingPlan).order_by(HospitalRoutingPlan.created_at.desc()).limit(limit).all()
        return [
            {
                "id": p.id,
                "plan_name": p.plan_name,
                "status": p.status,
                "created_at": p.created_at.isoformat() + "Z" if p.created_at else None,
                "approved_at": p.approved_at.isoformat() + "Z" if p.approved_at else None,
                "approved_by": p.approved_by,
                "stock_percentage": p.stock_percentage,
                "total_projected_demand": p.total_projected_demand,
                "total_effective_capacity": p.total_effective_capacity,
                "total_initial_deficit": p.total_initial_deficit,
                "total_routed_overflow": p.total_routed_overflow,
                "total_net_deficit": p.total_net_deficit,
                "shortage_resolution_percentage": p.shortage_resolution_percentage,
            }
            for p in plans
        ]
    finally:
        session.close()


def revalidate_hospital_plans(reason: str = "Capacity or demand altered") -> int:
    """Marks existing approved hospital plans as Revalidation Required when underlying inputs change."""
    session = SessionLocal()
    try:
        count = session.query(HospitalRoutingPlan).filter(HospitalRoutingPlan.status == "Approved").update(
            {"status": "Revalidation Required"}
        )
        session.commit()
        if count > 0:
            log_audit(
                action="REVALIDATE_HOSPITAL_PLANS",
                details=f"Marked {count} approved hospital routing plan(s) as 'Revalidation Required'. Reason: {reason}",
            )
        return count
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_approved_vector_plan(
    plan_name: str,
    approved_by: str,
    simulation_result: Dict[str, Any],
) -> int:
    """Persists an approved vector control deployment plan into the SQLite database."""
    session = SessionLocal()
    try:
        meta = simulation_result.get("scenario_metadata", {})
        regional = simulation_result.get("regional_impact_summary", {})

        plan = VectorControlPlan(
            plan_name=plan_name,
            approved_by=approved_by,
            status="Approved",
            created_at=datetime.utcnow(),
            approved_at=datetime.utcnow(),
            forecast_horizon_weeks=meta.get("forecast_horizon_weeks", 4),
            total_available_crews=meta.get("total_available_crews", 150),
            total_deployed_crews=meta.get("total_deployed_crews", 0),
            total_cases_prevented=float(regional.get("total_cases_prevented", 0.0)),
            total_beds_saved=int(regional.get("total_beds_saved", 0)),
            total_saline_bags_saved=int(regional.get("total_saline_bags_saved", 0)),
            overall_roi=float(regional.get("overall_roi", 0.0) or 0.0),
            simulation_data_json=json.dumps(simulation_result),
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)

        log_audit(
            action="APPROVE_VECTOR_CONTROL_PLAN",
            details=f"Approved vector control plan '{plan_name}' (ID: {plan.id}) with {plan.total_deployed_crews} crews deployed. Estimated cases prevented: {plan.total_cases_prevented}.",
            user=approved_by,
        )
        return plan.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_approved_vector_plans(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves list of saved vector control simulation plans."""
    session = SessionLocal()
    try:
        plans = session.query(VectorControlPlan).order_by(VectorControlPlan.created_at.desc()).limit(limit).all()
        return [
            {
                "id": p.id,
                "plan_name": p.plan_name,
                "status": p.status,
                "created_at": p.created_at.isoformat() + "Z" if p.created_at else None,
                "approved_at": p.approved_at.isoformat() + "Z" if p.approved_at else None,
                "approved_by": p.approved_by,
                "forecast_horizon_weeks": p.forecast_horizon_weeks,
                "total_available_crews": p.total_available_crews,
                "total_deployed_crews": p.total_deployed_crews,
                "total_cases_prevented": p.total_cases_prevented,
                "total_beds_saved": p.total_beds_saved,
                "total_saline_bags_saved": p.total_saline_bags_saved,
                "overall_roi": p.overall_roi,
            }
            for p in plans
        ]
    finally:
        session.close()


# Ensure tables are initialized on import
init_db()
