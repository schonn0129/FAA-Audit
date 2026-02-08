"""
Manual matching engine for MAP references.

Matches DCT questions to manual sections using:
1. Deterministic keyword overlap and CFR citations
2. Optional semantic similarity via embeddings (sentence-transformers)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from models import Audit, Manual, ManualSection, Question
import database as db
import reference_context
from config import EMBEDDING_ENABLED, EMBEDDING_MODEL, SEMANTIC_WEIGHT

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import numpy as np

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
    # AD Management - high weights for specific AD terms
    "airworthiness directives": 5.0,
    "airworthiness directive": 5.0,
    "ad management": 5.0,
    "ad management process": 6.0,
    "ad compliance": 5.0,
    "ad tracking": 4.0,
    "ad status": 4.0,
    "ad applicability": 4.0,
    "recurring ad": 4.5,
    "one-time ad": 4.5,
    "terminating action": 4.0,
    "amoc": 4.0,
    "alternative method of compliance": 4.0,
    "ad process measurement": 3.5,
    # Audit/compliance
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
    # Inspection program
    "inspection program": 2.5,
    "inspection schedule": 2.0,
    # Maintenance program
    "maintenance program": 2.5,
    "maintenance inspection": 2.0,
    "maintenance schedule": 2.0,
    "camp": 2.5,
    "continuous airworthiness maintenance program": 2.5,
    "task card": 1.5,
    "work package": 1.5,
    # Records
    "records retention": 2.0,
    "record keeping": 2.0,
    # Prohibition phrases
    "do not operate": 6.0,
    "not operated": 4.0,
    "not operate": 5.0,
    "aircraft not operated": 6.0,
    "not operate aircraft": 6.0,
    "will not operate": 6.0,
    "must not operate": 6.0
}

# Title bonus: boost score when section title contains key topic terms
TITLE_TOPIC_BONUS = {
    "ad management": ["airworthiness directive", "airworthiness directives", "ad management", "ad compliance"],
    "mel": ["minimum equipment list", "mel", "deferred"],
    "inspection program": ["inspection program", "inspection schedule"],
    "maintenance program": ["maintenance program", "camp"],
}
TITLE_BONUS_SCORE = 4.0

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
    ],
    "mel": [
        "minimum equipment list", "mel", "mmel", "deferred", "deferral",
        "inoperative equipment", "configuration deviation"
    ],
    "transponder": [
        "transponder", "ads-b", "adsb", "mode s", "mode c", "squawk",
        "altitude encoder", "atc transponder"
    ]
}

# Topic exclusions: when question is about topic X, penalize sections about topic Y
# Format: { question_topic: [excluded_section_topics] }
TOPIC_EXCLUSIONS = {
    "ad management": ["mel", "transponder", "moc"],
    "mel": ["ad management"],
    "transponder": ["ad management"],
    "inspection program": ["mel", "transponder"],
    "maintenance program": ["transponder"],
}

# Penalty applied when a section matches an excluded topic
TOPIC_EXCLUSION_PENALTY = 8.0

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


def _detect_question_topics(tokens: set, full_text: str) -> List[str]:
    """
    Detect which topics a question is primarily about.
    Returns a list of detected topic names.
    """
    detected: List[str] = []
    text_lower = full_text.lower()
    token_text = " ".join(sorted(tokens))

    for topic, triggers in TOPIC_TRIGGERS.items():
        for trigger in triggers:
            if trigger in text_lower or trigger in token_text:
                detected.append(topic)
                break

    return detected


def _section_matches_excluded_topic(section_text: str, section_title: str,
                                     question_topics: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if a section matches a topic that should be excluded for the question's topics.

    Returns:
        (is_excluded, list of matched exclusion topics)
    """
    if not question_topics:
        return False, []

    combined_text = (section_title + " " + section_text).lower()
    matched_exclusions: List[str] = []

    for q_topic in question_topics:
        excluded_topics = TOPIC_EXCLUSIONS.get(q_topic, [])
        for excluded_topic in excluded_topics:
            triggers = TOPIC_TRIGGERS.get(excluded_topic, [])
            for trigger in triggers:
                if trigger in combined_text:
                    matched_exclusions.append(excluded_topic)
                    break

    return len(matched_exclusions) > 0, list(set(matched_exclusions))


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
                           section: ManualSection, allow_prohibition: bool = True,
                           question_topics: List[str] = None) -> Tuple[float, Dict[str, Any]]:
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

    # Apply title bonus when section title matches question topic
    title_bonus = 0.0
    title_bonus_reason = None
    if question_topics:
        for q_topic in question_topics:
            bonus_terms = TITLE_TOPIC_BONUS.get(q_topic, [])
            for term in bonus_terms:
                if term in title_lower:
                    title_bonus = TITLE_BONUS_SCORE
                    title_bonus_reason = f"title contains '{term}'"
                    break
            if title_bonus > 0:
                break

    score = cfr_score + overlap_score + phrase_score + prohibition_bonus + title_bonus
    if title_lower.strip() in GENERIC_SECTION_TITLES:
        score -= 2.0
    # Penalize matches that only hit vague/generic tokens.
    if overlap and overlap.issubset(WEAK_TOKENS) and len(overlap) <= WEAK_TOKEN_MIN_OVERLAP:
        score -= WEAK_TOKEN_PENALTY

    signals = {
        "cfr_matches": sorted(cfr_matches),
        "keyword_hits": sorted(list(overlap))[:10],
        "phrase_hits": sorted(set(phrase_hits))
    }
    if title_bonus_reason:
        signals["title_bonus"] = title_bonus_reason

    return score, signals


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

    # Detect question topics for exclusion filtering
    question_topics = _detect_question_topics(question_tokens, full_text)

    scored: List[Tuple[float, ManualSection, Dict[str, Any], str, List[str]]] = []

    for section in sections:
        section_title = (section.section_title or "")
        section_text = (section.section_text or "")
        segments = _split_section_into_segments(section)
        if not segments:
            continue

        # Check if this section matches an excluded topic
        is_excluded, excluded_topics = _section_matches_excluded_topic(
            section_text, section_title, question_topics
        )

        for seg in segments:
            score, signals = _score_section_segment(
                question_tokens,
                question_cfrs,
                question_phrases,
                section_title,
                seg.get("text", ""),
                section,
                allow_prohibition=allow_prohibition,
                question_topics=question_topics
            )

            # Apply topic exclusion penalty
            if is_excluded:
                score -= TOPIC_EXCLUSION_PENALTY
                signals["excluded_topics"] = excluded_topics

            if score >= MIN_SCORE:
                scored.append((score, section, signals, seg.get("label"), excluded_topics))

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
    for score, section, signals, paragraph_label, excluded_topics in scored[:MAX_SUGGESTIONS_PER_MANUAL]:
        section_number = section.section_number or ""
        section_display = section_number or section.section_title or ""
        if paragraph_label and section_number:
            section_display = f"{section_number}({paragraph_label})"
        suggestion = {
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
        }
        if excluded_topics:
            suggestion["excluded_topics"] = excluded_topics
        suggestions.append(suggestion)

    return suggestions


def load_latest_manual_sections(session, audit_id: str = None) -> Dict[str, List[ManualSection]]:
    """
    Load sections for the most recently uploaded manual of each type.

    If audit_id is provided, pin the manuals per type for that audit on first use
    to ensure repeatable mapping even after new manual uploads.
    """
    logger.debug(f"Loading manual sections for audit_id={audit_id}")

    try:
        manuals = (
            session.query(Manual)
            .order_by(Manual.upload_date.desc())
            .all()
        )
        logger.debug(f"Found {len(manuals)} manuals in database")
    except Exception as e:
        logger.error(f"Failed to query manuals: {e}", exc_info=True)
        raise

    latest_by_type: Dict[str, Manual] = {}
    for manual in manuals:
        if manual.manual_type not in latest_by_type:
            latest_by_type[manual.manual_type] = manual

    logger.debug(f"Latest manuals by type: {list(latest_by_type.keys())}")

    pinned_ids: Dict[str, str] = {}
    if audit_id:
        try:
            audit = session.query(Audit).filter(Audit.id == audit_id).first()
            if audit:
                pinned_ids = audit.pinned_manual_ids or {}
                logger.debug(f"Existing pinned_manual_ids: {pinned_ids}")
                if not pinned_ids and latest_by_type:
                    pinned_ids = {mtype: manual.id for mtype, manual in latest_by_type.items()}
                    logger.info(f"Pinning manuals for audit {audit_id}: {pinned_ids}")
                    audit.pinned_manual_ids = pinned_ids
                    session.add(audit)
                    session.flush()
            else:
                logger.warning(f"Audit {audit_id} not found when loading manual sections")
        except Exception as e:
            logger.error(f"Failed to pin manual IDs for audit {audit_id}: {e}", exc_info=True)
            raise

    sections_by_type: Dict[str, List[ManualSection]] = {}
    for manual_type, manual in latest_by_type.items():
        manual_id = pinned_ids.get(manual_type, manual.id) if pinned_ids else manual.id
        try:
            sections = (
                session.query(ManualSection)
                .filter(ManualSection.manual_id == manual_id)
                .order_by(ManualSection.page_number.asc())
                .all()
            )
            if sections:
                sections_by_type[manual_type] = sections
                logger.debug(f"Loaded {len(sections)} sections for {manual_type}")
        except Exception as e:
            logger.error(f"Failed to load sections for manual {manual_id}: {e}", exc_info=True)
            raise

    logger.info(f"Loaded sections for manual types: {list(sections_by_type.keys())}")
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


# =============================================================================
# SEMANTIC MATCHING (Enhanced with Embeddings)
# =============================================================================

def _get_embedding_service():
    """Lazy-load the embedding service to avoid startup delay."""
    try:
        from embedding_service import get_embedding_service
        return get_embedding_service(EMBEDDING_MODEL)
    except Exception as e:
        logger.warning(
            f"Embeddings unavailable; semantic matching disabled. Reason: {e}",
            exc_info=True,
        )
        return None


def _compute_question_embedding(question: Question, embedding_service) -> Optional[np.ndarray]:
    """Compute or retrieve cached embedding for a question."""
    from embedding_service import build_question_intent_text, bytes_to_embedding, embedding_to_bytes

    # Check cache
    if question.intent_embedding and question.intent_embedding_model == EMBEDDING_MODEL:
        return bytes_to_embedding(question.intent_embedding)

    # Compute embedding
    intent_text = build_question_intent_text(question)
    embedding = embedding_service.embed_text(intent_text)

    # Cache for later (don't commit here - caller should handle transaction)
    question.intent_embedding = embedding_to_bytes(embedding)
    question.intent_embedding_model = EMBEDDING_MODEL

    return embedding


def _compute_section_embedding(section: ManualSection, embedding_service) -> Optional[np.ndarray]:
    """Compute or retrieve cached embedding for a manual section."""
    from embedding_service import build_section_content_text, bytes_to_embedding, embedding_to_bytes

    # Check cache
    if section.content_embedding and section.content_embedding_model == EMBEDDING_MODEL:
        return bytes_to_embedding(section.content_embedding)

    # Compute embedding
    content_text = build_section_content_text(section)
    embedding = embedding_service.embed_text(content_text)

    # Cache for later
    section.content_embedding = embedding_to_bytes(embedding)
    section.content_embedding_model = EMBEDDING_MODEL

    return embedding


def suggest_manual_links_enhanced(
    question: Question,
    sections_by_type: Dict[str, List[ManualSection]],
    use_semantic: bool = True,
    semantic_weight: float = None
) -> List[Dict[str, Any]]:
    """
    Enhanced suggestion with optional semantic matching.

    Combines deterministic scoring with semantic similarity:
    - deterministic_score: keyword/CFR/phrase matching (existing)
    - semantic_score: embedding similarity (0-1) scaled

    Args:
        question: The question to find matches for
        sections_by_type: Manual sections grouped by type
        use_semantic: Whether to use semantic matching (default True if available)
        semantic_weight: Weight for semantic score (0-1), default from config

    Returns:
        List of suggestion dictionaries with combined scores
    """
    if semantic_weight is None:
        semantic_weight = SEMANTIC_WEIGHT

    # Check if semantic matching is available and enabled
    embedding_service = None
    if use_semantic and EMBEDDING_ENABLED:
        embedding_service = _get_embedding_service()

    if embedding_service is None:
        # Fall back to deterministic only
        return suggest_manual_links(question, sections_by_type)

    # Get question embedding
    try:
        question_embedding = _compute_question_embedding(question, embedding_service)
    except Exception as e:
        logger.error(f"Failed to compute question embedding: {e}")
        return suggest_manual_links(question, sections_by_type)

    # Build question context for deterministic scoring
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
        question_phrases = [p for p in question_phrases if p not in PROHIBITION_PHRASES]
    question_cfrs = set(question.reference_cfr_list or [])

    # Detect question topics for exclusion filtering
    question_topics = _detect_question_topics(question_tokens, full_text)

    # Score all sections
    all_scored: List[Dict[str, Any]] = []

    for manual_type, sections in sections_by_type.items():
        for section in sections:
            section_title = section.section_title or ""
            section_text = section.section_text or ""
            segments = _split_section_into_segments(section)

            if not segments:
                continue

            # Check if this section matches an excluded topic
            is_excluded, excluded_topics = _section_matches_excluded_topic(
                section_text, section_title, question_topics
            )

            # Compute section embedding (once per section, not per segment)
            try:
                section_embedding = _compute_section_embedding(section, embedding_service)
                semantic_similarity = embedding_service.similarity(question_embedding, section_embedding)
            except Exception as e:
                logger.warning(f"Failed to compute section embedding: {e}")
                semantic_similarity = 0.0

            for seg in segments:
                # Deterministic score
                det_score, signals = _score_section_segment(
                    question_tokens,
                    question_cfrs,
                    question_phrases,
                    section_title,
                    seg.get("text", ""),
                    section,
                    allow_prohibition=allow_prohibition,
                    question_topics=question_topics
                )

                # Apply topic exclusion penalty
                if is_excluded:
                    det_score -= TOPIC_EXCLUSION_PENALTY
                    signals["excluded_topics"] = excluded_topics

                # Skip very low deterministic scores unless semantic is high
                if det_score < 1.0 and semantic_similarity < 0.3:
                    continue

                # Combined scoring
                # Scale semantic similarity to match deterministic range (roughly 0-20)
                semantic_score = semantic_similarity * 10.0

                # Weighted combination
                det_weight = 1.0 - semantic_weight
                final_score = (det_score * det_weight) + (semantic_score * semantic_weight)

                # Build section display
                section_number = section.section_number or ""
                section_display = section_number or section.section_title or ""
                paragraph_label = seg.get("label")
                if paragraph_label and section_number:
                    section_display = f"{section_number}({paragraph_label})"

                all_scored.append({
                    "manual_id": section.manual_id,
                    "manual_type": manual_type,
                    "section": section_display,
                    "section_number": section.section_number,
                    "section_title": section.section_title,
                    "page_number": section.page_number,
                    "paragraph": paragraph_label,
                    "score": round(final_score, 2),
                    "deterministic_score": round(det_score, 2),
                    "semantic_score": round(semantic_score, 2),
                    "semantic_similarity": round(semantic_similarity, 3),
                    "match_signals": signals,
                    "source": "auto"
                })

    if not all_scored:
        return []

    # Sort by final score
    all_scored.sort(key=lambda x: (-x["score"], x.get("page_number") or 0))

    # Limit to top N per manual type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for item in all_scored:
        mtype = item["manual_type"]
        if mtype not in by_type:
            by_type[mtype] = []
        if len(by_type[mtype]) < MAX_SUGGESTIONS_PER_MANUAL:
            by_type[mtype].append(item)

    # Flatten back to list
    suggestions = []
    for items in by_type.values():
        suggestions.extend(items)

    # Final sort
    suggestions.sort(key=lambda x: (-x["score"], x.get("page_number") or 0))

    return suggestions


def suggest_manual_links_for_audit_enhanced(
    audit_id: str,
    use_semantic: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Suggest manual links for all questions in an audit with semantic matching.
    """
    links: Dict[str, List[Dict[str, Any]]] = {}

    with db.get_session() as session:
        sections_by_type = load_latest_manual_sections(session, audit_id=audit_id)
        if not sections_by_type:
            return links

        questions = session.query(Question).filter(Question.audit_id == audit_id).all()

        for question in questions:
            if use_semantic and EMBEDDING_ENABLED:
                suggestions = suggest_manual_links_enhanced(question, sections_by_type)
            else:
                suggestions = suggest_manual_links(question, sections_by_type)

            if suggestions:
                links[question.qid] = suggestions

        # Commit any cached embeddings
        session.commit()

    return links


def generate_embeddings_for_audit(audit_id: str) -> Dict[str, int]:
    """
    Pre-generate embeddings for all questions in an audit and their linked manuals.

    Args:
        audit_id: The audit ID

    Returns:
        Dictionary with counts of embeddings generated
    """
    from embedding_service import (
        build_question_intent_text, build_section_content_text,
        embedding_to_bytes, get_embedding_service
    )

    if not EMBEDDING_ENABLED:
        return {"error": "Embedding is disabled in configuration"}

    embedding_service = get_embedding_service(EMBEDDING_MODEL)

    questions_embedded = 0
    sections_embedded = 0

    with db.get_session() as session:
        # Generate question embeddings
        questions = session.query(Question).filter(Question.audit_id == audit_id).all()

        for question in questions:
            if question.intent_embedding and question.intent_embedding_model == EMBEDDING_MODEL:
                continue  # Already has embedding

            intent_text = build_question_intent_text(question)
            embedding = embedding_service.embed_text(intent_text)
            question.intent_embedding = embedding_to_bytes(embedding)
            question.intent_embedding_model = EMBEDDING_MODEL
            questions_embedded += 1

        # Generate section embeddings for pinned manuals
        sections_by_type = load_latest_manual_sections(session, audit_id=audit_id)

        for manual_type, sections in sections_by_type.items():
            for section in sections:
                if section.content_embedding and section.content_embedding_model == EMBEDDING_MODEL:
                    continue  # Already has embedding

                content_text = build_section_content_text(section)
                embedding = embedding_service.embed_text(content_text)
                section.content_embedding = embedding_to_bytes(embedding)
                section.content_embedding_model = EMBEDDING_MODEL
                sections_embedded += 1

        session.commit()

    return {
        "questions_embedded": questions_embedded,
        "sections_embedded": sections_embedded,
        "model": EMBEDDING_MODEL
    }
