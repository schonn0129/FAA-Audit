"""
SQLAlchemy models for the FAA Audit application.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Audit(Base):
    """
    Represents a parsed PDF audit document.
    """
    __tablename__ = 'audits'

    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='processed')
    page_count = Column(Integer, default=0)

    # Metadata extracted from PDF
    inspection_date = Column(String(50), nullable=True)
    inspector_name = Column(String(255), nullable=True)
    facility_name = Column(String(255), nullable=True)
    facility_number = Column(String(100), nullable=True)
    document_type = Column(String(100), nullable=True)
    element_id = Column(String(50), nullable=True)  # e.g., "4.2.1"

    # Raw text length for reference
    raw_text_length = Column(Integer, default=0)

    # Compliance data
    compliance_status = Column(String(50), nullable=True)
    total_findings = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    major_findings = Column(Integer, default=0)
    minor_findings = Column(Integer, default=0)
    compliance_percentage = Column(Integer, nullable=True)

    # Relationships
    questions = relationship("Question", back_populates="audit", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="audit", cascade="all, delete-orphan")
    tables = relationship("ExtractedTable", back_populates="audit", cascade="all, delete-orphan")
    scope = relationship("AuditScope", back_populates="audit", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "filename": self.filename,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "status": self.status,
            "page_count": self.page_count,
            "metadata": {
                "inspection_date": self.inspection_date,
                "inspector_name": self.inspector_name,
                "facility_name": self.facility_name,
                "facility_number": self.facility_number,
                "document_type": self.document_type,
                "page_count": self.page_count,
                "element_id": self.element_id
            },
            "questions": [q.to_dict() for q in self.questions],
            "findings": [f.to_dict() for f in self.findings],
            "tables": [t.to_dict() for t in self.tables],
            "compliance": {
                "compliance_status": self.compliance_status,
                "total_findings": self.total_findings,
                "critical_findings": self.critical_findings,
                "major_findings": self.major_findings,
                "minor_findings": self.minor_findings,
                "compliance_percentage": self.compliance_percentage
            },
            "raw_text_length": self.raw_text_length
        }


class Question(Base):
    """
    Represents a DCT question extracted from a PDF.
    """
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(36), ForeignKey('audits.id'), nullable=False)

    element_id = Column(String(50), nullable=True)  # e.g., "4.2.1"
    qid = Column(String(20), nullable=True)  # e.g., "00004334"
    question_number = Column(String(10), nullable=True)  # e.g., "1", "2", "3"
    question_text_full = Column(Text, nullable=True)
    question_text_condensed = Column(String(255), nullable=True)
    data_collection_guidance = Column(Text, nullable=True)
    reference_raw = Column(Text, nullable=True)
    reference_cfr_list = Column(JSON, default=list)  # List of CFR references
    reference_faa_guidance_list = Column(JSON, default=list)  # List of FAA guidance
    reference_other_list = Column(JSON, default=list)  # Other references
    pdf_page_number = Column(Integer, nullable=True)
    pdf_element_block_id = Column(String(100), nullable=True)
    notes = Column(JSON, default=list)  # List of notes

    # Relationships
    audit = relationship("Audit", back_populates="questions")
    ownership_assignment = relationship("OwnershipAssignment",
                                       back_populates="question",
                                       uselist=False,
                                       cascade="all, delete-orphan")
    applicability = relationship("QuestionApplicability",
                                 back_populates="question",
                                 uselist=False,
                                 cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "Element_ID": self.element_id,
            "QID": self.qid,
            "Question_Number": self.question_number,
            "Question_Text_Full": self.question_text_full,
            "Question_Text_Condensed": self.question_text_condensed,
            "Data_Collection_Guidance": self.data_collection_guidance,
            "Reference_Raw": self.reference_raw,
            "Reference_CFR_List": self.reference_cfr_list or [],
            "Reference_FAA_Guidance_List": self.reference_faa_guidance_list or [],
            "Reference_Other_List": self.reference_other_list or [],
            "PDF_Page_Number": self.pdf_page_number,
            "PDF_Element_Block_ID": self.pdf_element_block_id,
            "Notes": self.notes or []
        }


class QuestionApplicability(Base):
    """
    Represents applicability status for a DCT question (per audit).
    """
    __tablename__ = 'question_applicability'

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False, unique=True)

    is_applicable = Column(Boolean, default=True)
    determined_by = Column(String(50), nullable=True)  # "auto" or "manual"
    reason = Column(Text, nullable=True)
    determined_date = Column(DateTime, default=datetime.utcnow)
    last_modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    question = relationship("Question", back_populates="applicability")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "question_id": self.question_id,
            "is_applicable": self.is_applicable,
            "determined_by": self.determined_by,
            "reason": self.reason,
            "determined_date": self.determined_date.isoformat() if self.determined_date else None,
            "last_modified_date": self.last_modified_date.isoformat() if self.last_modified_date else None
        }


class Finding(Base):
    """
    Represents an audit finding or violation.
    """
    __tablename__ = 'findings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(36), ForeignKey('audits.id'), nullable=False)

    number = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    finding_type = Column(String(50), nullable=True)  # "finding" or "violation"
    severity = Column(String(50), nullable=True)  # "critical", "major", "minor", "unknown"

    # Relationship
    audit = relationship("Audit", back_populates="findings")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "number": self.number,
            "description": self.description,
            "type": self.finding_type,
            "severity": self.severity
        }


class ExtractedTable(Base):
    """
    Represents a table extracted from a PDF.
    """
    __tablename__ = 'extracted_tables'

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(36), ForeignKey('audits.id'), nullable=False)

    page = Column(Integer, nullable=True)
    headers = Column(JSON, default=list)
    rows = Column(JSON, default=list)
    row_count = Column(Integer, default=0)

    # Relationship
    audit = relationship("Audit", back_populates="tables")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "page": self.page,
            "headers": self.headers or [],
            "rows": self.rows or [],
            "row_count": self.row_count
        }


class Manual(Base):
    """
    Represents an uploaded company manual (AIP or GMM).
    """
    __tablename__ = 'manuals'

    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    manual_type = Column(String(50), nullable=False)  # "AIP" or "GMM"
    upload_date = Column(DateTime, default=datetime.utcnow)
    version = Column(String(50), nullable=True)  # Manual version
    page_count = Column(Integer, default=0)
    status = Column(String(50), default='processed')

    # Relationships
    sections = relationship("ManualSection", back_populates="manual", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "filename": self.filename,
            "manual_type": self.manual_type,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "version": self.version,
            "page_count": self.page_count,
            "status": self.status,
            "section_count": len(self.sections) if self.sections else 0
        }


class ManualSection(Base):
    """
    Represents an extracted section from a company manual.
    """
    __tablename__ = 'manual_sections'

    id = Column(Integer, primary_key=True, autoincrement=True)
    manual_id = Column(String(36), ForeignKey('manuals.id'), nullable=False)

    section_number = Column(String(100), nullable=True)  # "5.2.1", "Chapter 3"
    section_title = Column(String(500), nullable=True)
    section_text = Column(Text, nullable=True)  # Full section content
    page_number = Column(Integer, nullable=True)

    # Extracted CFR citations found in this section
    cfr_citations = Column(JSON, default=list)  # ["14 CFR 121.369", ...]

    # Suggested owner based on content
    suggested_owner = Column(String(50), nullable=True)

    # Relationships
    manual = relationship("Manual", back_populates="sections")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "manual_id": self.manual_id,
            "section_number": self.section_number,
            "section_title": self.section_title,
            "section_text": self.section_text,
            "page_number": self.page_number,
            "cfr_citations": self.cfr_citations or [],
            "suggested_owner": self.suggested_owner
        }


class OwnershipAssignment(Base):
    """
    Represents ownership assignment for a DCT question.
    """
    __tablename__ = 'ownership_assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False, unique=True)

    # Primary assignment
    primary_function = Column(String(50), nullable=False)  # One of 7 functions
    supporting_functions = Column(JSON, default=list)  # ["MOC", "Quality"]

    # Rationale and confidence
    rationale = Column(Text, nullable=False)
    confidence_score = Column(String(20), nullable=False)  # "High", "Medium", "Low"
    confidence_value = Column(Float, nullable=True)  # 0.0-1.0

    # Signal breakdown (transparency)
    keyword_matches = Column(JSON, default=list)
    cfr_matches = Column(JSON, default=list)
    manual_section_links = Column(JSON, default=list)  # [{"section": "5.2.1", "manual": "AIP"}]

    # Manual override support
    is_manual_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    override_by = Column(String(100), nullable=True)
    override_date = Column(DateTime, nullable=True)

    # Metadata
    assigned_date = Column(DateTime, default=datetime.utcnow)
    assignment_version = Column(String(50), nullable=True)

    # Relationships
    question = relationship("Question", back_populates="ownership_assignment")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "question_id": self.question_id,
            "primary_function": self.primary_function,
            "supporting_functions": self.supporting_functions or [],
            "rationale": self.rationale,
            "confidence_score": self.confidence_score,
            "confidence_value": self.confidence_value,
            "keyword_matches": self.keyword_matches or [],
            "cfr_matches": self.cfr_matches or [],
            "manual_section_links": self.manual_section_links or [],
            "is_manual_override": self.is_manual_override,
            "override_reason": self.override_reason,
            "override_by": self.override_by,
            "override_date": self.override_date.isoformat() if self.override_date else None,
            "assigned_date": self.assigned_date.isoformat() if self.assigned_date else None,
            "assignment_version": self.assignment_version
        }


class OwnershipRule(Base):
    """
    Represents a configurable ownership assignment rule.
    """
    __tablename__ = 'ownership_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_type = Column(String(50), nullable=False)  # "keyword", "cfr"
    pattern = Column(String(255), nullable=False)
    target_function = Column(String(50), nullable=False)
    weight = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "rule_type": self.rule_type,
            "pattern": self.pattern,
            "target_function": self.target_function,
            "weight": self.weight,
            "is_active": self.is_active,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "notes": self.notes
        }


class AuditScope(Base):
    """
    Represents the scoping configuration for an audit.

    Defines which of the 7 functions are "in-scope" for the current
    audit cycle. Questions belonging to out-of-scope functions are
    tracked as "deferred" items.

    Key Design: Scope is a FILTER/VIEW, not a modification of the
    ownership table. All QIDs remain assigned to their functions
    regardless of audit scope.
    """
    __tablename__ = 'audit_scopes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(36), ForeignKey('audits.id'), nullable=False, unique=True)

    # Functions included in scope (stored as JSON list)
    # Example: ["Maintenance Planning", "Aircraft Records", "Quality"]
    in_scope_functions = Column(JSON, nullable=False, default=list)

    # Scope metadata
    scope_name = Column(String(255), nullable=True)
    scope_rationale = Column(Text, nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    last_modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    audit = relationship("Audit", back_populates="scope")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "audit_id": self.audit_id,
            "in_scope_functions": self.in_scope_functions or [],
            "scope_name": self.scope_name,
            "scope_rationale": self.scope_rationale,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "created_by": self.created_by,
            "last_modified_date": self.last_modified_date.isoformat() if self.last_modified_date else None
        }
