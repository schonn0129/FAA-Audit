# Development Documentation

## API Endpoints

### Base URL
All API endpoints are prefixed with `/api`

### Endpoints

#### 1. Health Check
- **GET** `/api/health`
- **Description**: Check if the API server is running
- **Response**: 
  ```json
  {
    "status": "ok",
    "timestamp": "2024-01-01T00:00:00Z"
  }
  ```

#### 2. Upload PDF
- **POST** `/api/upload`
- **Description**: Upload a PDF file for parsing and processing
- **Request**: 
  - Content-Type: `multipart/form-data`
  - Body: PDF file
- **Response**:
  ```json
  {
    "id": "uuid",
    "filename": "document.pdf",
    "status": "processing",
    "uploaded_at": "2024-01-01T00:00:00Z"
  }
  ```

#### 3. Get Audit Records
- **GET** `/api/audits`
- **Description**: Retrieve all audit records
- **Query Parameters**:
  - `page` (optional): Page number for pagination
  - `limit` (optional): Number of records per page
  - `status` (optional): Filter by status
- **Response**:
  ```json
  {
    "records": [
      {
        "id": "uuid",
        "filename": "document.pdf",
        "status": "completed",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "limit": 10
  }
  ```

#### 4. Get Single Audit Record
- **GET** `/api/audits/:id`
- **Description**: Retrieve a specific audit record by ID
- **Response**:
  ```json
  {
    "id": "uuid",
    "filename": "document.pdf",
    "status": "completed",
    "data": {
      // Parsed audit data
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
  ```

#### 5. Update Audit Record
- **PUT** `/api/audits/:id`
- **Description**: Update an existing audit record
- **Request Body**:
  ```json
  {
    "status": "reviewed",
    "notes": "Additional notes"
  }
  ```
- **Response**: Updated audit record

#### 6. Delete Audit Record
- **DELETE** `/api/audits/:id`
- **Description**: Delete an audit record
- **Response**:
  ```json
  {
    "message": "Record deleted successfully"
  }
  ```

#### 7. Export Data
- **GET** `/api/export`
- **Description**: Export audit data in various formats
- **Query Parameters**:
  - `format` (required): Export format (`csv`, `json`, `xlsx`)
  - `audit_ids` (optional): Comma-separated list of audit IDs to export
- **Response**: File download or JSON data depending on format

#### 8. Search Audits
- **GET** `/api/audits/search`
- **Description**: Search audit records by various criteria
- **Query Parameters**:
  - `q` (optional): Search query string
  - `date_from` (optional): Start date filter
  - `date_to` (optional): End date filter
- **Response**: List of matching audit records

## Error Responses

All endpoints may return the following error responses:

- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

Error response format:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

## PDF Parsing

### Overview

The PDF parsing system extracts structured data from FAA audit documents using the `pdfplumber` library. The parser handles various document formats and extracts metadata, findings, compliance data, and tables.

### How It Works

#### 1. **Text Extraction**
- Uses `pdfplumber` to extract raw text from all pages of the PDF
- Combines text from all pages into a single searchable string
- Preserves page boundaries for reference

#### 2. **Metadata Extraction**
The parser uses regex patterns to identify and extract:
- **Inspection Dates**: Searches for common date formats (MM/DD/YYYY, MM-DD-YYYY)
- **Inspector Names**: Identifies inspector names from headers and labels
- **Facility Information**: Extracts facility names and numbers
- **Document Type**: Classifies documents as "audit", "violation_report", or "unknown"

#### 3. **Table Extraction**
- Automatically detects and extracts all tables from each page
- Preserves table structure with headers and rows
- Returns tables as structured data with page references

#### 4. **Findings Extraction**
Identifies audit findings and violations by searching for:
- Finding numbers (e.g., "Finding 1:", "Finding 2:")
- Violation codes (e.g., "14 CFR 91.205")
- Descriptions and details associated with each finding
- Severity levels (critical, major, minor)

#### 5. **DCT Question Extraction**
Extracts structured DCT (Data Collection Tool) questions with all required fields:

**Extracted Fields:**
- **Element_ID**: Element identifier (e.g., 4.2.2, 4.1.1)
- **QID**: DCT Question ID (exact, no changes)
- **Question_Number**: Numbered questions within element (1., 2., 3.)
- **Question_Text_Full**: Full question/intent text as printed
- **Question_Text_Condensed**: Short label generated from full text
- **Data_Collection_Guidance**: "Guidance" / "How to verify" text
- **Reference_Raw**: Raw combined reference string (CFR, Orders, etc.)
- **Reference_CFR_List**: Parsed CFR citations (e.g., 14 CFR 121.369(b))
- **Reference_FAA_Guidance_List**: FAA Orders, Notices, ACs, etc.
- **Reference_Other_List**: Other references (e.g., "FAA DCT Job Aid", "PMI Guidance")
- **PDF_Page_Number**: Page where question appears
- **PDF_Element_Block_ID**: Internal tag for multiple tables per element
- **Notes**: Parsing comments/issues (e.g., "row split across pages")

**Extraction Methods:**
1. **Table-based extraction**: Primary method - extracts from DCT tables
   - Automatically maps columns (Element_ID, QID, Question_Text, Guidance, References)
   - Handles various header naming conventions
   - Tracks element blocks for complex PDFs
2. **Text pattern extraction**: Fallback for non-table formats
   - Identifies element IDs (4.2.2 pattern)
   - Extracts numbered questions within elements
   - Parses references from text

**Reference Parsing:**
- Automatically identifies and separates:
  - CFR citations (14 CFR 121.369(b))
  - FAA Guidance (Orders, ACs, Notices)
  - Other references (Job Aids, PMI Guidance, etc.)

#### 6. **Compliance Data**
Calculates compliance metrics:
- Total number of findings
- Breakdown by severity (critical, major, minor)
- Compliance percentage (if available in document)
- Overall compliance status:
  - `compliant`: No findings
  - `mostly_compliant`: Only minor findings
  - `needs_improvement`: Major findings present
  - `non_compliant`: Critical findings present

### Usage

```python
from pdf_parser import parse_pdf, FAAPDFParser

# Simple usage
parsed_data = parse_pdf("path/to/audit.pdf")

# Advanced usage with context manager
with FAAPDFParser("path/to/audit.pdf") as parser:
    metadata = parser.extract_metadata()
    findings = parser.extract_findings()
    tables = parser.extract_tables()
    compliance = parser.extract_compliance_data()
```

### Parsed Data Structure

```json
{
  "metadata": {
    "inspection_date": "2024-01-15T00:00:00",
    "inspector_name": "John Doe",
    "facility_name": "ABC Aviation",
    "facility_number": "FAA-12345",
    "document_type": "audit",
    "page_count": 10
  },
  "tables": [
    {
      "page": 1,
      "headers": ["Item", "Status", "Notes"],
      "rows": [["1", "Pass", "No issues"]],
      "row_count": 1
    }
  ],
  "findings": [
    {
      "number": "1",
      "description": "Missing documentation for...",
      "type": "finding",
      "severity": "major"
    }
  ],
  "questions": [
    {
      "Element_ID": "4.2.2",
      "QID": "DCT-4.2.2-001",
      "Question_Number": "1",
      "Question_Text_Full": "Does the facility maintain proper documentation?",
      "Question_Text_Condensed": "Does the facility maintain proper documentation?",
      "Data_Collection_Guidance": "Review documentation logs and verify current status",
      "Reference_Raw": "14 CFR 121.369(b); 14 CFR 121.373; FAA Order 8900.1",
      "Reference_CFR_List": ["14 CFR 121.369(b)", "14 CFR 121.373"],
      "Reference_FAA_Guidance_List": ["FAA Order 8900.1"],
      "Reference_Other_List": [],
      "PDF_Page_Number": 5,
      "PDF_Element_Block_ID": "4.2.2-1",
      "Notes": []
    }
  ],
  "compliance": {
    "compliance_status": "needs_improvement",
    "total_findings": 3,
    "critical_findings": 0,
    "major_findings": 2,
    "minor_findings": 1,
    "compliance_percentage": 85
  },
  "raw_text_length": 15234,
  "parsed_at": "2024-01-20T10:30:00"
}
```

### Processing Flow

1. **Upload**: PDF is uploaded via `/api/upload` endpoint
2. **Storage**: File is saved to temporary storage
3. **Parsing**: `FAAPDFParser` processes the PDF:
   - Opens PDF with pdfplumber
   - Extracts text content
   - Runs extraction methods (metadata, tables, findings, questions, compliance)
   - Handles errors gracefully
4. **Storage**: Parsed data is stored in database
5. **Response**: Returns parsed data structure to client

### Error Handling

- Invalid PDF files are caught and logged
- Missing or malformed data fields return `None`
- Date parsing failures fall back to alternative formats
- Table extraction continues even if some pages fail

### Question Extraction Details

The question extraction system uses multiple strategies to ensure comprehensive coverage:

1. **Pattern-Based Extraction**: Uses regex patterns to identify:
   - `Q1:`, `Q2.`, `Q3)` formats
   - `Question 1:`, `Question 2:` formats
   - Numbered lists: `1.`, `2.`, `3.`
   - `Item 1:`, `Item 2:` formats

2. **Table-Based Extraction**: 
   - Automatically detects question columns in tables
   - Handles tables without explicit "Question" headers
   - Extracts answers from adjacent columns when available

3. **Standalone Questions**: 
   - Captures questions ending with `?` that weren't caught by numbered patterns
   - Useful for documents with informal question formats

4. **Multi-line Support**: 
   - Handles questions that span multiple lines
   - Cleans up whitespace and formatting

5. **Deduplication**: 
   - Prevents the same question from being captured multiple times
   - Uses fuzzy matching to identify duplicates

### Troubleshooting Missing Questions

If questions are not being found:

1. **Check the PDF format**: Ensure it's a text-based PDF (not scanned)
2. **Verify question format**: The parser looks for specific patterns - questions may need to match:
   - Numbered formats (Q1, Question 1, 1., Item 1)
   - Question marks at the end
   - Table structures with question columns

3. **Review extraction patterns**: You may need to add custom patterns for your specific document format

4. **Check table extraction**: Questions in tables require proper table structure detection

### Limitations

- Works best with text-based PDFs (not scanned images)
- Pattern matching may need adjustment for different document formats
- Complex layouts may require manual review
- OCR support not included (would require additional libraries like Tesseract)
- Questions without standard numbering or question marks may be missed
