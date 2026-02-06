# Session Notes - February 6, 2026
## Synology NAS Deployment - Manual Upload Hang

---

## Session Overview
Investigated manual (GMM) upload failures and hangs on Synology NAS deployment. Identified manual parsing hang inside the backend container and implemented a parser change to use PyMuPDF for manual text extraction.

---

## Issue Diagnosed

### Symptoms
- Manual (GMM) uploads hang in the UI and eventually fail.
- Frontend nginx logs show 499 responses for `/api/manuals/upload` (client closed).
- Backend logs show repeated 400 responses for `/api/manuals/upload` earlier, then hangs when parsing.
- Direct parse inside backend container hangs on the GMM PDF.

### Root Cause
`pdfplumber` hangs on the specific GMM PDF during text extraction inside `manual_parser.py`. This stalls the request until the client gives up.

---

## What Was Done

### 1) Parser Change for Manuals
- Switched manual parsing to use PyMuPDF (fitz) when available.
- Retained pdfplumber as a fallback if PyMuPDF is not installed.

### 2) Dependency Update
- Added PyMuPDF to backend requirements so it is installed in the backend image.

---

## Files Updated
- `backend/manual_parser.py`
- `backend/requirements.txt`

---

## Status / Next Steps
1) Pull latest changes on the NAS (`git pull`).
2) Rebuild backend image using `/volume1/audit-app/compose.yaml`.
3) Re-test manual (GMM) upload and mapping.
4) Mapping still reported as failed after manual upload; to be troubleshot in the next session.

