"""
Applicability heuristics for DCT questions.

Conservative rules to auto-flag questions as not applicable when text
explicitly indicates non-applicability.
"""

import re
from typing import Optional, Tuple

NOT_APPLICABLE_PATTERNS = [
    re.compile(r'\bnot\s+applicable\b', re.IGNORECASE),
    re.compile(r'\bN/?A\b', re.IGNORECASE),
    re.compile(r'\bdoes\s+not\s+apply\b', re.IGNORECASE),
    re.compile(r'\bnot\s+required\b', re.IGNORECASE),
    re.compile(r'\bnot\s+used\b', re.IGNORECASE),
]


def detect_applicability(text: str) -> Optional[Tuple[bool, str]]:
    """
    Detect applicability from text.

    Returns:
        (is_applicable, reason) or None if no determination can be made.
    """
    if not text:
        return None

    for pattern in NOT_APPLICABLE_PATTERNS:
        if pattern.search(text):
            return False, "Detected 'not applicable' language in question text"

    return None
