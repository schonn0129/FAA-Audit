"""
MAP (Mapping Audit Package) construction for in-scope DCT questions.

Generates deterministic MAP rows from DCT questions, ownership assignments,
and audit scope configuration.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

import database as db
from models import Question, OwnershipAssignment, Manual, QuestionApplicability
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


def build_map_rows(audit_id: str, include_debug: bool = False) -> Tuple[List[Dict[str, Any]], List[str], List[Dict[str, Any]], int]:
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
            session.query(Question, OwnershipAssignment, QuestionApplicability)
            .join(OwnershipAssignment, OwnershipAssignment.question_id == Question.id)
            .outerjoin(QuestionApplicability, QuestionApplicability.question_id == Question.id)
            .filter(Question.audit_id == audit_id)
            .filter(OwnershipAssignment.primary_function.in_(in_scope_functions))
            .order_by(Question.element_id, Question.question_number, Question.qid)
        )

        sections_by_type = manual_mapper.load_latest_manual_sections(session, audit_id=audit_id)
        rows: List[Dict[str, Any]] = []
        not_applicable_count = 0
        for question, assignment, applicability in query.all():
            applicability_status = "Applicable"
            applicability_reason = ""
            if applicability and applicability.is_applicable is False:
                applicability_status = "Not Applicable"
                applicability_reason = applicability.reason or ""
                not_applicable_count += 1
            manual_links = assignment.manual_section_links or []
            exclusions = assignment.manual_section_exclusions or []
            excluded_keys = {
                (
                    (e.get("manual_type") or e.get("manual") or "").upper(),
                    str(e.get("section") or e.get("section_number") or e.get("reference") or "")
                )
                for e in exclusions
            }
            if any((e.get("manual_type") or "").upper() == "ANY" for e in exclusions):
                excluded_keys.add(("ANY", "*"))

            if manual_links:
                manual_links = [
                    l for l in manual_links
                    if (
                        (l.get("manual_type") or l.get("manual") or "").upper(),
                        str(l.get("section") or l.get("section_number") or l.get("reference") or "")
                    ) not in excluded_keys
                ]

            if sections_by_type:
                suggested_links = manual_mapper.suggest_manual_links(question, sections_by_type)
                if suggested_links:
                    # Merge manual overrides with auto-suggestions, avoiding duplicates.
                    merged = list(manual_links)
                    existing_keys = {
                        (
                            (l.get("manual_type") or l.get("manual") or "").upper(),
                            str(l.get("section") or l.get("section_number") or l.get("reference") or "")
                        )
                        for l in merged
                    }
                    for link in suggested_links:
                        key = (
                            (link.get("manual_type") or link.get("manual") or "").upper(),
                            str(link.get("section") or link.get("section_number") or link.get("reference") or "")
                        )
                        if key in excluded_keys or ("ANY", "*") in excluded_keys:
                            continue
                        if key not in existing_keys:
                            merged.append(link)
                            existing_keys.add(key)
                    manual_links = merged
            row = {
                "QID": question.qid or "",
                "Question_Text": question.question_text_full or question.question_text_condensed or "",
                "AIP_Reference": _extract_manual_refs(manual_links, "AIP"),
                "GMM_Reference": _extract_manual_refs(manual_links, "GMM"),
                "Other_Manual_References": _extract_other_manual_refs(manual_links, ["AIP", "GMM"]),
                "Evidence_Required": question.data_collection_guidance or "",
                "Applicability_Status": applicability_status,
                "Applicability_Reason": applicability_reason,
                "Audit_Finding": "",
                "Compliance_Status": ""
            }
            if include_debug:
                debug_links = []
                for link in manual_links:
                    if (link.get("source") or "").lower() != "auto":
                        continue
                    debug_links.append({
                        "manual_type": link.get("manual_type") or link.get("manual"),
                        "section": link.get("section") or link.get("section_number") or link.get("reference"),
                        "section_title": link.get("section_title"),
                        "page_number": link.get("page_number"),
                        "paragraph": link.get("paragraph"),
                        "score": link.get("score"),
                        "match_signals": link.get("match_signals")
                    })
                row["auto_suggestions_debug"] = debug_links
            rows.append(row)
        manuals_used = _get_latest_manuals(session)

    return rows, in_scope_functions, manuals_used, not_applicable_count


def generate_map_payload(audit_id: str, include_debug: bool = False) -> Dict[str, Any]:
    """Generate MAP response payload for the API."""
    rows, in_scope_functions, manuals_used, not_applicable_count = build_map_rows(
        audit_id,
        include_debug=include_debug
    )
    return {
        "audit_id": audit_id,
        "generated_date": datetime.utcnow().isoformat(),
        "in_scope_functions": in_scope_functions,
        "in_scope_total": len(rows),
        "not_applicable_count": not_applicable_count,
        "total_rows": len(rows),
        "manuals_used": manuals_used,
        "map_rows": rows
    }
