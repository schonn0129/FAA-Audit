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
1) ~~Pull latest changes on the NAS (`git pull`).~~ — Replaced by deploy script (see below).
2) Rebuild backend image using `/volume1/audit-app/compose.yaml`.
3) Re-test manual (GMM) upload and mapping.
4) Mapping still reported as failed after manual upload; to be troubleshot in the next session.

---

## Evening Session — Git Workflow Fix

### Problem
Git operations on the NAS (`/Volumes/audit-app`) were completely broken:
- `git pull`, `git reset`, `git checkout` all failed with bus errors and lock file conflicts
- **Root cause:** The NAS is mounted via SMB (Samba), which does not support the POSIX file locking that git requires
- Codex had earlier attempted to retrofit a `.git` repo onto the NAS share, which left it in a corrupted state
- VS Code's built-in git extension kept spawning `git status` against the SMB mount, constantly recreating lock files

### What Was Done

#### 1) Fresh local clone
- Cloned the GitHub repo to the iMac's local disk: `~/FAA-Audit`
- This is now the **only** place git operations happen on the iMac

#### 2) Removed broken `.git` from the NAS
- Deleted `/Volumes/audit-app/.git` (required `sudo` due to SMB permission restrictions)
- The NAS copy is now a **deployment target only** — no git repo

#### 3) Created deploy scripts
- **`deploy-to-nas.sh`** (iMac) — rsyncs `~/FAA-Audit/` → `/Volumes/audit-app/` over SMB
  - Excludes `data/` (preserves database, uploads, manuals on NAS)
  - Excludes `.git/`, `node_modules/`, `__pycache__/`, `.env`
  - Dry-run by default, `--go` flag to apply
- **`deploy-from-work.sh`** (Work PC) — pulls from GitHub, then rsyncs to NAS over SSH/Tailscale
  - Connects to NAS at `schonn.underwood@100.126.188.60`
  - Same exclusion rules

#### 4) Initial deploy completed
- Ran `deploy-to-nas.sh --go` — all code files synced to NAS
- Verified: no `.git` on NAS, database/manuals/uploads preserved, backend files match

### New Workflow

**From iMac (home):**
```bash
cd ~/FAA-Audit
# edit, commit, push to GitHub
git add . && git commit -m "message" && git push
# deploy to NAS
./deploy-to-nas.sh --go
```

**From Work PC:**
```bash
cd ~/FAA-Audit
# pull latest, deploy to NAS over Tailscale
git pull
./deploy-from-work.sh --go
```

### Files Created
- `deploy-to-nas.sh` — iMac deploy script (rsync over SMB)
- `deploy-from-work.sh` — Work PC deploy script (rsync over SSH/Tailscale)

### Key Rule
**Never run git on the NAS volume.** All git operations happen on local disk (`~/FAA-Audit`). The NAS is a deploy target only.

