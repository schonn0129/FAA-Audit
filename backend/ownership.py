"""
Ownership Assignment Engine for FAA DCT Questions.

This module implements a deterministic, rules-based decision tree to assign
each QID to one of the 7 authorized functions. Every decision is traceable,
repeatable, and defensible under PMI scrutiny.

The 7 Authorized Functions:
1. Maintenance Planning (MP)
2. Maintenance Operations Center (MOC)
3. Director of Maintenance (DOM)
4. Aircraft Records
5. Quality
6. Training
7. Safety
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Function(Enum):
    """The 7 authorized ownership functions."""
    MP = "Maintenance Planning"
    MOC = "Maintenance Operations Center"
    DOM = "Director of Maintenance"
    RECORDS = "Aircraft Records"
    QUALITY = "Quality"
    TRAINING = "Training"
    SAFETY = "Safety"


class Confidence(Enum):
    """Confidence levels for assignments."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class Signal:
    """Represents a signal that contributed to an ownership decision."""
    signal_type: str  # "keyword", "cfr", "manual"
    pattern: str
    matched_text: str
    target_function: str
    weight: float = 1.0


@dataclass
class OwnershipDecision:
    """Result of ownership assignment for a single question."""
    qid: str
    primary_function: str
    supporting_functions: List[str] = field(default_factory=list)
    confidence_score: str = "Low"
    confidence_value: float = 0.0
    rationale: str = ""
    keyword_matches: List[Dict[str, Any]] = field(default_factory=list)
    cfr_matches: List[Dict[str, Any]] = field(default_factory=list)
    manual_section_links: List[Dict[str, Any]] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)


# =============================================================================
# KEYWORD RULES
# =============================================================================

KEYWORD_RULES: Dict[str, List[Dict[str, Any]]] = {
    Function.MP.value: [
        {"pattern": r"\bprogram\b", "weight": 1.5, "description": "Program management"},
        {"pattern": r"\btask\s*card", "weight": 2.0, "description": "Task card development"},
        {"pattern": r"\bmaintenance\s+program", "weight": 2.0, "description": "Maintenance program"},
        {"pattern": r"\bscheduled\s+maintenance", "weight": 1.8, "description": "Scheduled maintenance"},
        {"pattern": r"\binterval", "weight": 1.2, "description": "Maintenance intervals"},
        {"pattern": r"\bCMP\b", "weight": 2.0, "description": "Continuous Maintenance Program"},
        {"pattern": r"\bCAMP\b", "weight": 2.0, "description": "Continuous Airworthiness Maintenance Program"},
        {"pattern": r"\bplanning", "weight": 1.0, "description": "Planning activities"},
        {"pattern": r"\bworkscope", "weight": 1.5, "description": "Work scope definition"},
        {"pattern": r"\bwork\s*package", "weight": 1.5, "description": "Work package development"},
        {"pattern": r"\bAD\s+compliance", "weight": 1.5, "description": "Airworthiness Directive compliance"},
        {"pattern": r"\bairworthiness\s+directive", "weight": 1.5, "description": "Airworthiness Directives"},
        {"pattern": r"\bSB\s+evaluation", "weight": 1.2, "description": "Service Bulletin evaluation"},
        {"pattern": r"\bservice\s+bulletin", "weight": 1.0, "description": "Service Bulletins"},
        {"pattern": r"\breliability\s+program", "weight": 1.5, "description": "Reliability program"},
    ],
    Function.MOC.value: [
        {"pattern": r"\bcontrol\b", "weight": 1.2, "description": "Control activities"},
        {"pattern": r"\bdispatch", "weight": 2.0, "description": "Dispatch operations"},
        {"pattern": r"\bMEL\b", "weight": 2.0, "description": "Minimum Equipment List"},
        {"pattern": r"\bminimum\s+equipment\s+list", "weight": 2.0, "description": "MEL management"},
        {"pattern": r"\bCDL\b", "weight": 1.8, "description": "Configuration Deviation List"},
        {"pattern": r"\bNEF\b", "weight": 1.5, "description": "Non-Essential Furnishings"},
        {"pattern": r"\bdefer", "weight": 1.5, "description": "Deferral management"},
        {"pattern": r"\boperations\s+center", "weight": 2.0, "description": "Operations center"},
        {"pattern": r"\brelease\s+to\s+service", "weight": 1.5, "description": "Release to service"},
        {"pattern": r"\baircraft\s+status", "weight": 1.2, "description": "Aircraft status monitoring"},
        {"pattern": r"\bscheduling", "weight": 1.0, "description": "Scheduling activities"},
        {"pattern": r"\bcoordination", "weight": 0.8, "description": "Coordination activities"},
    ],
    Function.DOM.value: [
        {"pattern": r"\bdirector", "weight": 1.5, "description": "Director responsibilities"},
        {"pattern": r"\bmanagement\s+responsibility", "weight": 2.0, "description": "Management responsibility"},
        {"pattern": r"\borganization", "weight": 1.0, "description": "Organization structure"},
        {"pattern": r"\bpolicy", "weight": 1.2, "description": "Policy development"},
        {"pattern": r"\bauthority", "weight": 1.2, "description": "Authority delegation"},
        {"pattern": r"\bapproval", "weight": 1.0, "description": "Approval authority"},
        {"pattern": r"\boversight", "weight": 1.5, "description": "Oversight responsibility"},
        {"pattern": r"\baccountable", "weight": 1.5, "description": "Accountability"},
        {"pattern": r"\bduties\s+and\s+responsibilities", "weight": 2.0, "description": "Duties and responsibilities"},
        {"pattern": r"\bmanagement\s+personnel", "weight": 1.5, "description": "Management personnel"},
    ],
    Function.RECORDS.value: [
        {"pattern": r"\brecord", "weight": 1.5, "description": "Record keeping"},
        {"pattern": r"\bdocument", "weight": 1.0, "description": "Documentation"},
        {"pattern": r"\blog\s*book", "weight": 2.0, "description": "Logbook management"},
        {"pattern": r"\baircraft\s+log", "weight": 2.0, "description": "Aircraft logs"},
        {"pattern": r"\bhistorical\s+record", "weight": 2.0, "description": "Historical records"},
        {"pattern": r"\bretention", "weight": 1.5, "description": "Record retention"},
        {"pattern": r"\btraceability", "weight": 1.5, "description": "Traceability"},
        {"pattern": r"\bpart\s+8110", "weight": 1.5, "description": "Part approval records"},
        {"pattern": r"\b8130", "weight": 1.8, "description": "FAA Form 8130"},
        {"pattern": r"\btime\s+in\s+service", "weight": 1.5, "description": "Time tracking"},
        {"pattern": r"\bcycle", "weight": 1.0, "description": "Cycle tracking"},
        {"pattern": r"\bserial\s+number", "weight": 1.2, "description": "Serial number tracking"},
        {"pattern": r"\blife\s+limit", "weight": 1.5, "description": "Life-limited parts"},
    ],
    Function.QUALITY.value: [
        {"pattern": r"\bquality", "weight": 2.0, "description": "Quality assurance"},
        {"pattern": r"\baudit", "weight": 1.8, "description": "Audit activities"},
        {"pattern": r"\binspection\s+program", "weight": 1.5, "description": "Inspection program"},
        {"pattern": r"\brequired\s+inspection", "weight": 2.0, "description": "Required Inspection Items"},
        {"pattern": r"\bRII\b", "weight": 2.5, "description": "Required Inspection Items"},
        {"pattern": r"\bcompliance\s+monitoring", "weight": 1.5, "description": "Compliance monitoring"},
        {"pattern": r"\bcontinuous\s+analysis", "weight": 1.5, "description": "Continuous analysis"},
        {"pattern": r"\bsurveillance", "weight": 1.5, "description": "Surveillance activities"},
        {"pattern": r"\bfinding", "weight": 1.2, "description": "Audit findings"},
        {"pattern": r"\bcorrective\s+action", "weight": 1.5, "description": "Corrective actions"},
        {"pattern": r"\broot\s+cause", "weight": 1.2, "description": "Root cause analysis"},
        {"pattern": r"\bnonconformance", "weight": 1.5, "description": "Nonconformance"},
        {"pattern": r"\bverif", "weight": 1.0, "description": "Verification"},
    ],
    Function.TRAINING.value: [
        {"pattern": r"\btraining", "weight": 2.0, "description": "Training programs"},
        {"pattern": r"\bqualification", "weight": 1.8, "description": "Qualification requirements"},
        {"pattern": r"\bauthoriz", "weight": 1.2, "description": "Authorization"},
        {"pattern": r"\bcertificat", "weight": 1.0, "description": "Certification"},
        {"pattern": r"\bcompetenc", "weight": 1.5, "description": "Competency"},
        {"pattern": r"\bcurriculum", "weight": 2.0, "description": "Training curriculum"},
        {"pattern": r"\binitial\s+training", "weight": 2.0, "description": "Initial training"},
        {"pattern": r"\brecurrent\s+training", "weight": 2.0, "description": "Recurrent training"},
        {"pattern": r"\bOJT\b", "weight": 2.0, "description": "On-the-job training"},
        {"pattern": r"\bon[\s-]*the[\s-]*job", "weight": 1.8, "description": "On-the-job training"},
        {"pattern": r"\bpersonnel\s+requirement", "weight": 1.2, "description": "Personnel requirements"},
    ],
    Function.SAFETY.value: [
        {"pattern": r"\bsafety\s+management", "weight": 2.5, "description": "Safety Management System"},
        {"pattern": r"\bSMS\b", "weight": 2.5, "description": "SMS"},
        {"pattern": r"\bhazard", "weight": 2.0, "description": "Hazard identification"},
        {"pattern": r"\brisk\s+assessment", "weight": 2.0, "description": "Risk assessment"},
        {"pattern": r"\brisk\s+management", "weight": 2.0, "description": "Risk management"},
        {"pattern": r"\bsafety\s+policy", "weight": 2.0, "description": "Safety policy"},
        {"pattern": r"\bsafety\s+objective", "weight": 1.8, "description": "Safety objectives"},
        {"pattern": r"\bsafety\s+assurance", "weight": 2.0, "description": "Safety assurance"},
        {"pattern": r"\bsafety\s+promotion", "weight": 1.5, "description": "Safety promotion"},
        {"pattern": r"\bincident", "weight": 1.2, "description": "Incident reporting"},
        {"pattern": r"\baccident", "weight": 1.5, "description": "Accident investigation"},
        {"pattern": r"\bSDR\b", "weight": 1.5, "description": "Service Difficulty Reports"},
        {"pattern": r"\bservice\s+difficulty", "weight": 1.5, "description": "Service difficulty reporting"},
    ],
}


# =============================================================================
# CFR REFERENCE RULES
# =============================================================================

CFR_RULES: Dict[str, List[Dict[str, Any]]] = {
    Function.MP.value: [
        {"pattern": r"121\.367", "weight": 2.0, "description": "Maintenance program requirements"},
        {"pattern": r"121\.369", "weight": 2.0, "description": "Maintenance program content"},
        {"pattern": r"121\.1109", "weight": 1.8, "description": "CAMP supplemental provisions"},
        {"pattern": r"43\.3", "weight": 1.0, "description": "Persons authorized to perform maintenance"},
        {"pattern": r"43\.13", "weight": 1.0, "description": "Performance rules"},
        {"pattern": r"91\.409", "weight": 1.5, "description": "Inspection requirements"},
    ],
    Function.MOC.value: [
        {"pattern": r"121\.379", "weight": 2.0, "description": "MOC requirements"},
        {"pattern": r"121\.628", "weight": 1.8, "description": "Inoperable instruments/equipment"},
        {"pattern": r"91\.213", "weight": 1.8, "description": "Inoperative instruments"},
        {"pattern": r"121\.631", "weight": 1.5, "description": "Dispatch/flight release"},
    ],
    Function.DOM.value: [
        {"pattern": r"121\.363", "weight": 2.0, "description": "DOM responsibility"},
        {"pattern": r"121\.365", "weight": 2.0, "description": "Maintenance organization requirements"},
        {"pattern": r"119\.65", "weight": 1.5, "description": "Management personnel qualifications"},
        {"pattern": r"119\.67", "weight": 1.5, "description": "Management personnel requirements"},
    ],
    Function.RECORDS.value: [
        {"pattern": r"121\.380", "weight": 2.0, "description": "Maintenance recording requirements"},
        {"pattern": r"121\.380a", "weight": 2.0, "description": "Transfer of records"},
        {"pattern": r"43\.9", "weight": 1.8, "description": "Content of maintenance records"},
        {"pattern": r"43\.11", "weight": 1.8, "description": "Content of inspection records"},
        {"pattern": r"43\.12", "weight": 1.5, "description": "Maintenance records retention"},
        {"pattern": r"91\.417", "weight": 1.5, "description": "Maintenance records"},
    ],
    Function.QUALITY.value: [
        {"pattern": r"121\.371", "weight": 2.0, "description": "RII requirements"},
        {"pattern": r"121\.373", "weight": 2.0, "description": "RII qualifications"},
        {"pattern": r"121\.375", "weight": 1.8, "description": "Continuous analysis and surveillance"},
        {"pattern": r"145\.211", "weight": 1.5, "description": "Quality control system"},
        {"pattern": r"145\.223", "weight": 1.5, "description": "FAA inspections"},
    ],
    Function.TRAINING.value: [
        {"pattern": r"121\.375", "weight": 1.0, "description": "Training requirements (shared)"},
        {"pattern": r"121\.377", "weight": 2.0, "description": "Maintenance personnel training"},
        {"pattern": r"43\.3", "weight": 1.2, "description": "Maintenance authorization"},
        {"pattern": r"43\.7", "weight": 1.5, "description": "Persons authorized to approve"},
        {"pattern": r"65\.81", "weight": 1.5, "description": "Mechanic requirements"},
        {"pattern": r"65\.83", "weight": 1.5, "description": "Mechanic experience"},
    ],
    Function.SAFETY.value: [
        {"pattern": r"5\.21", "weight": 2.5, "description": "Safety policy"},
        {"pattern": r"5\.23", "weight": 2.5, "description": "Safety accountability"},
        {"pattern": r"5\.25", "weight": 2.0, "description": "Safety hazard identification"},
        {"pattern": r"5\.51", "weight": 2.0, "description": "SMS applicability"},
        {"pattern": r"5\.53", "weight": 2.0, "description": "SMS components"},
        {"pattern": r"121\.703", "weight": 1.5, "description": "Mechanical reliability reports"},
    ],
}


class OwnershipEngine:
    """
    Deterministic ownership assignment engine.

    Applies rules-based decision tree to assign each QID to a responsible function.
    Every decision includes rationale, confidence score, and signal breakdown for
    full transparency and PMI defensibility.
    """

    def __init__(self):
        """Initialize the ownership engine with default rules."""
        self.keyword_rules = KEYWORD_RULES
        self.cfr_rules = CFR_RULES
        self.custom_rules: List[Dict[str, Any]] = []

    def add_custom_rule(self, rule_type: str, pattern: str,
                       target_function: str, weight: float = 1.0,
                       description: str = "") -> None:
        """
        Add a custom ownership rule.

        Args:
            rule_type: "keyword" or "cfr"
            pattern: Regex pattern to match
            target_function: Target function name
            weight: Weight for scoring (default 1.0)
            description: Human-readable description
        """
        self.custom_rules.append({
            "rule_type": rule_type,
            "pattern": pattern,
            "target_function": target_function,
            "weight": weight,
            "description": description
        })

    def _match_keywords(self, text: str) -> List[Signal]:
        """
        Match question text against keyword rules.

        Args:
            text: Question text to analyze

        Returns:
            List of matched signals
        """
        signals = []
        text_lower = text.lower()

        for function, rules in self.keyword_rules.items():
            for rule in rules:
                matches = re.findall(rule["pattern"], text_lower, re.IGNORECASE)
                if matches:
                    for match in matches:
                        signals.append(Signal(
                            signal_type="keyword",
                            pattern=rule["pattern"],
                            matched_text=match if isinstance(match, str) else match[0],
                            target_function=function,
                            weight=rule["weight"]
                        ))

        # Check custom rules
        for rule in self.custom_rules:
            if rule["rule_type"] == "keyword":
                matches = re.findall(rule["pattern"], text_lower, re.IGNORECASE)
                if matches:
                    for match in matches:
                        signals.append(Signal(
                            signal_type="keyword",
                            pattern=rule["pattern"],
                            matched_text=match if isinstance(match, str) else match[0],
                            target_function=rule["target_function"],
                            weight=rule["weight"]
                        ))

        return signals

    def _match_cfr_references(self, references: List[str]) -> List[Signal]:
        """
        Match CFR references against CFR rules.

        Args:
            references: List of CFR reference strings

        Returns:
            List of matched signals
        """
        signals = []

        for ref in references:
            ref_clean = ref.replace(" ", "")

            for function, rules in self.cfr_rules.items():
                for rule in rules:
                    if re.search(rule["pattern"], ref_clean, re.IGNORECASE):
                        signals.append(Signal(
                            signal_type="cfr",
                            pattern=rule["pattern"],
                            matched_text=ref,
                            target_function=function,
                            weight=rule["weight"]
                        ))

            # Check custom rules
            for rule in self.custom_rules:
                if rule["rule_type"] == "cfr":
                    if re.search(rule["pattern"], ref_clean, re.IGNORECASE):
                        signals.append(Signal(
                            signal_type="cfr",
                            pattern=rule["pattern"],
                            matched_text=ref,
                            target_function=rule["target_function"],
                            weight=rule["weight"]
                        ))

        return signals

    def _calculate_scores(self, signals: List[Signal]) -> Dict[str, float]:
        """
        Calculate weighted scores for each function based on signals.

        Args:
            signals: List of matched signals

        Returns:
            Dictionary mapping function names to scores
        """
        scores: Dict[str, float] = {}

        for signal in signals:
            func = signal.target_function
            if func not in scores:
                scores[func] = 0.0
            scores[func] += signal.weight

        return scores

    def _determine_confidence(self, scores: Dict[str, float],
                             signals: List[Signal]) -> Tuple[str, float]:
        """
        Determine confidence level based on signal strength and clarity.

        Args:
            scores: Function scores
            signals: List of matched signals

        Returns:
            Tuple of (confidence_label, confidence_value)
        """
        if not scores:
            return Confidence.LOW.value, 0.0

        sorted_scores = sorted(scores.values(), reverse=True)
        top_score = sorted_scores[0]

        # Calculate confidence based on:
        # 1. Total signal strength
        # 2. Gap between top and second choice
        # 3. Number of unique signals

        total_signals = len(signals)
        unique_signal_types = len(set(s.signal_type for s in signals))

        # Gap ratio (how much better is top vs second)
        gap_ratio = 1.0
        if len(sorted_scores) > 1 and sorted_scores[1] > 0:
            gap_ratio = top_score / sorted_scores[1]

        # Calculate confidence value (0.0 - 1.0)
        base_confidence = min(top_score / 10.0, 1.0)  # Cap at 10 points
        signal_bonus = min(total_signals * 0.05, 0.2)  # Bonus for more signals
        diversity_bonus = unique_signal_types * 0.1  # Bonus for diverse signals
        gap_bonus = min((gap_ratio - 1) * 0.1, 0.2)  # Bonus for clear winner

        confidence_value = min(
            base_confidence + signal_bonus + diversity_bonus + gap_bonus,
            1.0
        )

        # Map to confidence label
        if confidence_value >= 0.7:
            confidence_label = Confidence.HIGH.value
        elif confidence_value >= 0.4:
            confidence_label = Confidence.MEDIUM.value
        else:
            confidence_label = Confidence.LOW.value

        return confidence_label, confidence_value

    def _build_rationale(self, primary: str, signals: List[Signal],
                        scores: Dict[str, float]) -> str:
        """
        Build human-readable rationale for the assignment decision.

        Args:
            primary: Primary assigned function
            signals: List of matched signals
            scores: Function scores

        Returns:
            Rationale string
        """
        if not signals:
            return f"Assigned to {primary} by default (no signals detected). Manual review recommended."

        # Group signals by type for the primary function
        primary_signals = [s for s in signals if s.target_function == primary]
        keyword_signals = [s for s in primary_signals if s.signal_type == "keyword"]
        cfr_signals = [s for s in primary_signals if s.signal_type == "cfr"]

        rationale_parts = [f"Assigned to {primary} based on:"]

        if keyword_signals:
            keywords = list(set(s.matched_text for s in keyword_signals[:5]))
            rationale_parts.append(f"- Keyword matches: {', '.join(keywords)}")

        if cfr_signals:
            cfrs = list(set(s.matched_text for s in cfr_signals[:5]))
            rationale_parts.append(f"- CFR references: {', '.join(cfrs)}")

        # Note if there were competing signals
        other_functions = [f for f in scores.keys() if f != primary and scores[f] > 0]
        if other_functions:
            rationale_parts.append(
                f"- Note: Also has signals for {', '.join(other_functions[:3])} "
                f"(may need supporting function coordination)"
            )

        return " ".join(rationale_parts)

    def _identify_supporting_functions(self, primary: str,
                                       scores: Dict[str, float],
                                       threshold: float = 0.3) -> List[str]:
        """
        Identify supporting functions that may need coordination.

        Args:
            primary: Primary assigned function
            scores: Function scores
            threshold: Minimum score ratio to primary for consideration

        Returns:
            List of supporting function names
        """
        if not scores or primary not in scores:
            return []

        primary_score = scores[primary]
        if primary_score == 0:
            return []

        supporting = []
        for func, score in scores.items():
            if func != primary and score > 0:
                ratio = score / primary_score
                if ratio >= threshold:
                    supporting.append(func)

        # Sort by score descending
        supporting.sort(key=lambda f: scores.get(f, 0), reverse=True)
        return supporting[:3]  # Max 3 supporting functions

    def assign_ownership(self, question: Dict[str, Any]) -> OwnershipDecision:
        """
        Assign ownership for a single question.

        Args:
            question: Question dictionary with QID, text, and references

        Returns:
            OwnershipDecision with full breakdown
        """
        qid = question.get("QID", "unknown")
        question_text = question.get("Question_Text_Full", "")
        cfr_refs = question.get("Reference_CFR_List", [])

        # Collect all signals
        signals = []
        signals.extend(self._match_keywords(question_text))
        signals.extend(self._match_cfr_references(cfr_refs))

        # Calculate scores
        scores = self._calculate_scores(signals)

        # Determine primary function
        if scores:
            primary = max(scores.keys(), key=lambda k: scores[k])
        else:
            # Default assignment when no signals
            primary = Function.DOM.value  # DOM as catch-all for unmatched
            logger.warning(f"No signals for QID {qid}, defaulting to {primary}")

        # Calculate confidence
        confidence_label, confidence_value = self._determine_confidence(scores, signals)

        # Identify supporting functions
        supporting = self._identify_supporting_functions(primary, scores)

        # Build rationale
        rationale = self._build_rationale(primary, signals, scores)

        # Format signal breakdown
        keyword_matches = [
            {"pattern": s.pattern, "matched": s.matched_text, "weight": s.weight}
            for s in signals if s.signal_type == "keyword" and s.target_function == primary
        ]
        cfr_matches = [
            {"pattern": s.pattern, "matched": s.matched_text, "weight": s.weight}
            for s in signals if s.signal_type == "cfr" and s.target_function == primary
        ]

        return OwnershipDecision(
            qid=qid,
            primary_function=primary,
            supporting_functions=supporting,
            confidence_score=confidence_label,
            confidence_value=round(confidence_value, 3),
            rationale=rationale,
            keyword_matches=keyword_matches,
            cfr_matches=cfr_matches,
            signals=signals
        )

    def assign_all(self, questions: List[Dict[str, Any]]) -> List[OwnershipDecision]:
        """
        Assign ownership for all questions.

        Args:
            questions: List of question dictionaries

        Returns:
            List of OwnershipDecision objects
        """
        decisions = []
        for question in questions:
            decision = self.assign_ownership(question)
            decisions.append(decision)
        return decisions

    def get_summary(self, decisions: List[OwnershipDecision]) -> Dict[str, Any]:
        """
        Generate summary statistics for ownership assignments.

        Args:
            decisions: List of ownership decisions

        Returns:
            Summary dictionary with statistics
        """
        total = len(decisions)
        if total == 0:
            return {"total": 0, "by_function": {}, "by_confidence": {}}

        # Count by function
        by_function: Dict[str, int] = {}
        for d in decisions:
            func = d.primary_function
            by_function[func] = by_function.get(func, 0) + 1

        # Count by confidence
        by_confidence: Dict[str, int] = {}
        for d in decisions:
            conf = d.confidence_score
            by_confidence[conf] = by_confidence.get(conf, 0) + 1

        # Calculate percentages
        function_percentages = {
            f: round(count / total * 100, 1)
            for f, count in by_function.items()
        }
        confidence_percentages = {
            c: round(count / total * 100, 1)
            for c, count in by_confidence.items()
        }

        return {
            "total": total,
            "by_function": by_function,
            "by_confidence": by_confidence,
            "function_percentages": function_percentages,
            "confidence_percentages": confidence_percentages,
            "low_confidence_count": by_confidence.get(Confidence.LOW.value, 0),
            "needs_review_count": by_confidence.get(Confidence.LOW.value, 0)
        }


def assign_ownership_to_audit(questions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to assign ownership to all questions in an audit.

    Args:
        questions: List of question dictionaries from parsed audit

    Returns:
        Tuple of (assignments list, summary dict)
    """
    engine = OwnershipEngine()
    decisions = engine.assign_all(questions)
    summary = engine.get_summary(decisions)

    # Convert decisions to dictionaries
    assignments = []
    for d in decisions:
        assignments.append({
            "qid": d.qid,
            "primary_function": d.primary_function,
            "supporting_functions": d.supporting_functions,
            "confidence_score": d.confidence_score,
            "confidence_value": d.confidence_value,
            "rationale": d.rationale,
            "keyword_matches": d.keyword_matches,
            "cfr_matches": d.cfr_matches
        })

    return assignments, summary
