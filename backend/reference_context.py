"""
Reference context enrichment for DCT questions.

Builds deterministic keyword/phrase context from reference strings such as
AC-39-9 and FAA Order 8900.1 citations.
"""

import re
from typing import Dict, List, Set, Tuple

REFERENCE_CATALOG: Dict[str, Dict[str, List[str]]] = {
    "AC-39-9": {
        "title": "Airworthiness Directives Management Process",
        "keywords": [
            "airworthiness", "directive", "directives", "ad", "management",
            "process", "audit", "auditing", "compliance", "verification",
            "validation", "planning", "support", "provisioning", "implementing",
            "recording", "resources", "capabilities", "equipment", "size"
        ],
        "phrases": [
            "airworthiness directives management process",
            "ad management process",
            "continued ad compliance",
            "method of auditing",
            "ad compliance"
        ]
    },
    "FAA ORDER 8900.1 VOL 3 CH 59 SEC 1": {
        "title": "",
        "keywords": [
            "airworthiness", "directive", "directives", "ad", "management",
            "process", "evaluate", "evaluation", "audit", "auditing",
            "compliance", "verification", "oversight"
        ],
        "phrases": [
            "ad management process"
        ]
    },
    "FAA ORDER 8900.1 VOL 3 CH 59 SEC 3": {
        "title": "",
        "keywords": [
            "amoc", "alternative", "method", "compliance", "airworthiness",
            "directive", "directives", "ad", "processing", "proposal", "approval"
        ],
        "phrases": [
            "alternative method of compliance",
            "amoc"
        ]
    }
}


REFERENCE_ALIASES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bAC\s*[- ]?39-9\b", re.IGNORECASE), "AC-39-9"),
    (
        re.compile(
            r"\b(FAA\s*)?Order\s*8900\.1\b.*\bVol(?:ume)?\s*3\b.*\bCh(?:apter)?\s*59\b.*\bSec(?:tion)?\s*1\b",
            re.IGNORECASE
        ),
        "FAA ORDER 8900.1 VOL 3 CH 59 SEC 1"
    ),
    (
        re.compile(
            r"\b8900\.1\b.*\bVol(?:ume)?\s*3\b.*\bCh(?:apter)?\s*59\b.*\bSec(?:tion)?\s*1\b",
            re.IGNORECASE
        ),
        "FAA ORDER 8900.1 VOL 3 CH 59 SEC 1"
    ),
    (
        re.compile(
            r"\b(FAA\s*)?Order\s*8900\.1\b.*\bVol(?:ume)?\s*3\b.*\bCh(?:apter)?\s*59\b.*\bSec(?:tion)?\s*3\b",
            re.IGNORECASE
        ),
        "FAA ORDER 8900.1 VOL 3 CH 59 SEC 3"
    ),
    (
        re.compile(
            r"\b8900\.1\b.*\bVol(?:ume)?\s*3\b.*\bCh(?:apter)?\s*59\b.*\bSec(?:tion)?\s*3\b",
            re.IGNORECASE
        ),
        "FAA ORDER 8900.1 VOL 3 CH 59 SEC 3"
    ),
]


def extract_reference_keys(reference_texts: List[str]) -> Set[str]:
    keys: Set[str] = set()
    for text in reference_texts:
        if not text:
            continue
        for pattern, key in REFERENCE_ALIASES:
            if pattern.search(text):
                keys.add(key)
    return keys


def build_reference_context(reference_texts: List[str]) -> Dict[str, List[str]]:
    keys = extract_reference_keys(reference_texts)
    keywords: Set[str] = set()
    phrases: Set[str] = set()
    titles: List[str] = []

    for key in sorted(keys):
        entry = REFERENCE_CATALOG.get(key, {})
        title = entry.get("title")
        if title:
            titles.append(title)
            phrases.add(title.lower())
        for kw in entry.get("keywords", []):
            keywords.add(kw.lower())
        for phrase in entry.get("phrases", []):
            phrases.add(phrase.lower())

    return {
        "reference_keys": sorted(keys),
        "reference_titles": titles,
        "keywords": sorted(keywords),
        "phrases": sorted(phrases)
    }
