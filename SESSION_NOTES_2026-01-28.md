# Session Notes - January 28, 2026
## FAA DCT Compliance Engine - Auto-Mapping Enhancements

---

## Session Overview
Enhanced auto-mapping to be more context-aware and to surface multiple manual references per question. Added manual parser quality reporting and a re-parse endpoint to avoid bad manual inputs.

---

## What Was Done

### 1) Auto-Mapping: Multiple Suggestions
- Auto-suggestions now return up to 4 sections per manual type instead of 1 (deterministic sort).

### 2) Manual Parser Quality & Re-parse
- Parser now strips repeated header/footer lines and emits a parse quality report (ok/warning/fail).
- Manual upload returns parse_report so low-quality manuals are flagged immediately.
- Added /api/manuals/{manual_id}/reparse to reprocess an existing manual without re-uploading.

### 3) Context-Aware Auto-Matching
- Question context now includes Reference_Raw/Other and cleaned Notes (noise removed).
- Reference context enrichment added for AC-39-9 and FAA Order 8900.1 Vol 3 Ch 59 Sec 1/3.
- Added phrase-level matching (e.g., 'AD management process', 'process measurement').
- Synonym expansion is now topic-aware (AD, inspection program, maintenance program, records, audit, safety).

### 4) Debug Rationale
- MAP API now supports ?debug=1 to return auto_suggestions_debug per row (scores + keyword/phrase hits).

---

## Verification
- New GMM Rev 4 parsed cleanly: 463 pages, 2349 sections, parse quality = ok.
- DCT 4.2.3 audit ID: d3037cf1-4e0e-42cd-9f5b-ad1dc28e4a2b
- QID 00049442 now surfaces GMM 6.4.12 (AD Process Measurement) in auto suggestions.

---

## Files Updated
- backend/manual_mapper.py
- backend/reference_context.py
- backend/manual_parser.py
- backend/app.py
- backend/database.py

---

## Next Steps
1) Expand topic trigger lists (user to provide terminology).
2) Wire in DRS.FAA.GOV references once access details are provided.
3) Optionally expose debug rationale in the frontend (MAP view toggle).
