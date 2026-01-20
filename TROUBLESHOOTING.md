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
