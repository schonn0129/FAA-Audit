"""
SQLAlchemy models for the FAA Audit application.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
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

    # Relationship
    audit = relationship("Audit", back_populates="questions")

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
