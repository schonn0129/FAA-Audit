"""
FAA DCT Audit Application - Backend API

Flask application for processing and managing FAA DCT audit documents.
"""

import os
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pdf_parser import FAAPDFParser
import database as db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Upload and parse a PDF file."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if file.filename == '' or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    # Check file extension (case-insensitive)
    if not allowed_file(file.filename):
        return jsonify({
            "error": "Invalid file type. Only PDF files are allowed.",
            "received": file.filename
        }), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer

    if file_size > MAX_FILE_SIZE:
        return jsonify({
            "error": f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024)}MB"
        }), 400

    try:
        # Generate unique ID for this upload
        record_id = str(uuid.uuid4())

        # Save file
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({"error": "Invalid filename"}), 400

        filepath = os.path.join(UPLOAD_FOLDER, f"{record_id}_{filename}")

        # Ensure upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        file.save(filepath)

        # Verify file was saved and is readable
        if not os.path.exists(filepath):
            return jsonify({"error": "Failed to save file"}), 500

        # Parse PDF
        logger.info(f"Parsing PDF: {filepath}")
        with FAAPDFParser(filepath) as parser:
            parsed_data = parser.parse()

        # Save to database
        audit = db.save_audit(record_id, filename, parsed_data)

        logger.info(f"Successfully parsed PDF. Questions found: {len(parsed_data.get('questions', []))}")

        return jsonify({
            "id": record_id,
            "filename": filename,
            "status": "completed",
            "uploaded_at": datetime.utcnow().isoformat(),
            "summary": {
                "pages": parsed_data.get('metadata', {}).get('page_count', 0),
                "questions": len(parsed_data.get('questions', [])),
                "tables": len(parsed_data.get('tables', [])),
                "findings": len(parsed_data.get('findings', []))
            }
        }), 200

    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to process PDF",
            "message": str(e)
        }), 500


@app.route('/api/audits', methods=['GET'])
def get_audits():
    """Get all audit records."""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)

    # Get from database
    result = db.get_all_audits(page=page, per_page=limit)

    # Return summary (without full data)
    records_summary = []
    for record in result["audits"]:
        records_summary.append({
            "id": record["id"],
            "filename": record["filename"],
            "status": record["status"],
            "uploaded_at": record["upload_date"],
            "summary": {
                "pages": record.get("metadata", {}).get("page_count", 0),
                "questions": len(record.get("questions", [])),
                "tables": len(record.get("tables", [])),
                "findings": len(record.get("findings", []))
            }
        })

    return jsonify({
        "records": records_summary,
        "total": result["pagination"]["total"],
        "page": page,
        "limit": limit
    }), 200


@app.route('/api/audits/<audit_id>', methods=['GET'])
def get_audit(audit_id):
    """Get a specific audit record."""
    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    # Format response to match expected structure
    return jsonify({
        "id": record["id"],
        "filename": record["filename"],
        "status": record["status"],
        "uploaded_at": record["upload_date"],
        "data": {
            "metadata": record["metadata"],
            "questions": record["questions"],
            "findings": record["findings"],
            "tables": record["tables"],
            "compliance": record["compliance"],
            "raw_text_length": record["raw_text_length"]
        }
    }), 200


@app.route('/api/audits/<audit_id>', methods=['PUT'])
def update_audit(audit_id):
    """Update an audit record."""
    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    # For now, just return the existing record
    # TODO: Implement actual update logic
    return jsonify(record), 200


@app.route('/api/audits/<audit_id>', methods=['DELETE'])
def delete_audit(audit_id):
    """Delete an audit record."""
    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    # Delete associated file
    filepath = os.path.join(UPLOAD_FOLDER, f"{audit_id}_{record['filename']}")
    if os.path.exists(filepath):
        os.remove(filepath)

    # Delete from database
    db.delete_audit(audit_id)

    return jsonify({"message": "Record deleted successfully"}), 200


@app.route('/api/audits/search', methods=['GET'])
def search_audits():
    """Search audit records."""
    query = request.args.get('q', '')
    date_from = request.args.get('date_from', None)
    date_to = request.args.get('date_to', None)

    results = db.search_audits(filename=query, start_date=date_from, end_date=date_to)

    return jsonify({
        "results": [{
            "id": r["id"],
            "filename": r["filename"],
            "status": r["status"],
            "uploaded_at": r["upload_date"]
        } for r in results]
    }), 200


@app.route('/api/export', methods=['GET'])
def export_data():
    """Export audit data."""
    from flask import Response
    import export_map

    format_type = request.args.get('format', 'json')
    audit_ids = request.args.get('audit_ids', '').split(',') if request.args.get('audit_ids') else None

    # Get records from database
    if audit_ids and audit_ids[0]:
        records = [db.get_audit(id) for id in audit_ids]
        records = [r for r in records if r is not None]
    else:
        result = db.get_all_audits(page=1, per_page=1000)
        records = result["audits"]

    if not records:
        return jsonify({"error": "No records found"}), 404

    if format_type == 'json':
        return jsonify({"audits": records}), 200

    elif format_type == 'csv':
        csv_data = export_map.export_audits_to_csv(records)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=faa_audit_export.csv'}
        )

    elif format_type == 'xlsx':
        try:
            xlsx_data = export_map.export_audits_to_xlsx(records)
            return Response(
                xlsx_data,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': 'attachment; filename=faa_audit_export.xlsx'}
            )
        except ImportError as e:
            return jsonify({"error": str(e)}), 400

    else:
        return jsonify({"error": f"Export format '{format_type}' not supported. Use 'json', 'csv', or 'xlsx'."}), 400


@app.route('/api/audits/<audit_id>/export', methods=['GET'])
def export_single_audit(audit_id):
    """Export a single audit's data."""
    from flask import Response
    import export_map

    format_type = request.args.get('format', 'json')

    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    if format_type == 'json':
        return jsonify(record), 200

    elif format_type == 'csv':
        csv_data = export_map.export_audit_to_csv(record)
        filename = f"{record['filename'].rsplit('.', 1)[0]}_export.csv"
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    elif format_type == 'xlsx':
        try:
            xlsx_data = export_map.export_audit_to_xlsx(record)
            filename = f"{record['filename'].rsplit('.', 1)[0]}_export.xlsx"
            return Response(
                xlsx_data,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
        except ImportError as e:
            return jsonify({"error": str(e)}), 400

    else:
        return jsonify({"error": f"Export format '{format_type}' not supported. Use 'json', 'csv', or 'xlsx'."}), 400


# =============================================================================
# OWNERSHIP ASSIGNMENT ENDPOINTS (Phase 2)
# =============================================================================

@app.route('/api/audits/<audit_id>/ownership', methods=['POST'])
def assign_ownership(audit_id):
    """
    Run ownership assignment engine on an audit's questions.

    This applies the deterministic rules-based decision tree to assign
    each QID to one of the 7 authorized functions.
    """
    from ownership import OwnershipEngine, assign_ownership_to_audit

    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    questions = record.get("questions", [])
    if not questions:
        return jsonify({"error": "No questions found in audit"}), 400

    try:
        # Run ownership assignment
        assignments, summary = assign_ownership_to_audit(questions)

        # Save assignments to database
        db.save_ownership_assignments(audit_id, assignments)

        logger.info(f"Ownership assigned for audit {audit_id}: {summary['total']} questions")

        return jsonify({
            "audit_id": audit_id,
            "assignments": assignments,
            "summary": summary
        }), 200

    except Exception as e:
        logger.error(f"Error assigning ownership: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to assign ownership",
            "message": str(e)
        }), 500


@app.route('/api/audits/<audit_id>/ownership', methods=['GET'])
def get_ownership(audit_id):
    """Get ownership assignments for an audit."""
    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    # Get assignments from database
    assignments = db.get_ownership_assignments(audit_id)

    if not assignments:
        return jsonify({
            "audit_id": audit_id,
            "message": "No ownership assignments found. Run POST /api/audits/{id}/ownership first.",
            "assignments": [],
            "summary": None
        }), 200

    # Calculate summary
    total = len(assignments)
    by_function = {}
    by_confidence = {}

    for a in assignments:
        func = a.get("primary_function", "Unknown")
        conf = a.get("confidence_score", "Unknown")
        by_function[func] = by_function.get(func, 0) + 1
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

    summary = {
        "total": total,
        "by_function": by_function,
        "by_confidence": by_confidence,
        "function_percentages": {f: round(c / total * 100, 1) for f, c in by_function.items()},
        "low_confidence_count": by_confidence.get("Low", 0)
    }

    return jsonify({
        "audit_id": audit_id,
        "assignments": assignments,
        "summary": summary
    }), 200


@app.route('/api/audits/<audit_id>/ownership/<qid>', methods=['PUT'])
def override_ownership(audit_id, qid):
    """
    Manually override ownership assignment for a specific question.

    Request body:
    {
        "primary_function": "Quality",
        "supporting_functions": ["Training"],
        "override_reason": "Per management decision...",
        "override_by": "John Smith"
    }
    """
    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    primary_function = data.get("primary_function")
    if not primary_function:
        return jsonify({"error": "primary_function is required"}), 400

    # Validate function is one of the 7 authorized
    valid_functions = [
        "Maintenance Planning",
        "Maintenance Operations Center",
        "Director of Maintenance",
        "Aircraft Records",
        "Quality",
        "Training",
        "Safety"
    ]
    if primary_function not in valid_functions:
        return jsonify({
            "error": f"Invalid function. Must be one of: {', '.join(valid_functions)}"
        }), 400

    try:
        # Update assignment in database
        updated = db.override_ownership_assignment(
            audit_id=audit_id,
            qid=qid,
            primary_function=primary_function,
            supporting_functions=data.get("supporting_functions", []),
            override_reason=data.get("override_reason", "Manual override"),
            override_by=data.get("override_by", "Unknown")
        )

        if not updated:
            return jsonify({"error": "Question not found or no existing assignment"}), 404

        logger.info(f"Ownership override for QID {qid}: {primary_function}")

        return jsonify({
            "message": "Ownership override successful",
            "qid": qid,
            "primary_function": primary_function,
            "is_manual_override": True
        }), 200

    except Exception as e:
        logger.error(f"Error overriding ownership: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to override ownership",
            "message": str(e)
        }), 500


@app.route('/api/ownership/rules', methods=['GET'])
def get_ownership_rules():
    """Get all ownership assignment rules (keywords and CFR mappings)."""
    from ownership import KEYWORD_RULES, CFR_RULES

    return jsonify({
        "keyword_rules": KEYWORD_RULES,
        "cfr_rules": CFR_RULES,
        "functions": [
            "Maintenance Planning",
            "Maintenance Operations Center",
            "Director of Maintenance",
            "Aircraft Records",
            "Quality",
            "Training",
            "Safety"
        ]
    }), 200


@app.route('/api/ownership/rules', methods=['POST'])
def add_ownership_rule():
    """
    Add a custom ownership rule.

    Request body:
    {
        "rule_type": "keyword",  // or "cfr"
        "pattern": "\\bmy_keyword\\b",
        "target_function": "Quality",
        "weight": 1.5,
        "notes": "Custom rule for XYZ"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    required_fields = ["rule_type", "pattern", "target_function"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    if data["rule_type"] not in ["keyword", "cfr"]:
        return jsonify({"error": "rule_type must be 'keyword' or 'cfr'"}), 400

    try:
        rule_id = db.add_ownership_rule(
            rule_type=data["rule_type"],
            pattern=data["pattern"],
            target_function=data["target_function"],
            weight=data.get("weight", 1.0),
            notes=data.get("notes")
        )

        return jsonify({
            "message": "Rule added successfully",
            "rule_id": rule_id
        }), 201

    except Exception as e:
        logger.error(f"Error adding ownership rule: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to add rule",
            "message": str(e)
        }), 500


@app.route('/api/ownership/summary', methods=['GET'])
def get_ownership_summary():
    """Get ownership summary across all audits."""
    try:
        summary = db.get_ownership_summary()
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error getting ownership summary: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to get summary",
            "message": str(e)
        }), 500


# =============================================================================
# AUDIT SCOPE ENDPOINTS (Phase 3)
# =============================================================================

@app.route('/api/audits/<audit_id>/scope', methods=['GET'])
def get_audit_scope(audit_id):
    """
    Get the current scope configuration for an audit.

    Returns the list of in-scope functions and available functions.
    """
    from scoping import get_available_functions

    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Audit not found"}), 404

    scope = db.get_audit_scope(audit_id)

    return jsonify({
        "audit_id": audit_id,
        "scope": scope,
        "available_functions": get_available_functions()
    }), 200


@app.route('/api/audits/<audit_id>/scope', methods=['POST'])
def create_audit_scope(audit_id):
    """
    Create or update the scope configuration for an audit.

    Request body:
    {
        "in_scope_functions": ["Maintenance Planning", "Aircraft Records"],
        "scope_name": "Q1 2026 Maintenance Focus",
        "scope_rationale": "Per annual audit plan",
        "created_by": "John Smith"
    }
    """
    from scoping import validate_scope_functions

    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Audit not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    in_scope_functions = data.get("in_scope_functions")
    if not in_scope_functions:
        return jsonify({"error": "in_scope_functions is required"}), 400

    # Validate functions
    is_valid, invalid = validate_scope_functions(in_scope_functions)
    if not is_valid:
        return jsonify({
            "error": "Invalid functions specified",
            "invalid_functions": invalid
        }), 400

    try:
        scope = db.save_audit_scope(
            audit_id=audit_id,
            in_scope_functions=in_scope_functions,
            scope_name=data.get("scope_name"),
            scope_rationale=data.get("scope_rationale"),
            created_by=data.get("created_by")
        )

        logger.info(f"Scope set for audit {audit_id}: {len(in_scope_functions)} functions in scope")

        return jsonify({
            "message": "Scope saved successfully",
            "audit_id": audit_id,
            "scope": scope
        }), 200

    except Exception as e:
        logger.error(f"Error saving scope: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to save scope",
            "message": str(e)
        }), 500


@app.route('/api/audits/<audit_id>/scope', methods=['DELETE'])
def delete_audit_scope(audit_id):
    """
    Delete the scope configuration (reset to all functions in scope).
    """
    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Audit not found"}), 404

    deleted = db.delete_audit_scope(audit_id)

    if deleted:
        logger.info(f"Scope deleted for audit {audit_id}")
        return jsonify({
            "message": "Scope deleted. All functions are now in scope.",
            "audit_id": audit_id
        }), 200
    else:
        return jsonify({
            "message": "No scope was defined for this audit.",
            "audit_id": audit_id
        }), 200


@app.route('/api/audits/<audit_id>/coverage', methods=['GET'])
def get_audit_coverage(audit_id):
    """
    Get coverage metrics for an audit based on its scope.

    Returns breakdown of in-scope vs. deferred QIDs by function.
    """
    from scoping import calculate_coverage_metrics, calculate_accountability_check, VALID_FUNCTIONS

    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Audit not found"}), 404

    # Get assignments
    assignments = db.get_ownership_assignments(audit_id)

    if not assignments:
        return jsonify({
            "error": "No ownership assignments found. Run POST /api/audits/{id}/ownership first.",
            "audit_id": audit_id
        }), 400

    # Get scope
    scope = db.get_audit_scope(audit_id)
    if scope:
        in_scope_functions = scope.get("in_scope_functions", VALID_FUNCTIONS)
    else:
        in_scope_functions = VALID_FUNCTIONS

    # Calculate metrics
    metrics = calculate_coverage_metrics(assignments, in_scope_functions)
    accountability = calculate_accountability_check(assignments)

    return jsonify({
        "audit_id": audit_id,
        "total_qids": metrics.total_qids,
        "coverage": {
            "overall_percentage": metrics.overall_percentage,
            "in_scope_count": metrics.in_scope_count,
            "deferred_count": metrics.deferred_count,
            "by_function": metrics.by_function
        },
        "in_scope_functions": in_scope_functions,
        "accountability_check": accountability
    }), 200


@app.route('/api/audits/<audit_id>/deferred', methods=['GET'])
def get_deferred_items(audit_id):
    """
    Get deferred items report for PDF appendix generation.

    Lists all QIDs that are NOT in scope for this audit cycle,
    along with their assigned owners.
    """
    from scoping import generate_deferred_report, VALID_FUNCTIONS

    record = db.get_audit(audit_id)
    if not record:
        return jsonify({"error": "Audit not found"}), 404

    # Get assignments
    assignments = db.get_ownership_assignments(audit_id)

    if not assignments:
        return jsonify({
            "error": "No ownership assignments found. Run POST /api/audits/{id}/ownership first.",
            "audit_id": audit_id
        }), 400

    # Get scope
    scope = db.get_audit_scope(audit_id)
    if scope:
        in_scope_functions = scope.get("in_scope_functions", VALID_FUNCTIONS)
        scope_rationale = scope.get("scope_rationale", "")
    else:
        in_scope_functions = VALID_FUNCTIONS
        scope_rationale = "No scope defined - all functions in scope"

    # Generate report
    report = generate_deferred_report(assignments, in_scope_functions, scope_rationale)
    report["audit_id"] = audit_id

    return jsonify(report), 200


if __name__ == '__main__':
    print("Starting FAA DCT Audit Application...")
    print("Backend API running on http://localhost:5000")
    print("API Documentation: http://localhost:5000/api/health")
    print("Database: SQLite (faa_audit.db)")
    app.run(debug=True, host='0.0.0.0', port=5000)
