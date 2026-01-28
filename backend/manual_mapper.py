"""
Manual matching engine for MAP references.

Deterministically matches DCT questions to manual sections using
keyword overlap and CFR citations.
"""

import re
from typing import Any, Dict, List, Tuple

from models import Audit, Manual, ManualSection, Question
import database as db
import reference_context

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "when", "then",
    "shall", "should", "must", "may", "are", "was", "were", "have", "has", "had",
    "not", "but", "all", "any", "each", "such", "its", "their", "them", "his", "her",
    "these", "those", "about", "above", "below", "under", "over", "within", "without",
    "per", "performs", "perform", "ensure", "ensures", "ensure", "include", "includes"
}

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]{3,}")
MIN_SCORE = 2.0
MAX_SUGGESTIONS_PER_MANUAL = 4
PARAGRAPH_MARKER_PAREN_PATTERN = re.compile(r"(?<![A-Za-z0-9])\((?P<label>[a-z0-9]{1,3})\)\s+(?=[A-Z])")
PARAGRAPH_MARKER_LETTER_DOT = re.compile(r"(?<!\w)(?P<label>[a-z])\.\s+(?=[A-Z])")
PARAGRAPH_MARKER_LETTER_PAREN = re.compile(r"(?<!\w)(?P<label>[a-z])\)\s+(?=[A-Z])")
PARAGRAPH_MARKER_NUMBER_DOT = re.compile(r"(?<!\d)(?P<label>\d{1,2})\.\s+(?=[A-Z])")

GENERIC_SECTION_TITLES = {
    "general",
    "introduction",
    "overview",
    "purpose",
    "scope"
}

WEAK_TOKENS = {
    "equipment", "method", "procedures", "procedure", "program", "process",
    "resources", "capabilities", "appropriate", "ensure", "ensures"
}
WEAK_TOKEN_PENALTY = 3.0
WEAK_TOKEN_MIN_OVERLAP = 3

PROHIBITION_PATTERNS = [
    re.compile(r"\bdo\s+not\s+operate\b", re.IGNORECASE),
    re.compile(r"\bwill\s+not\s+operate\b", re.IGNORECASE),
    re.compile(r"\bmust\s+not\s+operate\b", re.IGNORECASE),
    re.compile(r"\bnot\s+operated\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+dispatch\b", re.IGNORECASE),
    re.compile(r"\bremove\s+from\s+service\b", re.IGNORECASE),
    re.compile(r"\bground(ed)?\b", re.IGNORECASE)
]

PROHIBITION_PHRASES = {
    "do not operate",
    "not operated",
    "not operate",
    "aircraft not operated",
    "not operate aircraft",
    "will not operate",
    "must not operate"
}

PHRASE_WEIGHTS = {
    "airworthiness directives": 3.0,
    "airworthiness directive": 3.0,
    "ad management": 3.0,
    "ad management process": 3.5,
    "ad process measurement": 2.5,
    "audit program": 2.5,
    "audit procedures": 2.0,
    "method of auditing": 2.5,
    "process measurement": 2.0,
    "compliance verification": 2.0,
    "continued compliance": 2.0,
    "quality assurance": 1.8,
    "compliance monitoring": 1.8,
    "internal audit": 1.8,
    "self audit": 1.6,
    "inspection program": 2.5,
    "inspection schedule": 2.0,
    "maintenance program": 2.5,
    "maintenance inspection": 2.0,
    "maintenance schedule": 2.0,
    "camp": 2.5,
    "continuous airworthiness maintenance program": 2.5,
    "task card": 1.5,
    "work package": 1.5,
    "records retention": 2.0,
    "record keeping": 2.0,
    "do not operate": 6.0,
    "not operated": 4.0,
    "not operate": 5.0,
    "aircraft not operated": 6.0,
    "not operate aircraft": 6.0,
    "will not operate": 6.0,
    "must not operate": 6.0
}

NOTE_NOISE_PATTERNS = [
    re.compile(r"UNCONTROLLED\s+COPY", re.IGNORECASE),
    re.compile(r"FOR\s+OFFICIAL\s+USE\s+ONLY", re.IGNORECASE),
    re.compile(r"Printed:\s*\d{1,2}/\d{1,2}/\d{4}", re.IGNORECASE),
    re.compile(r"Page\s+\d+\s+of\s+\d+", re.IGNORECASE)
]

SYNONYM_PHRASE_GROUPS = {
    "audit": [
        "audit program",
        "audit procedures",
        "process measurement",
        "compliance monitoring",
        "quality assurance",
        "internal audit",
        "self audit"
    ],
    "compliance": [
        "compliance verification",
        "continued compliance",
        "do not operate",
        "not operate",
        "not operated",
        "aircraft not operated",
        "not operate aircraft",
        "will not operate",
        "must not operate"
    ],
    "ad management": [
        "ad management process",
        "ad process measurement",
        "airworthiness directives management process",
        "airworthiness directive management process"
    ],
    "inspection program": [
        "inspection program",
        "inspection schedule",
        "maintenance inspection",
        "maintenance schedule"
    ],
    "maintenance program": [
        "maintenance program",
        "continuous airworthiness maintenance program",
        "camp",
        "task card",
        "work package",
        "aircraft inspection program",
        "aip"
    ],
    "records": [
        "record keeping",
        "records retention",
        "maintenance records"
    ],
    "aircraft records": [
        "aircraft records",
        "logbook",
        "log book",
        "record keeping",
        "records retention",
        "time since new",
        "time since overhaul",
        "aircraft maintenance log",
        "aml"
    ],
    "safety": [
        "safety management system",
        "sms",
        "safety risk management",
        "safety assurance",
        "safety policy",
        "safety promotion",
        "hazard reporting",
        "safety reporting",
        "risk assessment"
    ],
    "maintenance planning": [
        "maintenance planning",
        "maintenance plan",
        "planning",
        "scheduled maintenance",
        "maintenance schedule",
        "work scope",
        "planning interval",
        "forecasting"
    ],
    "moc": [
        "maintenance operations center",
        "moc",
        "control of maintenance",
        "maintenance control",
        "dispatch",
        "deferral",
        "mel",
        "cda"
    ],
    "aircraft records": [
        "aircraft records",
        "logbook",
        "log book",
        "record keeping",
        "records retention",
        "time since new",
        "time since overhaul"
    ]
}

TOPIC_TRIGGERS = {
    "ad management": [
        "ad management", "airworthiness directive", "airworthiness directives", "ad process", "ad compliance", "amoc"
    ],
    "inspection program": [
        "inspection program", "inspection schedule", "inspection requirements", "inspection intervals",
        "inspection time", "inspection task"
    ],
    "maintenance program": [
        "maintenance program", "camp", "continuous airworthiness maintenance program", "task card",
        "work package", "maintenance schedule", "aircraft inspection program", "aip"
    ],
    "records": [
        "record keeping", "records retention", "maintenance records", "records management"
    ],
    "audit": [
        "audit", "auditing", "audit program", "compliance monitoring", "quality assurance"
    ],
    "safety": [
        "safety", "sms", "safety management system", "safety risk management",
        "safety assurance", "safety policy", "safety promotion", "hazard reporting",
        "safety reporting", "risk assessment"
    ],
    "maintenance planning": [
        "maintenance planning", "maintenance plan", "scheduled maintenance",
        "maintenance schedule", "work scope", "planning interval", "forecasting"
    ],
    "moc": [
        "maintenance operations center", "moc", "maintenance control",
        "control of maintenance", "dispatch", "deferral", "mel", "cda"
    ],
    "aircraft records": [
        "aircraft records", "logbook", "log book", "record keeping",
        "records retention", "time since new", "time since overhaul",
        "aircraft maintenance log", "aml"
    ]
}

NORMALIZE_TOKEN_MAP = {
    "operated": "operate",
    "operating": "operate",
    "operation": "operate",
    "procedures": "procedure",
    "requirements": "requirement",
    "responsibilities": "responsibility"
}


def _tokenize(text: str) -> List[str]:
    tokens = [t.lower() for t in TOKEN_PATTERN.findall(text or "")]
    if re.search(r"\bAD\b", text or ""):
        tokens.append("ad")
    normalized = []
    for token in tokens:
        normalized.append(token)
        mapped = NORMALIZE_TOKEN_MAP.get(token)
        if mapped:
            normalized.append(mapped)
    return [t for t in normalized if t not in STOPWORDS]


def _clean_notes(notes: List[str]) -> str:
    if not notes:
        return ""
    cleaned = []
    for note in notes:
        if not note:
            continue
        if any(p.search(note) for p in NOTE_NOISE_PATTERNS):
            continue
        cleaned.append(note)
    return " ".join(cleaned)


def _split_section_into_segments(section: ManualSection) -> List[Dict[str, str]]:
    text = (section.section_text or "").strip()
    if not text:
        return []

    matches_map = {}
    for pattern in (
        PARAGRAPH_MARKER_PAREN_PATTERN,
        PARAGRAPH_MARKER_LETTER_DOT,
        PARAGRAPH_MARKER_LETTER_PAREN,
        PARAGRAPH_MARKER_NUMBER_DOT
    ):
        for match in pattern.finditer(text):
            start = match.start()
            label = match.group("label").lower()
            if start not in matches_map:
                matches_map[start] = label

    matches = [ (pos, label) for pos, label in matches_map.items() ]
    matches.sort(key=lambda item: item[0])
    if not matches:
        return [{"label": None, "text": text}]

    segments: List[Dict[str, str]] = []
    for idx, (start, label) in enumerate(matches):
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(text)
        segment_text = text[start:end].strip()
        if segment_text:
            segments.append({"label": label, "text": segment_text})

    # If the first marker isn't at the beginning, keep any preamble text.
    first_start = matches[0][0]
    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble and len(preamble.split()) >= 8:
            segments.insert(0, {"label": None, "text": preamble})

    return segments


def _expand_tokens(base_tokens: set, full_text: str) -> Tuple[set, List[str]]:
    expanded = set(base_tokens)
    phrases: List[str] = []
    text = (full_text or "").lower()

    if "ad management" in text or "airworthiness directives" in text:
        expanded.update({"management", "process", "audit", "auditing", "compliance"})
        phrases.extend(["ad management", "ad management process", "airworthiness directives"])

    if "audit" in text or "auditing" in text:
        expanded.update({"verification", "validation", "oversight"})
        phrases.extend(SYNONYM_PHRASE_GROUPS.get("audit", []))

    if "compliance" in text:
        expanded.update({"conformance", "verification"})
        phrases.extend(SYNONYM_PHRASE_GROUPS.get("compliance", []))

    return expanded, phrases


def _build_question_context(question: Question) -> Tuple[set, List[str]]:
    question_text = " ".join(filter(None, [
        question.question_text_condensed,
        question.question_text_full,
        question.data_collection_guidance
    ]))
    reference_texts = []
    if question.reference_raw:
        reference_texts.append(question.reference_raw)
    reference_texts.extend(question.reference_other_list or [])
    reference_texts.extend(question.reference_faa_guidance_list or [])
    notes_text = _clean_notes(question.notes or [])

    ref_context = reference_context.build_reference_context(reference_texts)
    ref_text_block = " ".join(ref_context.get("reference_titles", []))

    full_text = " ".join(filter(None, [
        question_text,
        " ".join(reference_texts),
        ref_text_block,
        notes_text
    ]))

    tokens = set(_tokenize(full_text))
    tokens.update(ref_context.get("keywords", []))
    tokens, extra_phrases = _expand_tokens(tokens, full_text)

    phrases = set(ref_context.get("phrases", []))
    for phrase in extra_phrases:
        phrases.add(phrase.lower())
    # If a topic is detected, expand only that topic's phrases (keeps mapping contextual).
    detected_topics = set()
    full_text_lower = full_text.lower()
    token_text = " ".join(sorted(tokens))
    for topic, triggers in TOPIC_TRIGGERS.items():
        for trigger in triggers:
            if trigger in full_text_lower or trigger in token_text:
                detected_topics.add(topic)
                break
    for topic in detected_topics:
        for phrase in SYNONYM_PHRASE_GROUPS.get(topic, []):
            phrases.add(phrase)
    # Always include compliance phrases if compliance is explicit.
    if "compliance" in tokens:
        for phrase in SYNONYM_PHRASE_GROUPS.get("compliance", []):
            phrases.add(phrase)
    for phrase in PHRASE_WEIGHTS.keys():
        if phrase in full_text.lower():
            phrases.add(phrase)

    return tokens, sorted(phrases)


def _question_has_prohibition_intent(tokens: set, full_text: str) -> bool:
    if any(p.search(full_text) for p in PROHIBITION_PATTERNS):
        return True
    # Also trigger if "operate" appears with a negation concept.
    if "operate" in tokens and ("not" in full_text.lower() or "no" in full_text.lower()):
        return True
    if "operate" in tokens and ("aircraft" in tokens or "dispatch" in tokens):
        return True
    return False


def _score_section_segment(question_tokens: set, question_cfrs: set, question_phrases: List[str],
                           section_title: str, segment_text: str,
                           section: ManualSection, allow_prohibition: bool = True) -> Tuple[float, Dict[str, Any]]:
    title_text = (section_title or "")
    section_tokens = set(_tokenize(title_text + " " + (segment_text or "")))

    cfr_matches = question_cfrs.intersection(set(section.cfr_citations or []))
    cfr_score = len(cfr_matches) * 5.0

    overlap = question_tokens.intersection(section_tokens)
    overlap_score = float(len(overlap))

    phrase_hits = []
    section_text_lower = (title_text + " " + (segment_text or "")).lower()
    title_lower = title_text.lower()
    phrase_score = 0.0
    for phrase in question_phrases:
        weight = PHRASE_WEIGHTS.get(phrase, 1.5)
        if phrase and phrase in section_text_lower:
            phrase_hits.append(phrase)
            phrase_score += weight
            if phrase in title_lower:
                phrase_score += 1.0

    prohibition_bonus = 0.0
    prohibition_hit = any(p.search(segment_text) for p in PROHIBITION_PATTERNS)
    if allow_prohibition and prohibition_hit:
        prohibition_bonus = 6.0
        phrase_hits.append("prohibit operation")
    # If the question doesn't imply prohibition, drop prohibition-only matches.
    if not allow_prohibition and prohibition_hit and not phrase_hits and len(overlap) < 3:
        return 0.0, {
            "cfr_matches": sorted(cfr_matches),
            "keyword_hits": sorted(list(overlap))[:10],
            "phrase_hits": ["prohibit operation (filtered)"]
        }

    score = cfr_score + overlap_score + phrase_score + prohibition_bonus
    if title_lower.strip() in GENERIC_SECTION_TITLES:
        score -= 2.0
    # Penalize matches that only hit vague/generic tokens.
    if overlap and overlap.issubset(WEAK_TOKENS) and len(overlap) <= WEAK_TOKEN_MIN_OVERLAP:
        score -= WEAK_TOKEN_PENALTY
    return score, {
        "cfr_matches": sorted(cfr_matches),
        "keyword_hits": sorted(list(overlap))[:10],
        "phrase_hits": sorted(set(phrase_hits))
    }


def _rank_sections(question: Question, sections: List[ManualSection]) -> List[Dict[str, Any]]:
    question_tokens, question_phrases = _build_question_context(question)
    full_text = " ".join(filter(None, [
        question.question_text_condensed,
        question.question_text_full,
        question.data_collection_guidance,
        question.reference_raw,
        " ".join(question.reference_other_list or []),
        " ".join(question.reference_faa_guidance_list or []),
        _clean_notes(question.notes or [])
    ])).lower()
    allow_prohibition = _question_has_prohibition_intent(question_tokens, full_text)
    if not allow_prohibition:
        question_phrases = [
            p for p in question_phrases
            if p not in PROHIBITION_PHRASES
        ]
    question_cfrs = set(question.reference_cfr_list or [])

    scored: List[Tuple[float, ManualSection, Dict[str, Any], str]] = []

    for section in sections:
        section_title = (section.section_title or "")
        segments = _split_section_into_segments(section)
        if not segments:
            continue
        for seg in segments:
            score, signals = _score_section_segment(
                question_tokens,
                question_cfrs,
                question_phrases,
                section_title,
                seg.get("text", ""),
                section,
                allow_prohibition=allow_prohibition
            )
            if score >= MIN_SCORE:
                scored.append((score, section, signals, seg.get("label")))

    if not scored:
        return []

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].page_number or 0,
            item[1].section_number or "",
            item[3] or "",
            item[1].section_title or ""
        )
    )

    suggestions: List[Dict[str, Any]] = []
    for score, section, signals, paragraph_label in scored[:MAX_SUGGESTIONS_PER_MANUAL]:
        section_number = section.section_number or ""
        section_display = section_number or section.section_title or ""
        if paragraph_label and section_number:
            section_display = f"{section_number}({paragraph_label})"
        suggestions.append({
            "manual_id": section.manual_id,
            "manual_type": section.manual.manual_type if section.manual else None,
            "section": section_display,
            "section_number": section.section_number,
            "section_title": section.section_title,
            "page_number": section.page_number,
            "paragraph": paragraph_label,
            "score": round(score, 2),
            "match_signals": signals,
            "source": "auto"
        })

    return suggestions


def load_latest_manual_sections(session, audit_id: str = None) -> Dict[str, List[ManualSection]]:
    """
    Load sections for the most recently uploaded manual of each type.

    If audit_id is provided, pin the manuals per type for that audit on first use
    to ensure repeatable mapping even after new manual uploads.
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

    pinned_ids: Dict[str, str] = {}
    if audit_id:
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if audit:
            pinned_ids = audit.pinned_manual_ids or {}
            if not pinned_ids:
                pinned_ids = {mtype: manual.id for mtype, manual in latest_by_type.items()}
                audit.pinned_manual_ids = pinned_ids
                session.add(audit)
                session.flush()

    sections_by_type: Dict[str, List[ManualSection]] = {}
    for manual_type, manual in latest_by_type.items():
        manual_id = pinned_ids.get(manual_type, manual.id) if pinned_ids else manual.id
        sections = (
            session.query(ManualSection)
            .filter(ManualSection.manual_id == manual_id)
            .order_by(ManualSection.page_number.asc())
            .all()
        )
        if sections:
            sections_by_type[manual_type] = sections

    return sections_by_type


def suggest_manual_links(question: Question,
                         sections_by_type: Dict[str, List[ManualSection]]) -> List[Dict[str, Any]]:
    """
    Suggest manual section links for a single question.
    """
    suggestions: List[Dict[str, Any]] = []
    for manual_type, sections in sections_by_type.items():
        ranked = _rank_sections(question, sections)
        if ranked:
            for suggestion in ranked:
                suggestion["manual_type"] = manual_type
                suggestions.append(suggestion)

    return suggestions


def suggest_manual_links_for_audit(audit_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Suggest manual links for all questions in an audit.
    """
    links: Dict[str, List[Dict[str, Any]]] = {}

    with db.get_session() as session:
        sections_by_type = load_latest_manual_sections(session, audit_id=audit_id)
        if not sections_by_type:
            return links

        questions = session.query(Question).filter(Question.audit_id == audit_id).all()
        for question in questions:
            suggestions = suggest_manual_links(question, sections_by_type)
            if suggestions:
                links[question.qid] = suggestions

    return links
