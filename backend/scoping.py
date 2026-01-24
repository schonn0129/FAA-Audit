"""
Audit Scoping Module for FAA DCT Compliance Engine.

This module implements the scoping layer that allows users to define
which functions are in-scope for an audit while maintaining full
QID accountability.

Key Design Principle: Scope is a FILTER/VIEW, not a modification
of the ownership table. All QIDs remain assigned to their functions
regardless of audit scope.

PMI Requirement: "This ensures PMI can see you accounted for everything,
even if you didn't audit everything."
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from ownership import Function


# The 7 authorized functions (derived from Function enum for consistency)
VALID_FUNCTIONS = [f.value for f in Function]


@dataclass
class CoverageMetrics:
    """Coverage metrics for an audit scope."""
    total_qids: int
    in_scope_count: int
    deferred_count: int
    overall_percentage: float
    by_function: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def validate_scope_functions(functions: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all specified functions are in the authorized list.

    Args:
        functions: List of function names to validate

    Returns:
        Tuple of (is_valid, invalid_functions)
    """
    if not functions:
        return False, ["At least one function must be selected"]

    invalid = [f for f in functions if f not in VALID_FUNCTIONS]
    return len(invalid) == 0, invalid


def get_available_functions() -> List[str]:
    """
    Get the list of all available functions.

    Returns:
        List of function names
    """
    return VALID_FUNCTIONS.copy()


def calculate_coverage_metrics(
    assignments: List[Dict[str, Any]],
    in_scope_functions: List[str]
) -> CoverageMetrics:
    """
    Calculate coverage metrics for a given scope.

    Args:
        assignments: List of ownership assignments (each with 'primary_function')
        in_scope_functions: List of functions that are in scope

    Returns:
        CoverageMetrics object with detailed breakdown
    """
    total = len(assignments)
    if total == 0:
        return CoverageMetrics(
            total_qids=0,
            in_scope_count=0,
            deferred_count=0,
            overall_percentage=0.0,
            by_function={}
        )

    # Count by function
    by_function: Dict[str, Dict[str, Any]] = {}
    in_scope_count = 0

    for func in VALID_FUNCTIONS:
        func_assignments = [a for a in assignments if a.get("primary_function") == func]
        func_count = len(func_assignments)
        is_in_scope = func in in_scope_functions

        if is_in_scope:
            in_scope_count += func_count

        by_function[func] = {
            "total": func_count,
            "in_scope": is_in_scope,
            "percentage_of_audit": round(func_count / total * 100, 1) if total > 0 else 0,
            "percentage_covered": 100.0 if is_in_scope else 0.0
        }

    deferred_count = total - in_scope_count
    overall_percentage = round(in_scope_count / total * 100, 1) if total > 0 else 0

    return CoverageMetrics(
        total_qids=total,
        in_scope_count=in_scope_count,
        deferred_count=deferred_count,
        overall_percentage=overall_percentage,
        by_function=by_function
    )


def filter_assignments_by_scope(
    assignments: List[Dict[str, Any]],
    in_scope_functions: List[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Separate assignments into in-scope and deferred lists.

    Args:
        assignments: List of all ownership assignments
        in_scope_functions: List of functions that are in scope

    Returns:
        Tuple of (in_scope_assignments, deferred_assignments)
    """
    in_scope = []
    deferred = []

    for assignment in assignments:
        if assignment.get("primary_function") in in_scope_functions:
            in_scope.append(assignment)
        else:
            # Add deferral reason
            assignment_copy = assignment.copy()
            assignment_copy["deferral_reason"] = "Function not in current audit scope"
            deferred.append(assignment_copy)

    return in_scope, deferred


def generate_deferred_report(
    assignments: List[Dict[str, Any]],
    in_scope_functions: List[str],
    scope_rationale: str = ""
) -> Dict[str, Any]:
    """
    Generate the deferred items report for PDF appendix.

    This report documents all QIDs that are NOT being audited in this cycle,
    along with their assigned owners. This satisfies the PMI requirement that
    all QIDs must be accounted for.

    Args:
        assignments: List of all ownership assignments
        in_scope_functions: List of functions that are in scope
        scope_rationale: Reason for the scope selection

    Returns:
        Report dictionary ready for PDF generation
    """
    _, deferred = filter_assignments_by_scope(assignments, in_scope_functions)

    # Summary by function
    summary_by_function: Dict[str, int] = {}
    for item in deferred:
        func = item.get("primary_function", "Unknown")
        summary_by_function[func] = summary_by_function.get(func, 0) + 1

    # Sort summary by count descending
    sorted_summary = dict(sorted(
        summary_by_function.items(),
        key=lambda x: x[1],
        reverse=True
    ))

    return {
        "generated_date": datetime.utcnow().isoformat(),
        "scope_rationale": scope_rationale,
        "in_scope_functions": in_scope_functions,
        "out_of_scope_functions": [f for f in VALID_FUNCTIONS if f not in in_scope_functions],
        "deferred_items": deferred,
        "summary_by_function": sorted_summary,
        "total_deferred": len(deferred)
    }


def calculate_accountability_check(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify that all QIDs have ownership assigned.

    This is a critical PMI defensibility check - every QID must have
    an assigned owner, regardless of whether it's in-scope or deferred.

    Args:
        assignments: List of all ownership assignments

    Returns:
        Dictionary with accountability check results
    """
    total = len(assignments)
    assigned = sum(1 for a in assignments if a.get("primary_function"))
    orphaned = total - assigned

    return {
        "all_qids_assigned": orphaned == 0,
        "total_qids": total,
        "assigned_qids": assigned,
        "orphaned_qids": orphaned,
        "message": (
            "100% of QIDs have ownership assigned"
            if orphaned == 0
            else f"Warning: {orphaned} QIDs do not have ownership assigned"
        )
    }
