# Troubleshooting Guide

## "Please upload a PDF file" Error

This error can occur for several reasons. Here's how to fix it:

### 1. Check File Extension

Make sure your file has a `.pdf` extension (case-insensitive):
- ✅ `document.pdf`
- ✅ `document.PDF`
- ✅ `document.Pdf`
- ❌ `document.pdf.txt` (hidden .txt extension)
- ❌ `document.doc`

**Fix**: Rename your file to have a `.pdf` extension.

### 2. Check Backend is Running

The error might be coming from the backend. Verify:

```bash
# Check if backend is running
curl http://localhost:5000/api/health

# Should return: {"status":"ok","timestamp":"..."}
```

**Fix**: Start the backend:
```bash
cd backend
python app.py
```

### 3. Check Browser Console

Open browser developer tools (F12) and check the Console tab for detailed error messages.

**Common console errors:**
- `Network error: Could not connect to server` → Backend not running
- `CORS error` → Backend CORS not configured (should be fixed)
- `Failed to fetch` → Network/connection issue

### 4. Verify File is Actually a PDF

Some files might have a `.pdf` extension but aren't actually PDFs:

```bash
# On macOS/Linux, check file type:
file your_document.pdf

# Should show: "PDF document, version ..."
```

**Fix**: Re-save or re-export your file as a proper PDF.

### 5. Check File Size

Files larger than 50MB will be rejected.

**Fix**: Compress the PDF or split it into smaller files.

### 6. Clear Browser Cache

Sometimes cached JavaScript can cause issues:

1. Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
2. Or clear browser cache and reload

### 7. Check File Input

Make sure you're selecting a file through the file picker, not dragging and dropping (drag-drop not yet implemented).

## Debug Steps

1. **Open Browser Console** (F12 → Console tab)
2. **Try uploading a file**
3. **Check console for errors**
4. **Check Network tab** to see the API request/response

## Common Issues

### Backend Not Running
```
Error: Network error: Could not connect to server
```
**Solution**: Start backend with `python app.py` in the backend directory

### File Too Large
```
Error: File size exceeds 50MB limit
```
**Solution**: Compress PDF or increase `MAX_FILE_SIZE` in `backend/app.py`

### Invalid File Type
```
Error: Invalid file type. Only PDF files are allowed.
```
**Solution**: Ensure file has `.pdf` extension and is a valid PDF

### Upload Directory Permissions
```
Error: Failed to save file
```
**Solution**: Ensure `backend/uploads/` directory exists and is writable:
```bash
cd backend
mkdir -p uploads
chmod 755 uploads
```

## Still Having Issues?

1. Check backend logs for detailed error messages
2. Check browser console for frontend errors
3. Verify file is a valid PDF: `file your_file.pdf`
4. Try with a known-good PDF file first
5. Check that both frontend (port 3000) and backend (port 5000) are running

## Manual Parsing Quality Warnings

If a manual upload returns a `parse_report` with `quality = warning` or `fail`,
the auto-mapping suggestions may be unreliable.

**What to look for in `parse_report`:**
- `quality`: `ok` | `warning` | `fail`
- `warnings`: List of issues (e.g., "Text extraction is very low")
- `metrics`: Page count, section count, avg section length

**Fix**: Upload a cleaner PDF or reprocess the manual after improving the source.

## Re-Parse an Existing Manual (No Re-Upload)

Use the re-parse endpoint to rebuild sections after parser improvements or
after replacing the manual file on disk:

```bash
curl -X POST http://localhost:5000/api/manuals/<manual_id>/reparse
```

## MAP Debug Rationale

To see why a manual reference was suggested, request MAP data with debug enabled:

```bash
http://localhost:5000/api/audits/<audit_id>/map?debug=1
```

Each row includes `auto_suggestions_debug` with scores and keyword/phrase hits.

---

## Synology NAS Deployment Issues

### 504 Gateway Timeout on PDF Upload

**Symptom:** Uploading a PDF (DCT or GMM) fails with "504 Gateway Timeout" or "Upload failed" error.

**Cause:** The nginx proxy timeout is shorter than the time needed for the backend to process the PDF. This is common on Synology NAS devices (like DS220+) because:
- The Celeron CPU is slower than desktop/laptop CPUs
- Embedding generation (sentence-transformers/PyTorch) is CPU-intensive
- Large PDFs take longer to parse and process

**Fix:** Increase the nginx proxy timeout in `frontend/nginx.conf`:

```nginx
location /api {
    # ... other settings ...

    # Increase these values (in seconds)
    proxy_connect_timeout 60s;
    proxy_send_timeout 600s;    # 10 minutes
    proxy_read_timeout 600s;    # 10 minutes
}
```

After editing, rebuild the frontend container:
1. In Container Manager, stop the project
2. Delete the `faa-audit-frontend` image (under Images)
3. Rebuild and start the project

If 10 minutes isn't enough for very large PDFs, increase to `1800s` (30 minutes).

### Manual Upload Hangs or Returns 499 (Client Closed)

**Symptom:** Uploading a GMM/AIP manual hangs in the UI. Nginx logs show 499 for `/api/manuals/upload`.

**Cause:** The manual parser can hang during text extraction on certain PDFs when using `pdfplumber`.

**Fix:** Use PyMuPDF for manual parsing and rebuild the backend image.
1. Update backend dependencies to include PyMuPDF:
   - `backend/requirements.txt`: add `PyMuPDF>=1.24.0`
2. Update manual parser to use PyMuPDF when available.
3. Rebuild the backend image and restart the project.

If the upload still hangs, test parsing inside the backend container and capture logs:
```bash
curl -i http://127.0.0.1:8888/api/health
```

Then re-try the upload and check backend logs for manual parsing activity.

### Container Build Uses Cached Layers

**Symptom:** Changes to `nginx.conf` or other files don't take effect after rebuild.

**Cause:** Docker caches build layers. If the file hasn't changed in a way Docker detects, it uses the cached version.

**Fix:** Force a clean rebuild:
1. Stop the project in Container Manager
2. Go to **Image** and delete both `faa-audit-backend` and `faa-audit-frontend` images
3. Recreate the project from scratch

### Data Folder Permission Issues

**Symptom:** "Bind mount failed" error when creating the project.

**Cause:** The data directories don't exist on the NAS.

**Fix:** Create the required folders in File Station:
```
/volume1/audit-app/data/
/volume1/audit-app/data/uploads/
/volume1/audit-app/data/manuals/
/volume1/audit-app/data/db/
```

### Container Won't Start - Port Already in Use

**Symptom:** Frontend container fails to start with port conflict error.

**Cause:** Port 8888 is already used by another service.

**Fix:** Change the port in `compose.yaml`:
```yaml
ports:
  - "9999:80"  # Change 8888 to another port
```

Then access the app at `http://your-nas-ip:9999` instead.

---

## MAP Generation Errors

### 500 Internal Server Error on /api/audits/<id>/map

**Symptom:** Clicking to view the MAP or accessing the map endpoint returns a 500 error.

**Possible Causes:**
1. No manuals uploaded (GMM/AIP required for mapping)
2. Embedding service failed to initialize (sentence-transformers not installed)
3. Database schema mismatch (missing `pinned_manual_ids` column)
4. Audit record doesn't exist or has no ownership assignments

**Diagnosis:**
Check the backend logs for detailed error messages. The MAP endpoint now logs:
- `Building MAP rows for audit <id>` - Start of generation
- `Loaded manual sections: ['AIP', 'GMM']` - Which manuals are available
- `Failed to load manual sections: <error>` - If manual loading fails

**Fix by cause:**

1. **No manuals uploaded:**
   ```bash
   # Check if manuals exist
   curl http://localhost:5000/api/manuals
   ```
   Upload GMM and/or AIP manuals before generating MAP.

2. **Embedding service not available:**
   ```bash
   # Install sentence-transformers
   pip install sentence-transformers
   ```
   Or disable semantic matching: `/api/audits/<id>/map?semantic=false`

3. **Database schema issue:**
   ```bash
   # The backend auto-migrates on startup, but you can force it:
   # Delete data/faa_audit.db and restart (WARNING: loses all data)
   ```

4. **Missing ownership assignments:**
   Run ownership assignment first:
   ```bash
   curl -X POST http://localhost:5000/api/audits/<id>/ownership
   ```

### Container Manager Project Shows Red Status

**Symptom:** The audit-app project in Container Manager shows a red status indicator, but both containers (frontend and backend) are running and the app is functional.

**Cause:** Container Manager may cache a previous failed state, or flag stderr output from containers as errors. The Werkzeug dev server warning was one known trigger (now fixed by switching to gunicorn).

**Diagnosis:**
```bash
# Verify the app is actually working
curl http://your-nas-ip:8888/api/health
# Should return: {"status":"ok","timestamp":"..."}
```

**Fix:**
1. If health check passes, the red status is cosmetic
2. Try stopping and starting the project (not rebuild)
3. If that doesn't clear it, delete the project entirely in Container Manager and recreate it from `compose.yaml`

### 404 Error on /api/audits/<id>

**Symptom:** Repeated 404 errors in browser console for audit endpoints.

**Cause:** The frontend is holding a stale audit ID that no longer exists in the database.

**Fix:**
1. Refresh the browser page (hard refresh: Cmd+Shift+R or Ctrl+Shift+R)
2. Clear browser local storage for the site
3. Navigate back to the audit list and select a valid audit

---

## MAP Mapping Quality

### Mapping Reported as Failed or Incomplete

**Symptom:** After uploading a manual (GMM/AIP), the MAP generation runs but results are incomplete, low quality, or reported as failed.

**Status:** Known issue — mapping logic needs improvement. Areas to investigate:
- `map_builder.py` — MAP row generation and scoring logic
- `manual_mapper.py` — manual-to-DCT matching algorithms
- Keyword matching thresholds may be too strict or too loose
- Semantic scoring (sentence-transformers embeddings) may need tuning
- Manual section parsing may be splitting sections in suboptimal ways

**Workaround:** Use the debug endpoint to see why matches are being made:
```bash
curl http://your-nas-ip:8888/api/audits/<audit_id>/map?debug=1
```
Each row includes `auto_suggestions_debug` with scores and keyword/phrase hits.

**To be addressed in a future session.**

---

## Session Log: 2026-02-07

### Issue: MAP Mapping Incorrect for QID 00004724

**Problem:** For QID 00004724 (AD Management), the application mapped:
- `6.4(b)` - should be `6.4.1(b)`
- `5.2(f)`, `5.2(i)`, `14.13(i)` - incorrectly matched (these are MEL/transponder sections, not AD-related)

**Root Cause Analysis:**

1. **Section Number Parsing Too Coarse** (`manual_parser.py:20-24`)
   - The parser captures section `6.4` but subsection `6.4.1` may not be detected as a separate section
   - Paragraph `(b)` gets attributed to `6.4` instead of `6.4.1`

2. **Keyword Matching Too Broad** (`manual_mapper.py:76-110`)
   - Sections `5.2(f)`, `5.2(i)`, `14.13(i)` match because they share generic keywords like "operate", "compliance", "equipment"
   - These sections are about MEL/transponders, NOT Airworthiness Directives
   - No topic exclusion logic exists to filter out unrelated content

3. **No Topic-Based Filtering**
   - If a question is about "AD Management", sections about "MEL", "transponder", "deferred items" should be penalized or excluded
   - Current logic only looks for positive matches, not negative/exclusion signals

**Fixes Implemented:**

1. **Improved section hierarchy parsing** (`manual_parser.py`)
   - Added pattern to detect section numbers alone on a line (e.g., "6.4.1" without title)
   - Added `_extract_inline_subsections()` function to detect subsections embedded within parent section text
   - Subsections like 6.4.1, 6.4.2 within section 6.4 are now extracted as separate sections

2. **Added topic exclusion rules** (`manual_mapper.py`)
   - New `TOPIC_EXCLUSIONS` dictionary defines which topics should NOT match
   - When question is about "ad management", sections about "mel", "transponder", "moc" are penalized (-8.0 score)
   - Added `_detect_question_topics()` to identify what a question is about
   - Added `_section_matches_excluded_topic()` to check if section contains excluded content
   - Exclusions are logged in `match_signals["excluded_topics"]` for debugging

3. **Strengthened AD Management phrase matching** (`manual_mapper.py`)
   - Increased weights for AD-specific phrases:
     - "airworthiness directives/directive": 3.0 → 5.0
     - "ad management": 3.0 → 5.0
     - "ad management process": 3.5 → 6.0
   - Added new AD-specific phrases: "ad compliance", "ad tracking", "ad status", "ad applicability", "recurring ad", "one-time ad", "terminating action", "amoc"

4. **Added title bonus scoring** (`manual_mapper.py`)
   - New `TITLE_TOPIC_BONUS` dictionary boosts sections whose title matches the question topic
   - When section title contains "airworthiness directive" and question is about AD management: +4.0 score
   - Helps prioritize section 6.4.1 "AD Management Process" over generic sections

5. **Fixed revision history pollution** (`manual_parser.py`)
   - Added `_is_revision_history_line()` to detect revision log entries
   - Lines starting with "Revised", "Added", "Deleted" or containing "=to=" are skipped
   - Prevents revision history entries from being parsed as section headings
   - Reduced spurious section count from 2353 to 2275

**Status:** Implemented and tested locally

**Test Results (simulated QID 00004724 - AD Management):**
```
Top matches after fixes:
  Score 26.30 | 6.4.12(a) - AD Process Measurement
  Score 23.00 | 6.4.1(b)  - General (correct match!)
  Score 14.00 | 6.4.1(a)  - General

MEL sections correctly penalized:
  Score 14.00 | 5.2.1(f)  - [EXCLUDED] penalty applied
  Score  2.00 | 5.2.1(a)  - [EXCLUDED]
  Score -1.00 | 5.2.13.3  - [EXCLUDED]
```

**Key improvements:**
- 6.4.1(b) now correctly identified (was 6.4(b) before)
- MEL sections (5.2.x) receive -8.0 penalty for AD questions
- Subsection detection working (6.4.1 detected as separate from 6.4)

**To apply changes on NAS:**
1. Rebuild Docker containers to pick up code changes
2. Re-parse the GMM manual
3. Regenerate MAP for the audit

```bash
# After rebuilding containers:

# Re-parse existing manual
curl -X POST http://your-nas-ip:8888/api/manuals/<manual_id>/reparse

# Regenerate MAP with debug info
curl "http://your-nas-ip:8888/api/audits/<audit_id>/map?debug=1"
```
