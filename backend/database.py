"""
Database connection and session management for the FAA Audit application.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

from config import DATABASE_URL
from models import Base, Audit, Question, Finding, ExtractedTable

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)
    print(f"Database initialized at {DATABASE_URL}")


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


# Initialize database on import
init_db()
