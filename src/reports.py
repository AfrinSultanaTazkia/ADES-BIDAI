"""
ADES BIDAI - Comprehensive Report & Notification Generation Engine
PDF Generation (ReportLab), HTML Generation (Jinja2), and Deterministic SMS/WhatsApp Templates
"""

import io
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from jinja2 import Template


def generate_pdf_report(plan_data: Dict[str, Any]) -> bytes:
    """
    Generates an official government PDF report of the dengue resource allocation plan using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "GovTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        alignment=1,  # Center
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "GovSubTitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        alignment=1,  # Center
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    section_title = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0284C7"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
    )
    body_bold = ParagraphStyle(
        "BodyDarkBold",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0F172A"),
    )
    alert_style = ParagraphStyle(
        "AlertText",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#DC2626"),
        fontName="Helvetica-Bold",
    )

    overview = plan_data.get("regional_overview", {})
    scarcity = plan_data.get("scarcity_controls", {})
    wards = plan_data.get("wards", [])
    routes = plan_data.get("hospital_overflow_routes", [])

    # 1. Header Banner
    story.append(Paragraph("GOVERNMENT OF THE PEOPLE'S REPUBLIC OF BANGLADESH", title_style))
    story.append(Paragraph(
        "DIRECTORATE GENERAL OF HEALTH SERVICES (DGHS) — CENTRAL DENGUE CONTROL COMMAND<br/>"
        "<b>ADES BIDAI AI-DRIVEN SURVEILLANCE & CONSTRAINED RESOURCE ALLOCATION PLAN</b><br/>"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Decision Authority: Central Health Administrator",
        subtitle_style
    ))
    story.append(Spacer(1, 8))

    # 2. Executive Regional Overview Table
    story.append(Paragraph("1. Regional Surveillance & Resource Allocation Overview", section_title))
    overview_data = [
        [
            Paragraph("Total Monitored Wards", body_bold), Paragraph(str(overview.get("total_wards", 60)), body_style),
            Paragraph("Selected Regional Stock", body_bold), Paragraph(f"{scarcity.get('selected_stock_percentage', 100)}%", body_style),
        ],
        [
            Paragraph("2-Week Predicted Cases", body_bold), Paragraph(f"{overview.get('total_predicted_cases', 0):.1f}", body_style),
            Paragraph("Spraying Crews Assigned", body_bold), Paragraph(f"{scarcity.get('assigned_spraying_crews', 0)} / {scarcity.get('total_spraying_crews', 0)}", body_style),
        ],
        [
            Paragraph("High / Med / Low Wards", body_bold), Paragraph(f"{overview.get('high_risk_wards_count', 0)} / {overview.get('medium_risk_wards_count', 0)} / {overview.get('low_risk_wards_count', 0)}", body_style),
            Paragraph("Critical Deficit Wards", body_bold), Paragraph(str(overview.get("critical_supply_wards_count", 0)), alert_style if overview.get("critical_supply_wards_count", 0) > 0 else body_style),
        ],
        [
            Paragraph("Saline Bags (Demand / Alloc / Deficit)", body_bold), Paragraph(f"{overview.get('total_saline_demand', 0)} / {overview.get('total_saline_allocated', 0)} / {overview.get('total_saline_deficit', 0)}", body_style),
            Paragraph("Kits (Demand / Alloc / Deficit)", body_bold), Paragraph(f"{overview.get('total_kits_demand', 0)} / {overview.get('total_kits_allocated', 0)} / {overview.get('total_kits_deficit', 0)}", body_style),
        ],
        [
            Paragraph("Hospital Beds (Demand / Alloc / Deficit)", body_bold), Paragraph(f"{overview.get('total_beds_demand', 0)} / {overview.get('total_beds_allocated', 0)} / {overview.get('total_beds_deficit', 0)}", body_style),
            Paragraph("Vector Crew Shortage", body_bold), Paragraph(str(overview.get("total_crew_shortage", 0)), body_style),
        ],
    ]
    t_overview = Table(overview_data, colWidths=[140, 130, 140, 130])
    t_overview.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 12))

    # 3. Top Priority & Critical Deficit Wards Table
    story.append(Paragraph("2. Top Vulnerable Wards & Resource Allocation Breakdown", section_title))
    ward_headers = [
        Paragraph("Rank", body_bold),
        Paragraph("Ward & Locality", body_bold),
        Paragraph("Priority", body_bold),
        Paragraph("Cases (2W)", body_bold),
        Paragraph("Saline Dem/Alloc", body_bold),
        Paragraph("Kits Dem/Alloc", body_bold),
        Paragraph("Beds Dem/Alloc", body_bold),
        Paragraph("Crews Req/Assigned", body_bold),
        Paragraph("Deficit Alert", body_bold),
    ]
    ward_rows = [ward_headers]

    for w in wards[:20]:  # Top 20 prioritized wards in PDF
        alert_text = "SHORTAGE" if w.get("has_critical_deficit") else "FULFILLED"
        p_alert = Paragraph(alert_text, alert_style if w.get("has_critical_deficit") else body_style)

        ward_rows.append([
            Paragraph(f"#{w.get('priority_ranking', '-')}", body_style),
            Paragraph(f"{w.get('ward_id')}<br/>{w.get('locality', '')}", body_style),
            Paragraph(f"{w.get('priority_score', 0):.3f}", body_style),
            Paragraph(f"{w.get('total_predicted_cases', 0):.1f}", body_style),
            Paragraph(f"{w.get('saline_demand', 0)} / {w.get('approved_saline_allocation', 0)}", body_style),
            Paragraph(f"{w.get('kits_demand', 0)} / {w.get('approved_kits_allocation', 0)}", body_style),
            Paragraph(f"{w.get('beds_demand', 0)} / {w.get('approved_beds_allocation', 0)}", body_style),
            Paragraph(f"{w.get('required_crews', 0)} / {w.get('approved_crew_allocation', 0)}", body_style),
            p_alert,
        ])

    t_wards = Table(ward_rows, colWidths=[30, 95, 45, 55, 75, 70, 70, 65, 55])
    t_wards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ]))
    story.append(t_wards)
    story.append(Spacer(1, 12))

    # 4. Hospital Overflow Routing Summary
    if routes:
        story.append(Paragraph("3. Hospital Overflow & Inpatient Referral Directives", section_title))
        route_headers = [
            Paragraph("Deficit Ward", body_bold),
            Paragraph("Designated Referral Hospital", body_bold),
            Paragraph("Distance", body_bold),
            Paragraph("Referred Beds", body_bold),
            Paragraph("Operational Directive", body_bold),
        ]
        route_rows = [route_headers]
        for r in routes[:10]:
            route_rows.append([
                Paragraph(f"{r.get('from_ward_id')}<br/>({r.get('from_locality')})", body_style),
                Paragraph(f"{r.get('to_ward_id')}<br/>({r.get('to_locality')})", body_style),
                Paragraph(f"{r.get('distance_km', 0):.1f} km", body_style),
                Paragraph(f"{r.get('patients_referred', 0)} beds", body_bold),
                Paragraph(r.get("rationale", ""), body_style),
            ])

        t_routes = Table(route_rows, colWidths=[90, 100, 55, 65, 230])
        t_routes.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0F2FE")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BAE6FD")),
        ]))
        story.append(t_routes)

    # 5. Sign-off block
    story.append(Spacer(1, 20))
    sign_data = [
        [
            Paragraph("<b>Prepared by:</b><br/>ADES BIDAI Predictive Optimization Engine", body_style),
            Paragraph("<b>Verified by:</b><br/>Director, Disease Surveillance & Vector Control", body_style),
            Paragraph("<b>Approved by:</b><br/>Central Health Administrator, DGHS", body_style),
        ]
    ]
    t_sign = Table(sign_data, colWidths=[180, 180, 180])
    t_sign.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#94A3B8")),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(KeepTogether(t_sign))

    doc.build(story)
    return buffer.getvalue()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ADES BIDAI - Official Dengue Resource Allocation Plan</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0B1120; color: #F8FAFC; margin: 0; padding: 24px; }
        .container { max-width: 1200px; margin: 0 auto; background: #111827; border: 1px solid #1F2937; border-radius: 12px; padding: 28px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .header { text-align: center; border-bottom: 2px solid #0284C7; padding-bottom: 16px; margin-bottom: 24px; }
        .header h1 { font-size: 22px; color: #38BDF8; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px; }
        .header p { font-size: 13px; color: #94A3B8; margin: 0; }
        .grid-kpi { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
        .kpi-card { background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 14px; }
        .kpi-label { font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 600; margin-bottom: 4px; }
        .kpi-val { font-size: 20px; font-weight: 700; color: #F8FAFC; }
        .kpi-val.alert { color: #EF4444; }
        .section-title { font-size: 16px; font-weight: 700; color: #38BDF8; margin: 24px 0 12px 0; display: flex; align-items: center; gap: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 20px; }
        th { background: #1E293B; color: #38BDF8; text-align: left; padding: 8px 10px; border: 1px solid #334155; }
        td { padding: 8px 10px; border: 1px solid #1F2937; color: #E2E8F0; }
        tr:nth-child(even) { background: #0F172A; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; }
        .badge-high { background: #7F1D1D; color: #FCA5A5; }
        .badge-med { background: #78350F; color: #FCD34D; }
        .badge-low { background: #064E3B; color: #6EE7B7; }
        .badge-deficit { background: #DC2626; color: white; }
        .badge-ok { background: #059669; color: white; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Directorate General of Health Services (DGHS)</h1>
        <p><b>ADES BIDAI AI-Driven Dengue Resource Allocation & Vector Control Plan</b></p>
        <p>Generated: {{ timestamp }} | Scarcity Level: {{ scarcity.selected_stock_percentage }}% Stock | Crews: {{ scarcity.total_spraying_crews }}</p>
    </div>

    <div class="grid-kpi">
        <div class="kpi-card">
            <div class="kpi-label">Total Predicted Cases</div>
            <div class="kpi-val">{{ overview.total_predicted_cases }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">High-Risk Wards</div>
            <div class="kpi-val {{ 'alert' if overview.high_risk_wards_count > 0 else '' }}">{{ overview.high_risk_wards_count }} / {{ overview.total_wards }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Saline Demand vs Allocated</div>
            <div class="kpi-val">{{ overview.total_saline_allocated }} / {{ overview.total_saline_demand }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Critical Deficit Wards</div>
            <div class="kpi-val {{ 'alert' if overview.critical_supply_wards_count > 0 else '' }}">{{ overview.critical_supply_wards_count }}</div>
        </div>
    </div>

    <div class="section-title">Priority-Based Ward Allocations (All 60 Wards)</div>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Ward ID</th>
                <th>Locality</th>
                <th>City</th>
                <th>Priority Score</th>
                <th>Risk Level</th>
                <th>Cases (2W)</th>
                <th>Saline (Dem/Alloc)</th>
                <th>Kits (Dem/Alloc)</th>
                <th>Beds (Dem/Alloc)</th>
                <th>Crews (Req/Assigned)</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for w in wards %}
            <tr>
                <td><b>#{{ w.priority_ranking }}</b></td>
                <td><b>{{ w.ward_id }}</b></td>
                <td>{{ w.locality }}</td>
                <td>{{ w.city }}</td>
                <td>{{ "%.4f"|format(w.priority_score) }}</td>
                <td><span class="badge badge-{{ w.risk_level|lower }}">{{ w.risk_level }}</span></td>
                <td>{{ w.total_predicted_cases }}</td>
                <td>{{ w.saline_demand }} / <b>{{ w.approved_saline_allocation }}</b></td>
                <td>{{ w.kits_demand }} / <b>{{ w.approved_kits_allocation }}</b></td>
                <td>{{ w.beds_demand }} / <b>{{ w.approved_beds_allocation }}</b></td>
                <td>{{ w.required_crews }} / <b>{{ w.approved_crew_allocation }}</b></td>
                <td>
                    {% if w.has_critical_deficit %}
                    <span class="badge badge-deficit">SHORTAGE</span>
                    {% else %}
                    <span class="badge badge-ok">FULFILLED</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    {% if routes %}
    <div class="section-title">Hospital Bed Capacity Overflow Routing</div>
    <table>
        <thead>
            <tr>
                <th>Deficit Ward</th>
                <th>Designated Surplus Hospital</th>
                <th>Distance</th>
                <th>Patients Referred</th>
                <th>Directive</th>
            </tr>
        </thead>
        <tbody>
            {% for r in routes %}
            <tr>
                <td><b>{{ r.from_ward_id }}</b> ({{ r.from_locality }})</td>
                <td><b>{{ r.to_ward_id }}</b> ({{ r.to_locality }})</td>
                <td>{{ "%.1f"|format(r.distance_km) }} km</td>
                <td><b>{{ r.patients_referred }} beds</b></td>
                <td>{{ r.rationale }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}
</div>
</body>
</html>
"""


def generate_html_report(plan_data: Dict[str, Any]) -> str:
    """Generates a complete standalone HTML report of the resource allocation plan."""
    template = Template(HTML_TEMPLATE)
    return template.render(
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        overview=plan_data.get("regional_overview", {}),
        scarcity=plan_data.get("scarcity_controls", {}),
        wards=plan_data.get("wards", []),
        routes=plan_data.get("hospital_overflow_routes", []),
    )


def generate_notification_templates(plan_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Deterministic template engine generating SMS and WhatsApp dispatch notifications
    for municipal field health workers, hospital directors, and vector control leads.
    """
    overview = plan_data.get("regional_overview", {})
    scarcity = plan_data.get("scarcity_controls", {})
    wards = plan_data.get("wards", [])
    routes = plan_data.get("hospital_overflow_routes", [])

    notifications = []

    # 1. High-Level Command Center SMS broadcast
    notifications.append({
        "channel": "SMS",
        "recipient_role": "Central Health & Municipal Commissioners",
        "title": "Regional Outbreak Early Warning & Resource Dispatch",
        "message": (
            f"[DGHS DENGUE ALERT] Regional stock set to {scarcity.get('selected_stock_percentage')}%. "
            f"2-Week Forecast: {overview.get('total_predicted_cases', 0):.0f} cases across {overview.get('total_wards', 60)} wards. "
            f"High-Risk Wards: {overview.get('high_risk_wards_count', 0)}. "
            f"Allocations: Saline {overview.get('total_saline_allocated')}/{overview.get('total_saline_demand')} bags, "
            f"Kits {overview.get('total_kits_allocated')}/{overview.get('total_kits_demand')}. "
            f"Spraying Crews Deployed: {overview.get('total_assigned_crews')}/{overview.get('total_required_crews')}. "
            f"Action: Implement approved plan immediately."
        ),
    })

    # 2. Critical Ward Alerts for Sanitary Inspectors
    top_critical_wards = [w for w in wards if w.get("has_critical_deficit")][:3]
    for cw in top_critical_wards:
        notifications.append({
            "channel": "WhatsApp",
            "recipient_role": f"Ward Sanitary Inspector ({cw['ward_id']})",
            "title": f"Critical Medical Resource Deficit Notice - {cw['locality']}",
            "message": (
                f"🚨 *CRITICAL DEFICIT ALERT - {cw['ward_id']} ({cw['locality']})*\n"
                f"Priority Ranking: #{cw.get('priority_ranking')} (Score: {cw.get('priority_score')})\n"
                f"Predicted Cases: {cw.get('total_predicted_cases')} in 2 weeks (Risk: {cw.get('risk_level')})\n"
                f"Allocated Saline: {cw.get('approved_saline_allocation')} (Deficit: {cw.get('remaining_saline_deficit')})\n"
                f"Allocated Kits: {cw.get('approved_kits_allocation')} (Deficit: {cw.get('remaining_kits_deficit')})\n"
                f"Spraying Crews: {cw.get('approved_crew_allocation')} assigned\n"
                f"Directives: Prioritize emergency fever triage; request inter-ward redistribution from central command."
            ),
        })

    # 3. Hospital Inpatient Overflow Referral Alerts
    for r in routes[:2]:
        notifications.append({
            "channel": "WhatsApp",
            "recipient_role": f"Medical Superintendent ({r['to_ward_id']} Hospital)",
            "title": f"Inpatient Surge Routing Directive ({r['to_locality']})",
            "message": (
                f"🏥 *PATIENT SURGE ROUTING DIRECTIVE*\n"
                f"Origin: {r['from_ward_id']} ({r['from_locality']})\n"
                f"Receiving Facility: {r['to_ward_id']} ({r['to_locality']}) — Distance: {r['distance_km']} km\n"
                f"Patients Routed: {r['patients_referred']} beds\n"
                f"Reason: {r['rationale']}\n"
                f"Action: Mobilize reserve bed capacity and notify triage teams."
            ),
        })

    return notifications
