"""
Company Manual PDF parser.

Extracts structured sections and CFR citations from uploaded manuals
for deterministic MAP reference suggestions.
"""

import re
import logging
from typing import Dict, List, Any, Optional

import pdfplumber

logger = logging.getLogger(__name__)

SECTION_PATTERNS = [
    re.compile(r'^(CHAPTER|Chapter)\s+([0-9IVX]+)\b\.?\s*(.*)$'),
    re.compile(r'^(SECTION|Section)\s+(\d+(?:\.\d+){0,4})\b\.?\s*(.*)$'),
    re.compile(r'^(\d+(?:\.\d+){1,4})\s*[-–—:]?\s*(.+)$'),
]

CFR_PATTERN = re.compile(
    r'\b\d+\s*CFR\s*(?:Part\s*)?\d+\.\d+[a-z0-9\.\(\)]*',
    re.IGNORECASE
)


def _match_heading(line: str) -> Optional[Dict[str, str]]:
    """Return section metadata if the line matches a heading pattern."""
    for pattern in SECTION_PATTERNS:
        match = pattern.match(line)
        if match:
            if len(match.groups()) == 3:
                section_number = match.group(2)
                section_title = match.group(3) or ""
            else:
                section_number = match.group(1)
                section_title = match.group(2) or ""
            return {
                "section_number": section_number.strip(),
                "section_title": section_title.strip()
            }
    return None


def _extract_version(text: str) -> Optional[str]:
    """Extract a version or revision string if present."""
    patterns = [
        r'\bRevision\s+([A-Za-z0-9\.\-]+)',
        r'\bVersion\s+([A-Za-z0-9\.\-]+)',
        r'\bRev\.\s*([A-Za-z0-9\.\-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_manual_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Parse a company manual PDF into structured sections.

    Returns:
        Dict with metadata and list of sections.
    """
    sections: List[Dict[str, Any]] = []
    page_texts: List[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            page_texts.append(text)

            lines = [line.strip() for line in text.split('\n') if line.strip()]
            current = None

            for line in lines:
                heading = _match_heading(line)
                if heading:
                    if current:
                        sections.append(current)
                    current = {
                        "section_number": heading.get("section_number"),
                        "section_title": heading.get("section_title"),
                        "section_text": "",
                        "page_number": page_num
                    }
                    continue

                if current:
                    current["section_text"] += (line + " ")

            if current:
                sections.append(current)

    if not sections:
        combined_text = "\n\n".join(page_texts).strip()
        if combined_text:
            sections = [{
                "section_number": None,
                "section_title": "Manual Text",
                "section_text": combined_text,
                "page_number": 1
            }]

    for section in sections:
        text = section.get("section_text", "")
        citations = CFR_PATTERN.findall(text or "")
        section["cfr_citations"] = sorted(set(citations))

    combined_all = "\n\n".join(page_texts)
    return {
        "page_count": len(page_texts),
        "version": _extract_version(combined_all),
        "sections": sections
    }
