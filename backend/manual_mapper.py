"""
Manual matching engine for MAP references.

Deterministically matches DCT questions to manual sections using
keyword overlap and CFR citations.
"""

import re
from typing import Any, Dict, List, Tuple

import database as db
from models import Manual, ManualSection, Question

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "when", "then",
    "shall", "should", "must", "may", "are", "was", "were", "have", "has", "had",
    "not", "but", "all", "any", "each", "such", "its", "their", "them", "his", "her",
    "these", "those", "about", "above", "below", "under", "over", "within", "without",
    "per", "performs", "perform", "ensure", "ensures", "ensure", "include", "includes"
}

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]{3,}")


def _tokenize(text: str) -> List[str]:
    tokens = [t.lower() for t in TOKEN_PATTERN.findall(text or "")]
    return [t for t in tokens if t not in STOPWORDS]


def _score_section(question_tokens: set, question_cfrs: set,
                   section: ManualSection) -> Tuple[float, Dict[str, Any]]:
    section_text = (section.section_text or "")
    section_title = (section.section_title or "")
    section_tokens = set(_tokenize(section_title + " " + section_text))

    cfr_matches = question_cfrs.intersection(set(section.cfr_citations or []))
    cfr_score = len(cfr_matches) * 5.0

    overlap = question_tokens.intersection(section_tokens)
    overlap_score = float(len(overlap))

    score = cfr_score + overlap_score
    return score, {
        "cfr_matches": sorted(cfr_matches),
        "keyword_hits": sorted(list(overlap))[:10]
    }


def _select_best_section(question: Question, sections: List[ManualSection]) -> Dict[str, Any]:
    question_text = " ".join(filter(None, [
        question.question_text_condensed,
        question.question_text_full,
        question.data_collection_guidance
    ]))
    question_tokens = set(_tokenize(question_text))
    question_cfrs = set(question.reference_cfr_list or [])

    best = None
    best_score = 0.0
    best_signals = {}

    for section in sections:
        score, signals = _score_section(question_tokens, question_cfrs, section)
        if score > best_score:
            best_score = score
            best = section
            best_signals = signals

    if not best or best_score < 2.0:
        return {}

    return {
        "manual_id": best.manual_id,
        "manual_type": best.manual.manual_type if best.manual else None,
        "section": best.section_number or best.section_title or "",
        "section_number": best.section_number,
        "section_title": best.section_title,
        "page_number": best.page_number,
        "score": round(best_score, 2),
        "match_signals": best_signals,
        "source": "auto"
    }


def load_latest_manual_sections(session) -> Dict[str, List[ManualSection]]:
    """
    Load sections for the most recently uploaded manual of each type.
    """
    manuals = (
        session.query(Manual)
        .order_by(Manual.upload_date.desc())
        .all()
    )

    latest_by_type: Dict[str, Manual] = {}
    for manual in manuals:
        if manual.manual_type not in latest_by_type:
            latest_by_type[manual.manual_type] = manual

    sections_by_type: Dict[str, List[ManualSection]] = {}
    for manual_type, manual in latest_by_type.items():
        sections = (
            session.query(ManualSection)
            .filter(ManualSection.manual_id == manual.id)
            .order_by(ManualSection.page_number.asc())
            .all()
        )
        sections_by_type[manual_type] = sections

    return sections_by_type


def suggest_manual_links(question: Question,
                         sections_by_type: Dict[str, List[ManualSection]]) -> List[Dict[str, Any]]:
    """
    Suggest manual section links for a single question.
    """
    suggestions: List[Dict[str, Any]] = []
    for manual_type, sections in sections_by_type.items():
        best = _select_best_section(question, sections)
        if best:
            best["manual_type"] = manual_type
            suggestions.append(best)

    return suggestions


def suggest_manual_links_for_audit(audit_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Suggest manual links for all questions in an audit.
    """
    links: Dict[str, List[Dict[str, Any]]] = {}

    with db.get_session() as session:
        sections_by_type = load_latest_manual_sections(session)
        if not sections_by_type:
            return links

        questions = session.query(Question).filter(Question.audit_id == audit_id).all()
        for question in questions:
            suggestions = suggest_manual_links(question, sections_by_type)
            if suggestions:
                links[question.qid] = suggestions

    return links
