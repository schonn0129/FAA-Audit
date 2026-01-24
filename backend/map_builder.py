"""
MAP (Mapping Audit Package) construction for in-scope DCT questions.

Generates deterministic MAP rows from DCT questions, ownership assignments,
and audit scope configuration.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

import database as db
from models import Question, OwnershipAssignment, Manual
import manual_mapper
from scoping import VALID_FUNCTIONS


def _extract_manual_refs(links: List[Dict[str, Any]], manual_type: str) -> str:
    """Extract manual section references for a given manual type."""
    if not links:
        return ""

    refs: List[str] = []
    manual_type_upper = manual_type.upper()

    for link in links:
        manual = (link.get("manual") or link.get("manual_type") or "").upper()
        if manual != manual_type_upper:
            continue

        section = (
            link.get("section")
            or link.get("section_number")
            or link.get("reference")
            or link.get("section_title")
        )
        if section:
            refs.append(str(section))

    return "; ".join(refs)


def _extract_other_manual_refs(links: List[Dict[str, Any]], excluded_types: List[str]) -> str:
    """Extract references for non-standard manual types."""
    if not links:
        return ""

    excluded_upper = {t.upper() for t in excluded_types}
    refs: List[str] = []

    for link in links:
        manual_type = (link.get("manual_type") or link.get("manual") or "OTHER").upper()
        if manual_type in excluded_upper:
            continue

        section = (
            link.get("section")
            or link.get("section_number")
            or link.get("reference")
            or link.get("section_title")
        )
        if section:
            refs.append(f"{manual_type} {section}".strip())

    return "; ".join(refs)


def _get_latest_manuals(session) -> List[Dict[str, Any]]:
    """Return latest manual per type for banner display."""
    manuals = session.query(Manual).order_by(Manual.upload_date.desc()).all()
    latest_by_type = {}
    for manual in manuals:
        if manual.manual_type not in latest_by_type:
            latest_by_type[manual.manual_type] = manual

    return [m.to_dict() for m in latest_by_type.values()]


def build_map_rows(audit_id: str) -> Tuple[List[Dict[str, Any]], List[str], List[Dict[str, Any]]]:
    """
    Build MAP rows for an audit, filtered to in-scope functions.

    Returns:
        Tuple of (rows, in_scope_functions)
    """
    scope = db.get_audit_scope(audit_id)
    if scope and scope.get("in_scope_functions"):
        in_scope_functions = scope.get("in_scope_functions", [])
    else:
        in_scope_functions = VALID_FUNCTIONS

    with db.get_session() as session:
        query = (
            session.query(Question, OwnershipAssignment)
            .join(OwnershipAssignment, OwnershipAssignment.question_id == Question.id)
            .filter(Question.audit_id == audit_id)
            .filter(OwnershipAssignment.primary_function.in_(in_scope_functions))
            .order_by(Question.element_id, Question.question_number, Question.qid)
        )

        sections_by_type = manual_mapper.load_latest_manual_sections(session)
        rows: List[Dict[str, Any]] = []
        for question, assignment in query.all():
            manual_links = assignment.manual_section_links or []
            if not manual_links and sections_by_type:
                manual_links = manual_mapper.suggest_manual_links(question, sections_by_type)
            rows.append({
                "QID": question.qid or "",
                "Question_Text": question.question_text_full or question.question_text_condensed or "",
                "AIP_Reference": _extract_manual_refs(manual_links, "AIP"),
                "GMM_Reference": _extract_manual_refs(manual_links, "GMM"),
                "Other_Manual_References": _extract_other_manual_refs(manual_links, ["AIP", "GMM"]),
                "Evidence_Required": question.data_collection_guidance or "",
                "Audit_Finding": "",
                "Compliance_Status": ""
            })
        manuals_used = _get_latest_manuals(session)

    return rows, in_scope_functions, manuals_used


def generate_map_payload(audit_id: str) -> Dict[str, Any]:
    """Generate MAP response payload for the API."""
    rows, in_scope_functions, manuals_used = build_map_rows(audit_id)
    return {
        "audit_id": audit_id,
        "generated_date": datetime.utcnow().isoformat(),
        "in_scope_functions": in_scope_functions,
        "total_rows": len(rows),
        "manuals_used": manuals_used,
        "map_rows": rows
    }
