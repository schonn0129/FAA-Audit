"""
PDF Generator for FAA DCT Compliance Package.

Generates a deterministic, professional PDF compliance package for PMI review.
Uses ReportLab for PDF generation.

PDF Structure (6 Sections):
1. Executive Summary - Scope, methodology, coverage statistics
2. QID Functional Ownership Table - ALL QIDs with assignments
3. In-Scope MAP - Audit-ready worksheets for selected functions
4. Deferred Items Log - Out-of-scope QIDs with documented owners
5. Methodology Appendix - Decision rules, source hierarchy
6. Sign-off Page - PMI review and approval

Design Principles:
- Deterministic: Same input always produces same PDF structure
- Traceable: Every assignment has documented rationale
- Defensible: Complete accountability for all QIDs
"""

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import database as db
import map_builder
from scoping import (
    VALID_FUNCTIONS,
    calculate_accountability_check,
    calculate_coverage_metrics,
    generate_deferred_report,
)

# =============================================================================
# STYLING CONSTANTS
# =============================================================================

FAA_BLUE = colors.HexColor("#1f4788")
FAA_LIGHT_BLUE = colors.HexColor("#e8f0f8")
CONFIDENCE_HIGH = colors.HexColor("#28a745")
CONFIDENCE_MEDIUM = colors.HexColor("#ffc107")
CONFIDENCE_LOW = colors.HexColor("#dc3545")
ROW_ALT = colors.HexColor("#f8f9fa")


def _get_styles() -> Dict[str, ParagraphStyle]:
    """Create consistent paragraph styles for the PDF."""
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Heading1"],
            fontSize=24,
            textColor=FAA_BLUE,
            spaceAfter=20,
            alignment=TA_CENTER,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            parent=base["Heading2"],
            fontSize=16,
            textColor=FAA_BLUE,
            spaceBefore=20,
            spaceAfter=12,
            borderPadding=5,
        ),
        "subsection": ParagraphStyle(
            "Subsection",
            parent=base["Heading3"],
            fontSize=12,
            textColor=FAA_BLUE,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            spaceAfter=8,
            leading=14,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontSize=8,
            spaceAfter=4,
            leading=10,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER,
        ),
    }


# =============================================================================
# DATA COLLECTION
# =============================================================================

def _collect_pdf_data(audit_id: str) -> Dict[str, Any]:
    """
    Collect all data needed for PDF generation in a single pass.

    Args:
        audit_id: The audit identifier

    Returns:
        Dictionary containing all PDF data sources
    """
    # Get audit metadata
    audit = db.get_audit(audit_id)
    if not audit:
        raise ValueError(f"Audit not found: {audit_id}")

    # Get ownership assignments
    assignments = db.get_ownership_assignments(audit_id)
    if not assignments:
        raise ValueError(f"No ownership assignments found for audit: {audit_id}")

    # Sort assignments by QID for determinism
    assignments = sorted(assignments, key=lambda x: x.get("qid", ""))

    # Get scope configuration
    scope = db.get_audit_scope(audit_id)
    if scope and scope.get("in_scope_functions"):
        in_scope_functions = scope["in_scope_functions"]
        scope_name = scope.get("scope_name", "Custom Scope")
        scope_rationale = scope.get("scope_rationale", "")
    else:
        in_scope_functions = VALID_FUNCTIONS
        scope_name = "Full Scope"
        scope_rationale = "All functions included - no scope restriction applied"

    # Sort in_scope_functions for determinism
    in_scope_functions = sorted(in_scope_functions)

    # Calculate coverage metrics
    coverage = calculate_coverage_metrics(assignments, in_scope_functions)

    # Calculate accountability check
    accountability = calculate_accountability_check(assignments)

    # Generate deferred report
    deferred = generate_deferred_report(assignments, in_scope_functions, scope_rationale)

    # Get MAP data
    map_payload = map_builder.generate_map_payload(audit_id)

    # Get applicability data
    applicability = db.get_applicability_for_audit(audit_id)
    applicability_map = {a["qid"]: a for a in applicability}

    # Get manuals for version info
    manuals = db.get_manuals()

    # Generation timestamp (fixed format for determinism)
    generation_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return {
        "audit": audit,
        "assignments": assignments,
        "in_scope_functions": in_scope_functions,
        "scope_name": scope_name,
        "scope_rationale": scope_rationale,
        "coverage": coverage.to_dict(),
        "accountability": accountability,
        "deferred": deferred,
        "map_payload": map_payload,
        "applicability_map": applicability_map,
        "manuals": manuals,
        "generation_time": generation_time,
    }


# =============================================================================
# SECTION BUILDERS
# =============================================================================

def _build_executive_summary(data: Dict[str, Any], styles: Dict) -> List:
    """Build Section 1: Executive Summary."""
    elements = []
    audit = data["audit"]
    coverage = data["coverage"]
    accountability = data["accountability"]

    # Title
    elements.append(Paragraph("FAA DCT Compliance Package", styles["title"]))
    elements.append(Spacer(1, 10))

    # Audit Info
    elements.append(Paragraph("1. Executive Summary", styles["section_header"]))

    # Audit Metadata Table
    meta_data = [
        ["Audit File:", audit.get("filename", "N/A")],
        ["DCT Edition:", audit.get("dct_edition", "N/A")],
        ["DCT Version:", audit.get("dct_version", "N/A")],
        ["Element ID:", audit.get("element_id", "N/A")],
        ["Generated:", data["generation_time"]],
    ]

    meta_table = Table(meta_data, colWidths=[1.5*inch, 4*inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # Scope Definition
    elements.append(Paragraph("Scope Definition", styles["subsection"]))
    elements.append(Paragraph(f"<b>Scope Name:</b> {data['scope_name']}", styles["body"]))
    elements.append(Paragraph(f"<b>Rationale:</b> {data['scope_rationale'] or 'Not specified'}", styles["body"]))

    # In-scope functions
    func_list = ", ".join(data["in_scope_functions"])
    elements.append(Paragraph(f"<b>In-Scope Functions:</b> {func_list}", styles["body"]))
    elements.append(Spacer(1, 10))

    # Coverage Statistics
    elements.append(Paragraph("Coverage Statistics", styles["subsection"]))

    stats_data = [
        ["Metric", "Value"],
        ["Total QIDs", str(coverage["total_qids"])],
        ["In-Scope QIDs", str(coverage["in_scope_count"])],
        ["Deferred QIDs", str(coverage["deferred_count"])],
        ["Coverage Percentage", f"{coverage['overall_percentage']}%"],
    ]

    stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 15))

    # Accountability Check
    elements.append(Paragraph("Accountability Verification", styles["subsection"]))
    check_status = "PASS" if accountability["all_qids_assigned"] else "FAIL"
    check_color = "green" if accountability["all_qids_assigned"] else "red"
    elements.append(Paragraph(
        f"<b>Status:</b> <font color='{check_color}'>{check_status}</font> - {accountability['message']}",
        styles["body"]
    ))

    elements.append(PageBreak())
    return elements


def _build_ownership_table(data: Dict[str, Any], styles: Dict) -> List:
    """Build Section 2: QID Functional Ownership Table (ALL QIDs)."""
    elements = []
    assignments = data["assignments"]
    in_scope_functions = data["in_scope_functions"]

    elements.append(Paragraph("2. QID Functional Ownership Table", styles["section_header"]))
    elements.append(Paragraph(
        "This table documents ownership assignments for ALL QIDs in the DCT, "
        "regardless of audit scope. QIDs marked with scope status indicate whether "
        "they are being audited in this cycle.",
        styles["body"]
    ))
    elements.append(Spacer(1, 10))

    # Build table data
    table_data = [["QID", "Question (Condensed)", "Primary Owner", "Confidence", "Scope"]]

    for assignment in assignments:
        qid = assignment.get("qid", "")
        question = assignment.get("question_text_condensed", "")[:80]
        if len(assignment.get("question_text_condensed", "")) > 80:
            question += "..."
        primary = assignment.get("primary_function", "Unassigned")
        confidence = assignment.get("confidence_score", "Low")

        # Determine scope status
        is_in_scope = primary in in_scope_functions
        scope_status = "In-Scope" if is_in_scope else "Deferred"

        table_data.append([qid, question, primary, confidence, scope_status])

    # Create table with column widths
    col_widths = [0.8*inch, 3.2*inch, 1.5*inch, 0.8*inch, 0.8*inch]
    ownership_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Build style commands
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]

    # Add alternating row colors and confidence highlighting
    for i, row in enumerate(table_data[1:], start=1):
        # Alternating background
        if i % 2 == 0:
            style_commands.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))

        # Confidence color coding
        confidence = row[3]
        if confidence == "High":
            style_commands.append(("TEXTCOLOR", (3, i), (3, i), CONFIDENCE_HIGH))
        elif confidence == "Medium":
            style_commands.append(("TEXTCOLOR", (3, i), (3, i), CONFIDENCE_MEDIUM))
        else:
            style_commands.append(("TEXTCOLOR", (3, i), (3, i), CONFIDENCE_LOW))

        # Scope status highlighting
        scope = row[4]
        if scope == "Deferred":
            style_commands.append(("TEXTCOLOR", (4, i), (4, i), colors.gray))

    ownership_table.setStyle(TableStyle(style_commands))
    elements.append(ownership_table)

    # Legend
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "<b>Legend:</b> Confidence: "
        "<font color='green'>High</font> | "
        "<font color='#ffc107'>Medium</font> | "
        "<font color='red'>Low</font>",
        styles["small"]
    ))

    elements.append(PageBreak())
    return elements


def _build_inscope_map(data: Dict[str, Any], styles: Dict) -> List:
    """Build Section 3: In-Scope MAP (Audit Worksheets)."""
    elements = []
    map_payload = data["map_payload"]
    map_rows = map_payload.get("map_rows", [])

    elements.append(Paragraph("3. In-Scope MAP (Mapping Audit Package)", styles["section_header"]))
    elements.append(Paragraph(
        "This section contains audit worksheets for in-scope questions. "
        "The Finding and Compliance Status columns are left blank for auditor completion.",
        styles["body"]
    ))
    elements.append(Paragraph(
        f"<b>Total In-Scope Questions:</b> {len(map_rows)} | "
        f"<b>Not Applicable:</b> {map_payload.get('not_applicable_count', 0)}",
        styles["body"]
    ))
    elements.append(Spacer(1, 10))

    if not map_rows:
        elements.append(Paragraph(
            "<i>No in-scope questions found. Check scope configuration.</i>",
            styles["body"]
        ))
        elements.append(PageBreak())
        return elements

    # Build MAP table
    table_data = [["QID", "Question", "AIP Ref", "GMM Ref", "Evidence Required", "Applicability", "Finding", "Status"]]

    for row in map_rows:
        qid = row.get("QID", "")
        question = row.get("Question_Text", "")[:60]
        if len(row.get("Question_Text", "")) > 60:
            question += "..."
        aip = row.get("AIP_Reference", "")[:20] or "-"
        gmm = row.get("GMM_Reference", "")[:20] or "-"
        evidence = row.get("Evidence_Required", "")[:40]
        if len(row.get("Evidence_Required", "")) > 40:
            evidence += "..."
        applicability = row.get("Applicability_Status", "Applicable")

        table_data.append([qid, question, aip, gmm, evidence, applicability, "", ""])

    # Column widths for landscape-ish fit
    col_widths = [0.6*inch, 2*inch, 0.7*inch, 0.7*inch, 1.3*inch, 0.7*inch, 0.6*inch, 0.5*inch]
    map_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (5, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]

    # Highlight not applicable rows
    for i, row in enumerate(table_data[1:], start=1):
        if row[5] == "Not Applicable":
            style_commands.append(("TEXTCOLOR", (5, i), (5, i), colors.gray))

    map_table.setStyle(TableStyle(style_commands))
    elements.append(map_table)

    elements.append(PageBreak())
    return elements


def _build_deferred_log(data: Dict[str, Any], styles: Dict) -> List:
    """Build Section 4: Deferred Items Log."""
    elements = []
    deferred = data["deferred"]
    deferred_items = deferred.get("deferred_items", [])

    elements.append(Paragraph("4. Deferred Items Log", styles["section_header"]))
    elements.append(Paragraph(
        "These QIDs are documented for accountability but are NOT being audited "
        "in this cycle. Each deferred item has an assigned owner for future audit cycles.",
        styles["body"]
    ))
    elements.append(Spacer(1, 10))

    if not deferred_items:
        elements.append(Paragraph(
            "<i>No deferred items. All QIDs are in-scope for this audit.</i>",
            styles["body"]
        ))
        elements.append(PageBreak())
        return elements

    # Summary by function
    summary = deferred.get("summary_by_function", {})
    if summary:
        elements.append(Paragraph("Deferred Summary by Function", styles["subsection"]))
        summary_data = [["Function", "Count"]]
        for func, count in sorted(summary.items()):
            summary_data.append([func, str(count)])

        summary_table = Table(summary_data, colWidths=[2.5*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))

    # Detailed deferred items
    elements.append(Paragraph("Deferred Items Detail", styles["subsection"]))

    table_data = [["QID", "Question (Condensed)", "Assigned Owner", "Confidence"]]
    for item in deferred_items:
        qid = item.get("qid", "")
        question = item.get("question_text_condensed", "")[:70]
        if len(item.get("question_text_condensed", "")) > 70:
            question += "..."
        owner = item.get("primary_function", "Unassigned")
        confidence = item.get("confidence_score", "Low")
        table_data.append([qid, question, owner, confidence])

    col_widths = [0.8*inch, 3.5*inch, 1.5*inch, 0.8*inch]
    deferred_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    deferred_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]))
    elements.append(deferred_table)

    elements.append(PageBreak())
    return elements


def _build_methodology_appendix(data: Dict[str, Any], styles: Dict) -> List:
    """Build Section 5: Methodology Appendix."""
    elements = []
    audit = data["audit"]
    manuals = data["manuals"]

    elements.append(Paragraph("5. Methodology Appendix", styles["section_header"]))

    # Decision Rules Overview
    elements.append(Paragraph("Ownership Assignment Decision Rules", styles["subsection"]))
    elements.append(Paragraph(
        "Ownership assignments are made using a deterministic, rules-based decision tree. "
        "The system evaluates each question against multiple signal sources:",
        styles["body"]
    ))

    rules_data = [
        ["Priority", "Signal Source", "Description"],
        ["1", "CFR References", "Direct regulatory citations in question text (e.g., 14 CFR 121.369)"],
        ["2", "Keyword Analysis", "Domain-specific terminology patterns (e.g., 'task card', 'dispatch')"],
        ["3", "Manual Cross-Reference", "Links to company manual sections (AIP, GMM)"],
        ["4", "Operational Reality", "Default assignment based on typical organizational structure"],
    ]

    rules_table = Table(rules_data, colWidths=[0.7*inch, 1.5*inch, 4*inch])
    rules_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]))
    elements.append(rules_table)
    elements.append(Spacer(1, 15))

    # Confidence Scoring
    elements.append(Paragraph("Confidence Scoring", styles["subsection"]))
    elements.append(Paragraph(
        "Each assignment includes a confidence score based on signal strength:",
        styles["body"]
    ))

    confidence_data = [
        ["Score", "Criteria"],
        ["High", "Multiple strong signals agree; direct CFR mapping; manual override"],
        ["Medium", "Single strong signal or multiple weak signals; keyword match"],
        ["Low", "No clear signals; default assignment based on question category"],
    ]

    confidence_table = Table(confidence_data, colWidths=[1*inch, 5*inch])
    confidence_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]))
    elements.append(confidence_table)
    elements.append(Spacer(1, 15))

    # The 7 Functions
    elements.append(Paragraph("The 7 Authorized Functions", styles["subsection"]))
    func_list = "\n".join([f"    {i+1}. {f}" for i, f in enumerate(VALID_FUNCTIONS)])
    elements.append(Paragraph(func_list.replace("\n", "<br/>"), styles["body"]))
    elements.append(Spacer(1, 15))

    # Version Control
    elements.append(Paragraph("Version Control", styles["subsection"]))

    version_data = [
        ["Document", "Version/Info"],
        ["DCT File", audit.get("filename", "N/A")],
        ["DCT Edition", audit.get("dct_edition", "N/A")],
        ["DCT Version", audit.get("dct_version", "N/A")],
        ["Total QIDs", str(len(data["assignments"]))],
        ["Generated", data["generation_time"]],
    ]

    # Add manual versions
    for manual in manuals[:5]:  # Limit to 5 most recent
        version_data.append([
            f"{manual.get('manual_type', 'Manual')}",
            f"{manual.get('filename', 'N/A')} (v{manual.get('version', 'N/A')})"
        ])

    version_table = Table(version_data, colWidths=[1.5*inch, 4.5*inch])
    version_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FAA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]))
    elements.append(version_table)

    elements.append(PageBreak())
    return elements


def _build_signoff_page(data: Dict[str, Any], styles: Dict) -> List:
    """Build Section 6: PMI Sign-off Page."""
    elements = []

    elements.append(Paragraph("6. PMI Review and Approval", styles["section_header"]))
    elements.append(Spacer(1, 20))

    # Compliance Statement
    elements.append(Paragraph("Compliance Statement", styles["subsection"]))
    elements.append(Paragraph(
        "This compliance package has been prepared in accordance with FAA DCT requirements. "
        "All questions have been assigned to accountable functions, and the scope of this "
        "audit has been documented with appropriate rationale.",
        styles["body"]
    ))
    elements.append(Spacer(1, 15))

    # Verification Checklist
    elements.append(Paragraph("Verification Checklist", styles["subsection"]))

    checklist = [
        "All QIDs from the DCT have been assigned to one of the 7 authorized functions",
        "Scope selection has been documented with appropriate rationale",
        "Deferred items have been reviewed and their owners documented",
        "Manual references have been verified against current AIP/GMM versions",
        "Low-confidence assignments have been reviewed by management",
    ]

    for item in checklist:
        elements.append(Paragraph(f"\u2610  {item}", styles["body"]))

    elements.append(Spacer(1, 30))

    # Signature Lines
    elements.append(Paragraph("Approvals", styles["subsection"]))

    sig_data = [
        ["Role", "Name", "Signature", "Date"],
        ["Prepared By:", "_" * 25, "_" * 25, "_" * 15],
        ["Reviewed By:", "_" * 25, "_" * 25, "_" * 15],
        ["PMI Approval:", "_" * 25, "_" * 25, "_" * 15],
    ]

    sig_table = Table(sig_data, colWidths=[1.2*inch, 2*inch, 2*inch, 1.3*inch])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(sig_table)

    elements.append(Spacer(1, 40))

    # Footer
    elements.append(Paragraph(
        f"Generated: {data['generation_time']}<br/>"
        f"This document was generated by the FAA DCT Compliance Engine.",
        styles["footer"]
    ))

    return elements


# =============================================================================
# MAIN GENERATOR
# =============================================================================

def _add_page_number(canvas, doc):
    """Add page numbers to each page."""
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.gray)
    canvas.drawCentredString(letter[0] / 2, 0.5 * inch, text)
    canvas.restoreState()


def generate_compliance_pdf(audit_id: str) -> bytes:
    """
    Generate the complete compliance package PDF.

    Args:
        audit_id: The audit identifier

    Returns:
        PDF file contents as bytes
    """
    # Collect all data
    data = _collect_pdf_data(audit_id)

    # Get styles
    styles = _get_styles()

    # Build PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title=f"FAA DCT Compliance Package - {data['audit'].get('filename', 'Audit')}",
        author="FAA DCT Compliance Engine",
    )

    # Build all sections
    elements = []
    elements.extend(_build_executive_summary(data, styles))
    elements.extend(_build_ownership_table(data, styles))
    elements.extend(_build_inscope_map(data, styles))
    elements.extend(_build_deferred_log(data, styles))
    elements.extend(_build_methodology_appendix(data, styles))
    elements.extend(_build_signoff_page(data, styles))

    # Generate PDF
    doc.build(elements, onFirstPage=_add_page_number, onLaterPages=_add_page_number)

    # Return bytes
    buffer.seek(0)
    return buffer.read()
