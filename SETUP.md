# Setup Guide - FAA DCT Audit Application

## Quick Setup (Recommended)

### Option 1: Use the startup script (macOS/Linux)

```bash
./start.sh
```

This will:
- Check dependencies
- Install Python packages
- Install Node.js packages
- Start both backend and frontend servers

### Option 2: Manual Setup

#### Step 1: Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

#### Step 3: Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # If using venv
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **API Health Check**: http://localhost:5000/api/health

## First Time Setup Checklist

- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] Node.js 16+ installed (`node --version`)
- [ ] npm installed (`npm --version`)
- [ ] Backend dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] Frontend dependencies installed (`npm install` in frontend directory)
- [ ] Backend server running on port 5000
- [ ] Frontend server running on port 3000

## Testing the Parser

Before using the web interface, you can test the parser directly:

```bash
cd backend
python test_parser.py /path/to/your/dct.pdf
```

## Troubleshooting

### Port Already in Use

If port 5000 or 3000 is already in use:

**Backend**: Edit `backend/app.py` and change `port=5000` to another port
**Frontend**: Edit `frontend/vite.config.js` and change `port: 3000` to another port

### Python Import Errors

```bash
cd backend
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Node Module Errors

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### PDF Upload Fails

1. Check file size (max 50MB)
2. Ensure file is a PDF
3. Check backend logs for errors
4. Verify `backend/uploads/` directory exists and is writable

## Next Steps

1. Upload a DCT PDF file through the web interface
2. Note: QID counts vary by DCT edition/version; completeness is validated against the uploaded DCT
3. View extracted questions and data
4. Review the parsed JSON output
5. Test with different PDF formats

## Development Workflow (Two-Machine Setup)

This project is developed on two machines with the app deployed on a Synology NAS:

| Machine | Location | Access to NAS | Git Repo |
|---------|----------|---------------|----------|
| iMac | Home | SMB mount at `/Volumes/audit-app` | `~/FAA-Audit` |
| Work PC | Office | SSH via Tailscale (`schonn.underwood@100.126.188.60`) | `~/FAA-Audit` |
| NAS | Synology DS220+ | — | **No git** (deploy target only) |

**GitHub repo:** `https://github.com/schonn0129/FAA-Audit.git`

### Important: Never run git on the NAS
The NAS is mounted via SMB which does not support git's file locking. All git operations must happen on local disk (`~/FAA-Audit`).

### First-Time Setup (either machine)
```bash
git clone https://github.com/schonn0129/FAA-Audit.git ~/FAA-Audit
cd ~/FAA-Audit
chmod +x deploy-to-nas.sh deploy-from-work.sh
```

### Deploy from iMac (home)
```bash
cd ~/FAA-Audit
git pull                       # get latest from GitHub
./deploy-to-nas.sh             # dry-run — preview changes
./deploy-to-nas.sh --go        # sync code to NAS over SMB
```

### Deploy from Work PC
```bash
cd ~/FAA-Audit
git pull                       # get latest from GitHub
./deploy-from-work.sh          # dry-run — preview changes
./deploy-from-work.sh --go     # sync code to NAS over SSH/Tailscale
```

### After deploying, rebuild containers
1. Open Container Manager on the NAS (via browser or QuickConnect)
2. Stop the project
3. Delete old images (`faa-audit-backend`, `faa-audit-frontend`)
4. Rebuild and start the project

### What the deploy scripts protect
- `data/` directory is **never overwritten** (database, uploads, manuals stay on NAS)
- `.git/`, `node_modules/`, `__pycache__/`, `.env` are excluded

## Development Notes

- Backend uses Flask with CORS enabled
- Frontend uses React with Vite
- PDF parsing uses PyMuPDF (with pdfplumber fallback)
- Data is stored in SQLite (`data/db/faa_audit.db`) on the NAS
- Docker deployment via `compose.yaml` on Synology Container Manager
