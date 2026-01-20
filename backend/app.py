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


if __name__ == '__main__':
    print("Starting FAA DCT Audit Application...")
    print("Backend API running on http://localhost:5000")
    print("API Documentation: http://localhost:5000/api/health")
    print("Database: SQLite (faa_audit.db)")
    app.run(debug=True, host='0.0.0.0', port=5000)
