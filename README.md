# FAA DCT Audit Application

A web application for uploading, parsing, and analyzing FAA Data Collection Tool (DCT) audit documents.

## Features

- 📄 **PDF Upload**: Upload FAA DCT PDF documents
- 🔍 **Automatic Parsing**: Extract structured data including:
  - Element IDs (e.g., 4.2.2)
  - Question IDs (QID)
  - Question text and guidance
  - CFR references
  - FAA Guidance references
  - Compliance data
- 📊 **Data Management**: View, search, and manage audit records
- 🎨 **Modern UI**: Clean, responsive interface

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+ and npm

### Setup

1. **Clone/Navigate to the project**
   ```bash
   cd faa-audit
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd ../frontend
   npm install
   ```

### Running the Application

**Terminal 1 - Start Backend:**
```bash
cd backend
python app.py
```
Backend will run on http://localhost:5000

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```
Frontend will run on http://localhost:3000

### Usage

1. Open http://localhost:3000 in your browser
2. Click "Choose PDF File" to upload a DCT PDF
3. Wait for processing (parsing happens automatically)
4. Note: QID counts vary by DCT edition/version; completeness is validated against the uploaded file
5. View extracted questions and data in the interface

## Project Structure

```
faa-audit/
├── backend/
│   ├── app.py              # Flask API server
│   ├── pdf_parser.py       # PDF parsing logic
│   ├── requirements.txt    # Python dependencies
│   └── uploads/            # Uploaded PDF files (created automatically)
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React component
│   │   ├── services/
│   │   │   └── api.js      # API service
│   │   └── App.css         # Styles
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
└── README.md
```

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/upload` - Upload PDF file
- `GET /api/audits` - List all audits
- `GET /api/audits/:id` - Get specific audit
- `PUT /api/audits/:id` - Update audit
- `DELETE /api/audits/:id` - Delete audit
- `GET /api/audits/search` - Search audits
- `GET /api/export` - Export data

## Testing

See `backend/README_TESTING.md` for detailed testing instructions.

Quick test:
```bash
cd backend
python test_parser.py path/to/your/file.pdf
```

## Development

### Backend Development
- Uses Flask for the API
- PDF parsing with pdfplumber
- In-memory storage (replace with database for production)

### Frontend Development
- React with Vite
- Modern ES6+ JavaScript
- Responsive CSS

## License

[Your License Here]
