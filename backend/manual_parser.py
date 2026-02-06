"""
Company Manual PDF parser.

Extracts structured sections and CFR citations from uploaded manuals
for deterministic MAP reference suggestions.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

import pdfplumber
try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None

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


def _build_parse_report(page_texts: List[str], sections: List[Dict[str, Any]],
                        headings_by_page: Dict[int, int],
                        header_footer_lines: List[str]) -> Dict[str, Any]:
    page_count = len(page_texts)
    combined = "\n".join(page_texts)
    total_chars = len(combined)
    alnum_chars = sum(1 for c in combined if c.isalnum())
    alnum_ratio = (alnum_chars / total_chars) if total_chars else 0.0
    pages_with_text = sum(1 for t in page_texts if t.strip())
    pages_with_headings = len([p for p, count in headings_by_page.items() if count > 0])
    section_text_lengths = [len(s.get("section_text", "") or "") for s in sections]
    avg_section_chars = (
        sum(section_text_lengths) / len(section_text_lengths)
        if section_text_lengths else 0.0
    )
    avg_section_words = (
        sum(len((s.get("section_text", "") or "").split()) for s in sections) / len(sections)
        if sections else 0.0
    )

    warnings: List[str] = []
    if total_chars < 500 or pages_with_text == 0:
        warnings.append("Text extraction is very low; manual may be scanned or unreadable.")
    if not sections:
        warnings.append("No section headings detected; sectioning may be unreliable.")
    elif page_count > 10 and len(sections) < max(3, page_count // 10):
        warnings.append("Very few sections detected for the page count.")
    if avg_section_words and avg_section_words < 50:
        warnings.append("Average section length is short; matches may be weak.")
    if alnum_ratio and alnum_ratio < 0.6:
        warnings.append("Low alphanumeric density detected; text may be noisy.")
    if page_count and (pages_with_text / page_count) < 0.7:
        warnings.append("Many pages have little or no text.")
    if page_count and (pages_with_headings / page_count) < 0.2 and sections:
        warnings.append("Few pages contain headings; section boundaries may be inaccurate.")

    if total_chars < 500 or alnum_ratio < 0.3:
        quality = "fail"
    elif warnings:
        quality = "warning"
    else:
        quality = "ok"

    return {
        "quality": quality,
        "warnings": warnings,
        "metrics": {
            "page_count": page_count,
            "sections": len(sections),
            "pages_with_text": pages_with_text,
            "pages_with_headings": pages_with_headings,
            "avg_section_chars": round(avg_section_chars, 1),
            "avg_section_words": round(avg_section_words, 1),
            "alnum_ratio": round(alnum_ratio, 3),
            "header_footer_lines_removed": len(header_footer_lines)
        }
    }


def _collect_header_footer_lines(pages: List[List[str]]) -> List[str]:
    if not pages:
        return []
    candidates: Dict[str, int] = {}
    for lines in pages:
        if not lines:
            continue
        heads = lines[:2]
        tails = lines[-2:] if len(lines) > 2 else []
        for line in heads + tails:
            if len(line) > 120:
                continue
            candidates[line] = candidates.get(line, 0) + 1
    threshold = max(3, int(len(pages) * 0.3))
    return [line for line, count in candidates.items() if count >= threshold]


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


def _extract_page_texts(pdf_path: str, max_pages: Optional[int] = None
                        ) -> Tuple[List[str], List[List[str]]]:
    page_texts: List[str] = []
    page_lines: List[List[str]] = []

    if fitz is not None:
        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            limit = min(page_count, max_pages) if max_pages and max_pages > 0 else page_count
            for index in range(limit):
                text = doc.load_page(index).get_text("text") or ""
                page_texts.append(text)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                page_lines.append(lines)
        return page_texts, page_lines

    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages
        if max_pages and max_pages > 0:
            pages = pages[:max_pages]
        for page in pages:
            text = page.extract_text() or ""
            page_texts.append(text)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            page_lines.append(lines)
    return page_texts, page_lines


def parse_manual_pdf(pdf_path: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """
    Parse a company manual PDF into structured sections.

    Returns:
        Dict with metadata and list of sections.
    """
    sections: List[Dict[str, Any]] = []
    headings_by_page: Dict[int, int] = {}

    page_texts, page_lines = _extract_page_texts(pdf_path, max_pages=max_pages)

    header_footer_lines = _collect_header_footer_lines(page_lines)
    current = None
    for page_num, lines in enumerate(page_lines, 1):
        filtered = [line for line in lines if line not in header_footer_lines]
        for line in filtered:
            heading = _match_heading(line)
            if heading:
                headings_by_page[page_num] = headings_by_page.get(page_num, 0) + 1
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
        "sections": sections,
        "parse_report": _build_parse_report(page_texts, sections, headings_by_page, header_footer_lines)
    }
