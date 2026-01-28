"""
Database connection and session management for the FAA Audit application.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

from config import DATABASE_URL
from models import (
    Base,
    Audit,
    Question,
    Finding,
    ExtractedTable,
    OwnershipAssignment,
    OwnershipRule,
    AuditScope,
    Manual,
    ManualSection,
    QuestionApplicability
)

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)
    _ensure_audit_columns()
    _ensure_ownership_columns()
    print(f"Database initialized at {DATABASE_URL}")


def _ensure_audit_columns():
    """Add new columns to the audits table if the database already exists."""
    inspector = inspect(engine)
    if "audits" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("audits")}
    alters = []
    if "dct_edition" not in columns:
        alters.append("ALTER TABLE audits ADD COLUMN dct_edition VARCHAR(50)")
    if "dct_version" not in columns:
        alters.append("ALTER TABLE audits ADD COLUMN dct_version VARCHAR(50)")
    if "pinned_manual_ids" not in columns:
        alters.append("ALTER TABLE audits ADD COLUMN pinned_manual_ids TEXT")

    if not alters:
        return

    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))


def _ensure_ownership_columns():
    """Add new columns to the ownership_assignments table if needed."""
    inspector = inspect(engine)
    if "ownership_assignments" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("ownership_assignments")}
    alters = []
    if "manual_section_exclusions" not in columns:
        alters.append("ALTER TABLE ownership_assignments ADD COLUMN manual_section_exclusions TEXT")

    if not alters:
        return

    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))


def drop_db():
    """Drop all tables (use with caution!)."""
    Base.metadata.drop_all(engine)
    print("All tables dropped")


@contextmanager
def get_session():
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            session.query(Audit).all()
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_audit(audit_id: str, filename: str, parsed_data: dict) -> Audit:
    """
    Save a parsed audit to the database.

    Args:
        audit_id: Unique identifier for the audit
        filename: Original filename of the PDF
        parsed_data: Dictionary containing parsed PDF data

    Returns:
        The created Audit object
    """
    with get_session() as session:
        # Extract metadata
        metadata = parsed_data.get("metadata", {})
        compliance = parsed_data.get("compliance", {})

        # Create audit record
        audit = Audit(
            id=audit_id,
            filename=filename,
            status="processed",
            page_count=metadata.get("page_count", 0),
            inspection_date=metadata.get("inspection_date"),
            inspector_name=metadata.get("inspector_name"),
            facility_name=metadata.get("facility_name"),
            facility_number=metadata.get("facility_number"),
            document_type=metadata.get("document_type"),
            dct_edition=metadata.get("dct_edition"),
            dct_version=metadata.get("dct_version"),
            raw_text_length=parsed_data.get("raw_text_length", 0),
            compliance_status=compliance.get("compliance_status"),
            total_findings=compliance.get("total_findings", 0),
            critical_findings=compliance.get("critical_findings", 0),
            major_findings=compliance.get("major_findings", 0),
            minor_findings=compliance.get("minor_findings", 0),
            compliance_percentage=compliance.get("compliance_percentage")
        )

        # Extract element_id from first question if available
        questions_data = parsed_data.get("questions", [])
        if questions_data and questions_data[0].get("Element_ID"):
            audit.element_id = questions_data[0]["Element_ID"]

        session.add(audit)

        # Add questions
        for q_data in questions_data:
            question = Question(
                audit_id=audit_id,
                element_id=q_data.get("Element_ID"),
                qid=q_data.get("QID"),
                question_number=q_data.get("Question_Number"),
                question_text_full=q_data.get("Question_Text_Full"),
                question_text_condensed=q_data.get("Question_Text_Condensed"),
                data_collection_guidance=q_data.get("Data_Collection_Guidance"),
                reference_raw=q_data.get("Reference_Raw"),
                reference_cfr_list=q_data.get("Reference_CFR_List", []),
                reference_faa_guidance_list=q_data.get("Reference_FAA_Guidance_List", []),
                reference_other_list=q_data.get("Reference_Other_List", []),
                pdf_page_number=q_data.get("PDF_Page_Number"),
                pdf_element_block_id=q_data.get("PDF_Element_Block_ID"),
                notes=q_data.get("Notes", [])
            )
            session.add(question)

        # Add findings
        for f_data in parsed_data.get("findings", []):
            finding = Finding(
                audit_id=audit_id,
                number=f_data.get("number"),
                description=f_data.get("description"),
                finding_type=f_data.get("type"),
                severity=f_data.get("severity")
            )
            session.add(finding)

        # Add tables
        for t_data in parsed_data.get("tables", []):
            table = ExtractedTable(
                audit_id=audit_id,
                page=t_data.get("page"),
                headers=t_data.get("headers", []),
                rows=t_data.get("rows", []),
                row_count=t_data.get("row_count", 0)
            )
            session.add(table)

        session.commit()

        # Refresh to get relationships
        session.refresh(audit)
        return audit


def get_audit(audit_id: str) -> dict:
    """
    Get an audit by ID.

    Args:
        audit_id: The audit ID

    Returns:
        Dictionary representation of the audit, or None if not found
    """
    with get_session() as session:
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if audit:
            return audit.to_dict()
        return None


def get_all_audits(page: int = 1, per_page: int = 10) -> dict:
    """
    Get all audits with pagination.

    Args:
        page: Page number (1-indexed)
        per_page: Number of items per page

    Returns:
        Dictionary with audits and pagination info
    """
    with get_session() as session:
        total = session.query(Audit).count()
        offset = (page - 1) * per_page

        audits = session.query(Audit)\
            .order_by(Audit.upload_date.desc())\
            .offset(offset)\
            .limit(per_page)\
            .all()

        return {
            "audits": [a.to_dict() for a in audits],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }


def delete_audit(audit_id: str) -> bool:
    """
    Delete an audit by ID.

    Args:
        audit_id: The audit ID

    Returns:
        True if deleted, False if not found
    """
    with get_session() as session:
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if audit:
            session.delete(audit)
            session.commit()
            return True
        return False


def search_audits(filename: str = None, start_date: str = None, end_date: str = None) -> list:
    """
    Search audits by filename and date range.

    Args:
        filename: Partial filename to search for
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        List of matching audits
    """
    from datetime import datetime

    with get_session() as session:
        query = session.query(Audit)

        if filename:
            query = query.filter(Audit.filename.ilike(f"%{filename}%"))

        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Audit.upload_date >= start)
            except ValueError:
                pass

        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Audit.upload_date <= end)
            except ValueError:
                pass

        audits = query.order_by(Audit.upload_date.desc()).all()
        return [a.to_dict() for a in audits]


# =============================================================================
# MANUAL FUNCTIONS
# =============================================================================

def save_manual_with_sections(manual_id: str, filename: str, manual_type: str,
                              page_count: int, sections: list, version: str = None) -> dict:
    """
    Save an uploaded manual and its extracted sections.

    Args:
        manual_id: UUID for the manual
        filename: Original filename
        manual_type: Manual type (AIP, GMM, or custom)
        page_count: Number of pages
        sections: List of section dictionaries
        version: Optional manual version

    Returns:
        Manual dictionary
    """
    with get_session() as session:
        manual = Manual(
            id=manual_id,
            filename=filename,
            manual_type=manual_type,
            page_count=page_count,
            version=version,
            status="processed"
        )
        session.add(manual)

        for section in sections:
            manual_section = ManualSection(
                manual_id=manual_id,
                section_number=section.get("section_number"),
                section_title=section.get("section_title"),
                section_text=section.get("section_text"),
                page_number=section.get("page_number"),
                cfr_citations=section.get("cfr_citations", []),
                suggested_owner=section.get("suggested_owner")
            )
            session.add(manual_section)

        session.commit()
        session.refresh(manual)
        return manual.to_dict()


def replace_manual_sections(manual_id: str, page_count: int, sections: list,
                            version: str = None, status: str = "processed") -> dict:
    """
    Replace all sections for an existing manual.

    Args:
        manual_id: UUID for the manual
        page_count: Number of pages
        sections: List of section dictionaries
        version: Optional manual version
        status: Manual processing status

    Returns:
        Manual dictionary
    """
    with get_session() as session:
        manual = session.query(Manual).filter(Manual.id == manual_id).first()
        if not manual:
            return None

        session.query(ManualSection).filter(
            ManualSection.manual_id == manual_id
        ).delete(synchronize_session=False)

        for section in sections:
            manual_section = ManualSection(
                manual_id=manual_id,
                section_number=section.get("section_number"),
                section_title=section.get("section_title"),
                section_text=section.get("section_text"),
                page_number=section.get("page_number"),
                cfr_citations=section.get("cfr_citations", []),
                suggested_owner=section.get("suggested_owner")
            )
            session.add(manual_section)

        manual.page_count = page_count
        manual.version = version
        manual.status = status

        session.add(manual)
        session.commit()
        session.refresh(manual)
        return manual.to_dict()


def get_manuals(manual_type: str = None) -> list:
    """
    Get list of uploaded manuals.
    """
    with get_session() as session:
        query = session.query(Manual)
        if manual_type:
            query = query.filter(Manual.manual_type == manual_type)
        manuals = query.order_by(Manual.upload_date.desc()).all()
        return [m.to_dict() for m in manuals]


def get_manual(manual_id: str) -> dict:
    """
    Get a manual by ID.
    """
    with get_session() as session:
        manual = session.query(Manual).filter(Manual.id == manual_id).first()
        return manual.to_dict() if manual else None


def get_latest_manual_by_type(manual_type: str) -> dict:
    """
    Get the most recent manual for a given type.
    """
    with get_session() as session:
        manual = (
            session.query(Manual)
            .filter(Manual.manual_type == manual_type)
            .order_by(Manual.upload_date.desc())
            .first()
        )
        return manual.to_dict() if manual else None


def get_audit_pinned_manual_ids(audit_id: str) -> dict:
    """Return pinned manual IDs for an audit (by manual type)."""
    with get_session() as session:
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return {}
        return audit.pinned_manual_ids or {}


def set_audit_pinned_manual_ids(audit_id: str, pinned_manual_ids: dict) -> dict:
    """Persist pinned manual IDs for an audit."""
    with get_session() as session:
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return {}
        audit.pinned_manual_ids = pinned_manual_ids or {}
        session.add(audit)
        session.commit()
        session.refresh(audit)
        return audit.pinned_manual_ids or {}


def get_manual_sections(manual_id: str) -> list:
    """
    Get all sections for a manual.
    """
    with get_session() as session:
        sections = (
            session.query(ManualSection)
            .filter(ManualSection.manual_id == manual_id)
            .order_by(ManualSection.page_number.asc())
            .all()
        )
        return [s.to_dict() for s in sections]


def add_manual_section_link(audit_id: str, qid: str, manual_type: str, section: str,
                            reference: str = None, notes: str = None, added_by: str = None) -> dict:
    """
    Add a manual section link to a question's ownership assignment.
    """
    if not qid:
        raise ValueError("QID is required")
    if not manual_type or not section:
        raise ValueError("manual_type and section are required")

    manual_type = manual_type.strip().upper()
    section = section.strip()
    reference = reference.strip() if reference else None
    notes = notes.strip() if notes else None

    with get_session() as session:
        question = session.query(Question).filter(
            Question.audit_id == audit_id,
            Question.qid == qid
        ).first()
        if not question or not question.ownership_assignment:
            raise ValueError("Ownership assignment not found for QID")

        assignment = question.ownership_assignment
        # Create a copy of the list to ensure SQLAlchemy detects the change
        links = list(assignment.manual_section_links or [])

        new_link = {
            "manual_type": manual_type,
            "section": section
        }
        if reference:
            new_link["reference"] = reference
        if notes:
            new_link["notes"] = notes
        if added_by:
            new_link["added_by"] = added_by

        if not any(
            (l.get("manual_type") or l.get("manual")) == manual_type
            and (l.get("section") or l.get("reference")) == section
            and (l.get("reference") or "") == (reference or "")
            for l in links
        ):
            links.append(new_link)

        assignment.manual_section_links = links
        # If previously excluded, remove from exclusions list
        # Create a new list to ensure SQLAlchemy detects the change
        exclusions = [
            e for e in (assignment.manual_section_exclusions or [])
            if not (
                (e.get("manual_type") or e.get("manual") or "").upper() == manual_type
                and (e.get("section") or e.get("section_number") or e.get("reference")) == section
            )
        ]
        assignment.manual_section_exclusions = exclusions
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return assignment.to_dict()


def remove_manual_section_link(audit_id: str, qid: str, manual_type: str, section: str,
                               reference: str = None, removed_by: str = None) -> dict:
    """
    Remove a manual section link and exclude it from auto-suggestions.
    """
    if not qid:
        raise ValueError("QID is required")
    if not manual_type or not section:
        raise ValueError("manual_type and section are required")

    manual_type = manual_type.strip().upper()
    section = section.strip()
    reference = reference.strip() if reference else None

    with get_session() as session:
        question = session.query(Question).filter(
            Question.audit_id == audit_id,
            Question.qid == qid
        ).first()
        if not question or not question.ownership_assignment:
            raise ValueError("Ownership assignment not found for QID")

        assignment = question.ownership_assignment
        # Create a copy to ensure SQLAlchemy detects the change
        links = list(assignment.manual_section_links or [])

        if manual_type == "ANY":
            def _match(link):
                return (
                    (link.get("section") or link.get("section_number") or link.get("reference")) == section
                    and (reference is None or (link.get("reference") or "") == reference)
                )
        else:
            def _match(link):
                return (
                    (link.get("manual_type") or link.get("manual") or "").upper() == manual_type
                    and (link.get("section") or link.get("section_number") or link.get("reference")) == section
                    and (reference is None or (link.get("reference") or "") == reference)
                )

        links = [l for l in links if not _match(l)]
        assignment.manual_section_links = links

        # Create a copy to ensure SQLAlchemy detects the change
        exclusions = list(assignment.manual_section_exclusions or [])
        exclusion_types = [manual_type]
        if manual_type == "ANY":
            exclusion_types = set()
            # Include types from existing links
            for l in assignment.manual_section_links or []:
                if (l.get("section") or l.get("section_number") or l.get("reference")) == section:
                    exclusion_types.add((l.get("manual_type") or l.get("manual") or "OTHER").upper())
            # Include types from auto-suggestions
            try:
                import manual_mapper
                sections_by_type = manual_mapper.load_latest_manual_sections(session)
                suggestions = manual_mapper.suggest_manual_links(question, sections_by_type)
                for s in suggestions:
                    if (s.get("section") or s.get("section_number") or s.get("reference")) == section:
                        exclusion_types.add((s.get("manual_type") or s.get("manual") or "OTHER").upper())
            except Exception:
                pass
            if not exclusion_types:
                exclusion_types = {"ANY"}

        for mtype in exclusion_types:
            exclude_entry = {"manual_type": mtype, "section": section}
            if reference:
                exclude_entry["reference"] = reference
            if removed_by:
                exclude_entry["removed_by"] = removed_by
            if exclude_entry not in exclusions:
                exclusions.append(exclude_entry)
        assignment.manual_section_exclusions = exclusions

        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return assignment.to_dict()


# =============================================================================
# APPLICABILITY FUNCTIONS
# =============================================================================

def get_applicability_for_audit(audit_id: str) -> list:
    """
    Get applicability status for all questions in an audit.
    """
    with get_session() as session:
        rows = (
            session.query(Question, QuestionApplicability)
            .outerjoin(QuestionApplicability, QuestionApplicability.question_id == Question.id)
            .filter(Question.audit_id == audit_id)
            .all()
        )

        results = []
        for question, applicability in rows:
            results.append({
                "qid": question.qid,
                "question_id": question.id,
                "is_applicable": applicability.is_applicable if applicability else True,
                "determined_by": applicability.determined_by if applicability else None,
                "reason": applicability.reason if applicability else None,
                "last_modified_date": applicability.last_modified_date.isoformat()
                if applicability and applicability.last_modified_date else None
            })
        return results


def set_applicability(audit_id: str, qid: str, is_applicable: bool,
                      reason: str = "", determined_by: str = "manual") -> dict:
    """
    Set applicability for a question. Manual updates override auto.
    """
    with get_session() as session:
        question = session.query(Question).filter(
            Question.audit_id == audit_id,
            Question.qid == qid
        ).first()

        if not question:
            return None

        applicability = session.query(QuestionApplicability).filter(
            QuestionApplicability.question_id == question.id
        ).first()

        if applicability:
            if applicability.determined_by == "manual" and determined_by == "auto":
                return applicability.to_dict()
            applicability.is_applicable = is_applicable
            applicability.reason = reason
            applicability.determined_by = determined_by
        else:
            applicability = QuestionApplicability(
                question_id=question.id,
                is_applicable=is_applicable,
                reason=reason,
                determined_by=determined_by
            )
            session.add(applicability)

        session.commit()
        session.refresh(applicability)
        return applicability.to_dict()


def auto_determine_applicability(audit_id: str) -> dict:
    """
    Run auto applicability detection for all questions in an audit.
    """
    from applicability import detect_applicability

    updated = 0
    skipped_manual = 0

    with get_session() as session:
        questions = session.query(Question).filter(Question.audit_id == audit_id).all()
        for question in questions:
            text = " ".join(filter(None, [
                question.question_text_full,
                question.question_text_condensed,
                question.data_collection_guidance
            ]))
            result = detect_applicability(text)
            if not result:
                continue

            is_applicable, reason = result
            applicability = session.query(QuestionApplicability).filter(
                QuestionApplicability.question_id == question.id
            ).first()

            if applicability and applicability.determined_by == "manual":
                skipped_manual += 1
                continue

            if applicability:
                applicability.is_applicable = is_applicable
                applicability.reason = reason
                applicability.determined_by = "auto"
            else:
                applicability = QuestionApplicability(
                    question_id=question.id,
                    is_applicable=is_applicable,
                    reason=reason,
                    determined_by="auto"
                )
                session.add(applicability)

            updated += 1

        session.commit()

    return {
        "updated": updated,
        "skipped_manual": skipped_manual
    }


# =============================================================================
# OWNERSHIP ASSIGNMENT FUNCTIONS
# =============================================================================

def save_ownership_assignments(audit_id: str, assignments: list) -> int:
    """
    Save ownership assignments for an audit's questions.

    Args:
        audit_id: The audit ID
        assignments: List of assignment dictionaries from ownership engine

    Returns:
        Number of assignments saved
    """
    from datetime import datetime

    with get_session() as session:
        # Get all questions for this audit
        questions = session.query(Question).filter(Question.audit_id == audit_id).all()
        qid_to_question = {q.qid: q for q in questions}

        count = 0
        for assignment in assignments:
            qid = assignment.get("qid")
            question = qid_to_question.get(qid)

            if not question:
                continue

            # Check if assignment already exists
            existing = session.query(OwnershipAssignment).filter(
                OwnershipAssignment.question_id == question.id
            ).first()

            if existing:
                # Update existing assignment (only if not manually overridden)
                if not existing.is_manual_override:
                    existing.primary_function = assignment.get("primary_function")
                    existing.supporting_functions = assignment.get("supporting_functions", [])
                    existing.rationale = assignment.get("rationale", "")
                    existing.confidence_score = assignment.get("confidence_score", "Low")
                    existing.confidence_value = assignment.get("confidence_value", 0.0)
                    existing.keyword_matches = assignment.get("keyword_matches", [])
                    existing.cfr_matches = assignment.get("cfr_matches", [])
                    existing.assigned_date = datetime.utcnow()
            else:
                # Create new assignment
                new_assignment = OwnershipAssignment(
                    question_id=question.id,
                    primary_function=assignment.get("primary_function"),
                    supporting_functions=assignment.get("supporting_functions", []),
                    rationale=assignment.get("rationale", ""),
                    confidence_score=assignment.get("confidence_score", "Low"),
                    confidence_value=assignment.get("confidence_value", 0.0),
                    keyword_matches=assignment.get("keyword_matches", []),
                    cfr_matches=assignment.get("cfr_matches", []),
                    is_manual_override=False
                )
                session.add(new_assignment)

            count += 1

        session.commit()
        return count


def get_ownership_assignments(audit_id: str) -> list:
    """
    Get all ownership assignments for an audit.

    Args:
        audit_id: The audit ID

    Returns:
        List of assignment dictionaries
    """
    with get_session() as session:
        # Join questions with their ownership assignments
        questions = session.query(Question).filter(Question.audit_id == audit_id).all()

        assignments = []
        for q in questions:
            if q.ownership_assignment:
                assignment_dict = q.ownership_assignment.to_dict()
                # Add question info for context
                assignment_dict["qid"] = q.qid
                assignment_dict["question_number"] = q.question_number
                assignment_dict["question_text_condensed"] = q.question_text_condensed
                assignments.append(assignment_dict)

        return assignments


def override_ownership_assignment(audit_id: str, qid: str, primary_function: str,
                                  supporting_functions: list = None,
                                  override_reason: str = "",
                                  override_by: str = "") -> bool:
    """
    Manually override ownership assignment for a question.

    Args:
        audit_id: The audit ID
        qid: The question ID (QID)
        primary_function: New primary function assignment
        supporting_functions: Optional list of supporting functions
        override_reason: Reason for the override
        override_by: Person making the override

    Returns:
        True if updated, False if not found
    """
    from datetime import datetime

    with get_session() as session:
        # Find the question
        question = session.query(Question).filter(
            Question.audit_id == audit_id,
            Question.qid == qid
        ).first()

        if not question:
            return False

        # Find or create assignment
        assignment = session.query(OwnershipAssignment).filter(
            OwnershipAssignment.question_id == question.id
        ).first()

        if not assignment:
            # Create new assignment with override
            assignment = OwnershipAssignment(
                question_id=question.id,
                primary_function=primary_function,
                supporting_functions=supporting_functions or [],
                rationale=f"Manual override: {override_reason}",
                confidence_score="High",  # Manual overrides are considered high confidence
                confidence_value=1.0,
                is_manual_override=True,
                override_reason=override_reason,
                override_by=override_by,
                override_date=datetime.utcnow()
            )
            session.add(assignment)
        else:
            # Update existing assignment
            assignment.primary_function = primary_function
            assignment.supporting_functions = supporting_functions or []
            assignment.is_manual_override = True
            assignment.override_reason = override_reason
            assignment.override_by = override_by
            assignment.override_date = datetime.utcnow()
            assignment.rationale = f"Manual override: {override_reason}"
            assignment.confidence_score = "High"
            assignment.confidence_value = 1.0

        session.commit()
        return True


def add_ownership_rule(rule_type: str, pattern: str, target_function: str,
                       weight: float = 1.0, notes: str = None) -> int:
    """
    Add a custom ownership rule.

    Args:
        rule_type: "keyword" or "cfr"
        pattern: Regex pattern to match
        target_function: Target function name
        weight: Weight for scoring
        notes: Optional notes about the rule

    Returns:
        The new rule ID
    """
    with get_session() as session:
        rule = OwnershipRule(
            rule_type=rule_type,
            pattern=pattern,
            target_function=target_function,
            weight=weight,
            notes=notes,
            is_active=True
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return rule.id


def get_custom_ownership_rules() -> list:
    """
    Get all custom ownership rules.

    Returns:
        List of rule dictionaries
    """
    with get_session() as session:
        rules = session.query(OwnershipRule).filter(OwnershipRule.is_active == True).all()
        return [r.to_dict() for r in rules]


def get_ownership_summary() -> dict:
    """
    Get ownership summary statistics across all audits.

    Returns:
        Summary dictionary with statistics
    """
    with get_session() as session:
        # Count total assignments
        total = session.query(OwnershipAssignment).count()

        if total == 0:
            return {
                "total_assignments": 0,
                "by_function": {},
                "by_confidence": {},
                "manual_overrides": 0,
                "audits_with_assignments": 0
            }

        # Count by function
        from sqlalchemy import func
        by_function_query = session.query(
            OwnershipAssignment.primary_function,
            func.count(OwnershipAssignment.id)
        ).group_by(OwnershipAssignment.primary_function).all()
        by_function = {row[0]: row[1] for row in by_function_query}

        # Count by confidence
        by_confidence_query = session.query(
            OwnershipAssignment.confidence_score,
            func.count(OwnershipAssignment.id)
        ).group_by(OwnershipAssignment.confidence_score).all()
        by_confidence = {row[0]: row[1] for row in by_confidence_query}

        # Count manual overrides
        manual_overrides = session.query(OwnershipAssignment).filter(
            OwnershipAssignment.is_manual_override == True
        ).count()

        # Count audits with assignments
        audits_with_assignments = session.query(
            func.count(func.distinct(Question.audit_id))
        ).join(OwnershipAssignment).scalar()

        return {
            "total_assignments": total,
            "by_function": by_function,
            "by_confidence": by_confidence,
            "function_percentages": {f: round(c / total * 100, 1) for f, c in by_function.items()},
            "manual_overrides": manual_overrides,
            "audits_with_assignments": audits_with_assignments
        }


# =============================================================================
# AUDIT SCOPE FUNCTIONS (Phase 3)
# =============================================================================

def save_audit_scope(audit_id: str, in_scope_functions: list,
                     scope_name: str = None, scope_rationale: str = None,
                     created_by: str = None) -> dict:
    """
    Save or update audit scope configuration.

    Args:
        audit_id: The audit ID
        in_scope_functions: List of function names that are in-scope
        scope_name: Optional name for the scope
        scope_rationale: Optional rationale for scope selection
        created_by: Person creating the scope

    Returns:
        Dictionary representation of the saved scope
    """
    from datetime import datetime

    with get_session() as session:
        # Verify audit exists
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return None

        # Check for existing scope
        existing = session.query(AuditScope).filter(
            AuditScope.audit_id == audit_id
        ).first()

        if existing:
            # Update existing scope
            existing.in_scope_functions = in_scope_functions
            existing.scope_name = scope_name
            existing.scope_rationale = scope_rationale
            existing.last_modified_date = datetime.utcnow()
            session.commit()
            session.refresh(existing)
            return existing.to_dict()
        else:
            # Create new scope
            scope = AuditScope(
                audit_id=audit_id,
                in_scope_functions=in_scope_functions,
                scope_name=scope_name,
                scope_rationale=scope_rationale,
                created_by=created_by
            )
            session.add(scope)
            session.commit()
            session.refresh(scope)
            return scope.to_dict()


def get_audit_scope(audit_id: str) -> dict:
    """
    Get audit scope configuration.

    Args:
        audit_id: The audit ID

    Returns:
        Dictionary with scope info, or None if no scope defined
    """
    with get_session() as session:
        scope = session.query(AuditScope).filter(
            AuditScope.audit_id == audit_id
        ).first()

        if scope:
            return scope.to_dict()
        return None


def delete_audit_scope(audit_id: str) -> bool:
    """
    Delete audit scope (reset to all functions).

    Args:
        audit_id: The audit ID

    Returns:
        True if deleted, False if not found
    """
    with get_session() as session:
        scope = session.query(AuditScope).filter(
            AuditScope.audit_id == audit_id
        ).first()

        if scope:
            session.delete(scope)
            session.commit()
            return True
        return False


def get_scoped_ownership_assignments(audit_id: str) -> dict:
    """
    Get ownership assignments with scope filtering applied.

    Args:
        audit_id: The audit ID

    Returns:
        Dictionary with in_scope and deferred assignments
    """
    from scoping import filter_assignments_by_scope, VALID_FUNCTIONS

    # Get all assignments
    assignments = get_ownership_assignments(audit_id)

    # Get scope
    scope = get_audit_scope(audit_id)

    if scope and scope.get("in_scope_functions"):
        in_scope_functions = scope["in_scope_functions"]
    else:
        # No scope defined = all functions in scope
        in_scope_functions = VALID_FUNCTIONS

    in_scope, deferred = filter_assignments_by_scope(assignments, in_scope_functions)

    return {
        "audit_id": audit_id,
        "in_scope_functions": in_scope_functions,
        "in_scope_assignments": in_scope,
        "deferred_assignments": deferred,
        "in_scope_count": len(in_scope),
        "deferred_count": len(deferred),
        "total": len(assignments)
    }


# Initialize database on import
init_db()
