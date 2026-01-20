"""
PDF Parser for FAA Audit Documents

This module handles parsing of PDF audit documents, extracting structured data
from various FAA audit report formats.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pdfplumber
from pdfplumber.table import Table

logger = logging.getLogger(__name__)


class FAAPDFParser:
    """
    Parser for FAA audit PDF documents.
    
    Handles extraction of:
    - Document metadata (dates, inspector names, facility info)
    - Audit findings and violations
    - Questions and questionnaire items
    - Compliance data
    - Tables and structured data
    """
    
    def __init__(self, pdf_path: str):
        """
        Initialize the PDF parser.
        
        Args:
            pdf_path: Path to the PDF file to parse
        """
        self.pdf_path = pdf_path
        self.pdf = None
        self.text_content = None
        self.pages = []
        
    def __enter__(self):
        """Context manager entry."""
        self.pdf = pdfplumber.open(self.pdf_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.pdf:
            self.pdf.close()
    
    def extract_text(self) -> str:
        """
        Extract all text content from the PDF.
        
        Returns:
            Combined text from all pages
        """
        if self.text_content is None:
            text_parts = []
            for page in self.pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            self.text_content = "\n\n".join(text_parts)
        return self.text_content
    
    def find_text_on_page(self, search_text: str) -> Optional[int]:
        """
        Find which page contains the given text.
        
        Args:
            search_text: Text to search for
            
        Returns:
            Page number (1-indexed) or None if not found
        """
        for page_num, page in enumerate(self.pdf.pages, 1):
            text = page.extract_text()
            if text and search_text in text:
                return page_num
        return None
    
    def debug_extract_patterns(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Debug method to identify potential question patterns in the PDF.
        Useful for understanding what formats are present but not being captured.
        
        Args:
            output_file: Optional file path to write debug output
            
        Returns:
            Dictionary with potential patterns found
        """
        text = self.extract_text()
        lines = text.split('\n')
        
        debug_info = {
            "total_lines": len(lines),
            "total_chars": len(text),
            "potential_questions": [],
            "numbered_items": [],
            "question_marks": [],
            "table_structures": []
        }
        
        # Find lines that start with numbers or letters followed by numbers
        for i, line in enumerate(lines[:100]):  # Check first 100 lines
            line_stripped = line.strip()
            
            # Check for numbered patterns
            if re.match(r'^\d+[\.\)]\s+', line_stripped):
                debug_info["numbered_items"].append({
                    "line": i + 1,
                    "text": line_stripped[:100]  # First 100 chars
                })
            
            # Check for Q patterns
            if re.match(r'^Q\s*\d+', line_stripped, re.IGNORECASE):
                debug_info["potential_questions"].append({
                    "line": i + 1,
                    "text": line_stripped[:100]
                })
            
            # Check for question marks
            if '?' in line_stripped:
                debug_info["question_marks"].append({
                    "line": i + 1,
                    "text": line_stripped[:100]
                })
        
        # Get table info
        tables = self.extract_tables()
        for table in tables:
            if table.get("headers"):
                debug_info["table_structures"].append({
                    "page": table.get("page"),
                    "headers": table.get("headers"),
                    "row_count": table.get("row_count")
                })
        
        if output_file:
            import json
            with open(output_file, 'w') as f:
                json.dump(debug_info, f, indent=2)
        
        return debug_info
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract document metadata from the PDF.
        
        Looks for:
        - Inspection dates
        - Inspector names
        - Facility information
        - Document numbers
        
        Returns:
            Dictionary containing extracted metadata
        """
        text = self.extract_text()
        metadata = {
            "inspection_date": None,
            "inspector_name": None,
            "facility_name": None,
            "facility_number": None,
            "document_type": None,
            "page_count": len(self.pdf.pages)
        }
        
        # Extract inspection date (common formats)
        date_patterns = [
            r'Inspection Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Date of Inspection[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try to parse the date
                    for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y']:
                        try:
                            metadata["inspection_date"] = datetime.strptime(date_str, fmt).isoformat()
                            break
                        except ValueError:
                            continue
                    if metadata["inspection_date"]:
                        break
                except Exception as e:
                    logger.warning(f"Error parsing date: {e}")
        
        # Extract inspector name
        inspector_patterns = [
            r'Inspector[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'Inspector Name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        
        for pattern in inspector_patterns:
            match = re.search(pattern, text)
            if match:
                metadata["inspector_name"] = match.group(1).strip()
                break
        
        # Extract facility information
        facility_patterns = [
            r'Facility[:\s]+([^\n]+)',
            r'Facility Name[:\s]+([^\n]+)',
        ]
        
        for pattern in facility_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["facility_name"] = match.group(1).strip()
                break
        
        # Extract facility number
        facility_num_match = re.search(r'Facility\s*(?:Number|#)[:\s]+([A-Z0-9-]+)', text, re.IGNORECASE)
        if facility_num_match:
            metadata["facility_number"] = facility_num_match.group(1).strip()
        
        # Determine document type
        if re.search(r'audit|inspection', text, re.IGNORECASE):
            metadata["document_type"] = "audit"
        elif re.search(r'violation|finding', text, re.IGNORECASE):
            metadata["document_type"] = "violation_report"
        else:
            metadata["document_type"] = "unknown"
        
        return metadata
    
    def extract_tables(self) -> List[Dict[str, Any]]:
        """
        Extract all tables from the PDF.
        
        Returns:
            List of tables, each represented as a dictionary with headers and rows
        """
        tables = []
        
        for page_num, page in enumerate(self.pdf.pages, 1):
            page_tables = page.extract_tables()
            
            for table in page_tables:
                if table and len(table) > 0:
                    # First row is typically headers
                    headers = table[0] if table else []
                    rows = table[1:] if len(table) > 1 else []
                    
                    tables.append({
                        "page": page_num,
                        "headers": headers,
                        "rows": rows,
                        "row_count": len(rows)
                    })
        
        return tables
    
    def extract_findings(self) -> List[Dict[str, Any]]:
        """
        Extract audit findings and violations from the PDF.

        Looks for:
        - Finding numbers
        - Violation codes
        - Descriptions
        - Severity levels

        Returns:
            List of findings with their details
        """
        text = self.extract_text()
        findings = []

        # Pattern to find actual audit findings (not CFR references in questions)
        # Look for explicit "Finding" or "Violation" labels followed by descriptions
        finding_patterns = [
            # "Finding 1:" or "Finding #1:" followed by description
            r'Finding\s+#?(\d+)\s*[:\.]\s*(.+?)(?=Finding\s+#?\d+|Violation|$)',
            # "Violation:" followed by description
            r'Violation\s*[:\.]\s*(.+?)(?=Violation|Finding|$)',
        ]

        for pattern in finding_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Skip if this looks like a question or reference (contains QID, REFERENCES, etc.)
                match_text = match.group(0)
                if any(skip in match_text for skip in ['QID:', 'REFERENCES:', 'Safety Attribute:', 'Question Type:']):
                    continue

                if len(match.groups()) > 1:
                    finding = {
                        "number": match.group(1),
                        "description": match.group(2).strip()[:500],  # Limit description length
                        "type": "finding"
                    }
                else:
                    finding = {
                        "number": None,
                        "description": match.group(1).strip()[:500] if match.group(1) else match.group(0)[:500],
                        "type": "violation"
                    }

                # Extract severity if mentioned
                severity_match = re.search(r'(critical|major|minor|serious)', finding["description"], re.IGNORECASE)
                if severity_match:
                    finding["severity"] = severity_match.group(1).lower()
                else:
                    finding["severity"] = "unknown"

                # Only add if we have a meaningful description
                if finding["description"] and len(finding["description"]) > 10:
                    findings.append(finding)

        return findings
    
    def parse_cfr_reference(self, ref_text: str) -> Dict[str, List[str]]:
        """
        Parse reference text to extract CFR citations, FAA Guidance, and other references.
        
        Args:
            ref_text: Raw reference string
            
        Returns:
            Dictionary with parsed reference lists
        """
        if not ref_text:
            return {
                "cfr_list": [],
                "faa_guidance_list": [],
                "other_list": []
            }
        
        cfr_list = []
        faa_guidance_list = []
        other_list = []
        
        # Pattern for CFR citations: 14 CFR 121.369(b), 14 CFR 121.373, etc.
        cfr_pattern = r'\d+\s+CFR\s+[\d\.]+[A-Z]?(?:\([a-z]\))?(?:;\s*\d+\s+CFR\s+[\d\.]+[A-Z]?(?:\([a-z]\))?)*'
        cfr_matches = re.findall(cfr_pattern, ref_text, re.IGNORECASE)
        for match in cfr_matches:
            # Split multiple CFRs separated by semicolons
            cfr_items = re.split(r';\s*', match)
            for cfr in cfr_items:
                cfr_clean = cfr.strip()
                if cfr_clean and cfr_clean not in cfr_list:
                    cfr_list.append(cfr_clean)
        
        # Pattern for FAA Orders, Notices, ACs
        faa_guidance_patterns = [
            r'Order\s+[\d\.]+[A-Z]?',
            r'AC\s+[\d\.]+[A-Z]?[-]?[\d]+',
            r'Notice\s+[\d\.]+',
            r'Advisory\s+Circular\s+[\d\.]+',
            r'FAA\s+Order\s+[\d\.]+',
        ]
        
        for pattern in faa_guidance_patterns:
            matches = re.findall(pattern, ref_text, re.IGNORECASE)
            for match in matches:
                match_clean = match.strip()
                if match_clean and match_clean not in faa_guidance_list:
                    faa_guidance_list.append(match_clean)
        
        # Everything else that's not CFR or FAA Guidance
        # Remove CFR and FAA guidance from text, then extract remaining references
        remaining_text = ref_text
        for cfr in cfr_list:
            remaining_text = remaining_text.replace(cfr, '')
        for faa in faa_guidance_list:
            remaining_text = remaining_text.replace(faa, '')
        
        # Extract other references (phrases that might be references)
        other_patterns = [
            r'FAA\s+DCT\s+Job\s+Aid',
            r'PMI\s+Guidance',
            r'[A-Z][a-z]+\s+Guidance',
        ]
        
        for pattern in other_patterns:
            matches = re.findall(pattern, remaining_text, re.IGNORECASE)
            for match in matches:
                match_clean = match.strip()
                if match_clean and match_clean not in other_list:
                    other_list.append(match_clean)
        
        # If there's still text left, add it as "other" if it looks like a reference
        remaining_clean = remaining_text.strip()
        if remaining_clean and len(remaining_clean) > 5 and remaining_clean not in other_list:
            # Only add if it looks like a reference (has capital letters, numbers, etc.)
            if re.search(r'[A-Z]', remaining_clean) and (re.search(r'\d', remaining_clean) or len(remaining_clean.split()) <= 5):
                other_list.append(remaining_clean)
        
        return {
            "cfr_list": cfr_list,
            "faa_guidance_list": faa_guidance_list,
            "other_list": other_list
        }
    
    def extract_questions(self) -> List[Dict[str, Any]]:
        """
        Extract DCT (Data Collection Tool) questions with all required fields.

        Extracts structured data including:
        - Element_ID (e.g., 4.2.2, 4.1.1)
        - QID (DCT Question ID)
        - Question_Number (1., 2., 3. within element)
        - Question_Text_Full (full question text)
        - Question_Text_Condensed (short label)
        - Data_Collection_Guidance
        - Reference_Raw and parsed references (CFR, FAA Guidance, Other)
        - PDF_Page_Number
        - PDF_Element_Block_ID
        - Notes

        Returns:
            List of DCT questions with all required fields
        """
        questions = []

        # Extract element ID from the document (e.g., "4.2.1" from header)
        full_text = self.extract_text()
        element_id_match = re.search(r'MLF\s+Label:\s*(\d+\.\d+\.\d+)', full_text)
        if not element_id_match:
            # Try alternate pattern
            element_id_match = re.search(r'^(\d+\.\d+\.\d+)\s+\(AW\)', full_text, re.MULTILINE)

        element_id = element_id_match.group(1) if element_id_match else "4.2.1"

        # Combine all pages text with page markers for cross-page questions
        pages_text = []
        page_boundaries = [0]  # Track where each page starts in combined text
        for page in self.pdf.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)
            page_boundaries.append(page_boundaries[-1] + len(page_text) + 2)  # +2 for \n\n separator

        combined_text = "\n\n".join(pages_text)

        # Helper function to find page number for a position in combined text
        def get_page_for_position(pos):
            for i, boundary in enumerate(page_boundaries[1:], 1):
                if pos < boundary:
                    return i
            return len(page_boundaries) - 1

        # Find all QID patterns in the entire document
        qid_pattern = r'QID:\s*(\d{8})'
        qid_matches = list(re.finditer(qid_pattern, combined_text))

        for qid_match in qid_matches:
            qid = qid_match.group(1)
            qid_pos = qid_match.start()

            # Find the question number that precedes this QID
            # Look backwards from QID position to find the question number
            text_before_qid = combined_text[:qid_pos]

            # Find question number pattern: starts with number at beginning of line or after newline
            # Pattern matches: "1 Do procedures..." or "26 Does the CAMP..."
            question_num_pattern = r'(?:^|\n)\s*(\d{1,2})\s+(Do|Does|Is|Are)\s+'
            q_matches = list(re.finditer(question_num_pattern, text_before_qid))

            if not q_matches:
                continue

            # Get the last (most recent) question number before this QID
            last_q_match = q_matches[-1]
            question_number = last_q_match.group(1)
            question_start = last_q_match.start()

            # Extract the full question text from question start to QID
            question_block = text_before_qid[question_start:]

            # Also include a bit after QID to capture any trailing metadata
            text_after_qid = combined_text[qid_pos:qid_pos + 200]
            full_block = question_block + text_after_qid

            # Extract question text - it ends before REFERENCES or Safety Attribute
            question_text_match = re.search(
                r'^\s*\d{1,2}\s+((?:Do|Does|Is|Are).+?)(?=REFERENCES:|Safety Attribute:|$)',
                question_block,
                re.DOTALL
            )

            if not question_text_match:
                continue

            question_text_full = question_text_match.group(1).strip()
            # Clean up the question text - normalize whitespace
            question_text_full = re.sub(r'\s+', ' ', question_text_full).strip()
            # Remove trailing answer options if present
            question_text_full = re.sub(r'\s*[◯○]\s*(Yes|No|Not Applicable).*$', '', question_text_full, flags=re.IGNORECASE)
            question_text_full = question_text_full.strip()

            # Extract REFERENCES - look in full block
            ref_match = re.search(r'REFERENCES:\s*([^\n]+)', full_block)
            reference_raw = ref_match.group(1).strip() if ref_match else None

            # Extract Data Collection Guidance (Safety Attribute line contains this info)
            guidance_match = re.search(
                r'Safety Attribute:\s*([^,]+),\s*Question Type:\s*([^,]+),\s*Scoping Attribute:\s*([^,]+)',
                full_block
            )
            data_collection_guidance = None
            if guidance_match:
                data_collection_guidance = f"Safety Attribute: {guidance_match.group(1)}, Question Type: {guidance_match.group(2)}, Scoping Attribute: {guidance_match.group(3)}"

            # Extract NOTE if present
            note_match = re.search(r'NOTE:\s*(.+?)(?=Safety Attribute:|QID:|$)', full_block, re.DOTALL)
            notes = []
            if note_match:
                note_text = re.sub(r'\s+', ' ', note_match.group(1)).strip()
                notes.append(note_text)

            # Parse references
            parsed_refs = self.parse_cfr_reference(reference_raw) if reference_raw else {
                "cfr_list": [],
                "faa_guidance_list": [],
                "other_list": []
            }

            # Generate condensed version
            question_text_condensed = question_text_full[:100]
            sentence_end = max(
                question_text_condensed.rfind('.'),
                question_text_condensed.rfind('?'),
                question_text_condensed.rfind('!')
            )
            if sentence_end > 50:
                question_text_condensed = question_text_condensed[:sentence_end + 1]

            # Determine page number based on question start position
            page_num = get_page_for_position(question_start)

            question = {
                "Element_ID": element_id,
                "QID": qid,
                "Question_Number": question_number,
                "Question_Text_Full": question_text_full,
                "Question_Text_Condensed": question_text_condensed.strip(),
                "Data_Collection_Guidance": data_collection_guidance,
                "Reference_Raw": reference_raw,
                "Reference_CFR_List": parsed_refs["cfr_list"],
                "Reference_FAA_Guidance_List": parsed_refs["faa_guidance_list"],
                "Reference_Other_List": parsed_refs["other_list"],
                "PDF_Page_Number": page_num,
                "PDF_Element_Block_ID": f"{element_id}_Table1",
                "Notes": notes
            }

            questions.append(question)

        # Deduplicate by QID (in case same question spans pages)
        seen_qids = set()
        unique_questions = []
        for q in questions:
            if q["QID"] not in seen_qids:
                seen_qids.add(q["QID"])
                unique_questions.append(q)

        # Sort by question number
        unique_questions.sort(key=lambda x: int(x["Question_Number"]) if x["Question_Number"] else 0)

        return unique_questions
    
    def extract_compliance_data(self) -> Dict[str, Any]:
        """
        Extract compliance-related data from the PDF.
        
        Returns:
            Dictionary containing compliance metrics and status
        """
        text = self.extract_text()
        compliance = {
            "compliance_status": None,
            "total_findings": 0,
            "critical_findings": 0,
            "major_findings": 0,
            "minor_findings": 0,
            "compliance_percentage": None
        }
        
        findings = self.extract_findings()
        compliance["total_findings"] = len(findings)
        
        for finding in findings:
            severity = finding.get("severity", "").lower()
            if "critical" in severity:
                compliance["critical_findings"] += 1
            elif "major" in severity:
                compliance["major_findings"] += 1
            elif "minor" in severity:
                compliance["minor_findings"] += 1
        
        # Look for compliance percentage
        compliance_match = re.search(r'Compliance[:\s]+(\d+)%', text, re.IGNORECASE)
        if compliance_match:
            compliance["compliance_percentage"] = int(compliance_match.group(1))
        
        # Determine overall status
        if compliance["critical_findings"] > 0:
            compliance["compliance_status"] = "non_compliant"
        elif compliance["major_findings"] > 0:
            compliance["compliance_status"] = "needs_improvement"
        elif compliance["total_findings"] == 0:
            compliance["compliance_status"] = "compliant"
        else:
            compliance["compliance_status"] = "mostly_compliant"
        
        return compliance
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse the entire PDF and extract all relevant data.
        
        Returns:
            Complete parsed data structure
        """
        try:
            metadata = self.extract_metadata()
            tables = self.extract_tables()
            findings = self.extract_findings()
            questions = self.extract_questions()
            compliance = self.extract_compliance_data()
            
            return {
                "metadata": metadata,
                "tables": tables,
                "findings": findings,
                "questions": questions,
                "compliance": compliance,
                "raw_text_length": len(self.extract_text()),
                "parsed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            raise


def parse_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Parsed data dictionary
    """
    with FAAPDFParser(pdf_path) as parser:
        return parser.parse()
