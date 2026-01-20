# Testing the PDF Parser Locally

This guide explains how to test the PDF parser on your local machine.

## Prerequisites

1. **Python 3.8+** installed
2. **Virtual environment** (recommended)

## Setup

### 1. Navigate to the backend directory

```bash
cd backend
```

### 2. Create a virtual environment (recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `pdfplumber` - PDF parsing library
- `Flask` - Web framework (if testing via API)
- `Flask-CORS` - CORS support
- `python-dateutil` - Date parsing utilities

## Testing Methods

### Method 1: Command Line Test Script (Recommended)

Use the provided test script:

```bash
python test_parser.py <path_to_your_pdf>
```

**Example:**
```bash
# Test with a PDF file
python test_parser.py ../test_documents/sample_dct.pdf

# Run in debug mode to see what patterns are detected
python test_parser.py ../test_documents/sample_dct.pdf --debug
```

The script will:
- Parse the PDF
- Display a summary of extracted data
- Show the first 10 questions found
- Save full output to a JSON file (`<filename>_parsed.json`)

### Method 2: Python Interactive Shell

```python
from pdf_parser import parse_pdf, FAAPDFParser

# Simple usage
parsed_data = parse_pdf("path/to/your/file.pdf")

# Print questions
for q in parsed_data['questions']:
    print(f"Element {q['Element_ID']}: {q['Question_Text_Full']}")

# Advanced usage with context manager
with FAAPDFParser("path/to/your/file.pdf") as parser:
    questions = parser.extract_questions()
    metadata = parser.extract_metadata()
    tables = parser.extract_tables()
```

### Method 3: Test via Flask API (if implemented)

If you have a Flask app running:

```bash
# Start the Flask server
python app.py

# In another terminal, test the upload endpoint
curl -X POST http://localhost:5000/api/upload \
  -F "file=@path/to/your/file.pdf"
```

## Expected Output

The parser extracts the following fields for each question:

- `Element_ID` - e.g., "4.2.2"
- `QID` - DCT Question ID
- `Question_Number` - Numbered questions within element
- `Question_Text_Full` - Full question text
- `Question_Text_Condensed` - Short label
- `Data_Collection_Guidance` - Guidance text
- `Reference_Raw` - Raw reference string
- `Reference_CFR_List` - Parsed CFR citations
- `Reference_FAA_Guidance_List` - FAA Orders, ACs, etc.
- `Reference_Other_List` - Other references
- `PDF_Page_Number` - Page number
- `PDF_Element_Block_ID` - Element block ID
- `Notes` - Parsing notes/issues

## Troubleshooting

### Import Errors

If you get import errors:
```bash
# Make sure you're in the backend directory
cd backend

# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### PDF Not Parsing Correctly

1. **Check if PDF is text-based** (not scanned image):
   ```python
   # Try extracting text manually
   import pdfplumber
   with pdfplumber.open("your_file.pdf") as pdf:
       print(pdf.pages[0].extract_text())
   ```

2. **Run in debug mode** to see what patterns are detected:
   ```bash
   python test_parser.py your_file.pdf --debug
   ```

3. **Check the JSON output** file (`<filename>_parsed.json`) to see what was extracted

### Questions Not Found

If questions aren't being extracted:

1. Check if the PDF uses tables (DCT format typically uses tables)
2. Verify the table headers match expected patterns
3. Check the `Notes` field in extracted questions for parsing issues
4. Run debug mode to see what patterns are detected

### Missing Dependencies

If you get errors about missing modules:
```bash
pip install pdfplumber python-dateutil
```

## Example Test Workflow

```bash
# 1. Setup (one time)
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Test with your PDF
python test_parser.py ../path/to/your/dct.pdf

# 3. Check the output JSON file
cat ../path/to/your/dct_parsed.json | python -m json.tool | less

# 4. If issues, run debug mode
python test_parser.py ../path/to/your/dct.pdf --debug
```

## Next Steps

- Review the extracted data in the JSON output file
- Check if all required fields are populated
- Verify question text accuracy
- Check reference parsing
- Report any missing questions or parsing issues
