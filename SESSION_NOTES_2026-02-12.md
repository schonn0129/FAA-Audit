# Session Notes - February 12, 2026
## MAP Intent-First Matching Tuning (Cross-DCT)

---

## Session Overview
Focused on improving mapping quality using an intent-first approach that works across DCT domains (not just AD management). The target behavior is:

1. Read question
2. Determine intent/topic
3. Read manual content
4. Return chapter/section/subsection where intent is met

Work included scoring refactor, candidate filtering, validation on live API, and operational troubleshooting updates.

---

## Goals
- Reduce noisy MAP links
- Improve precision on top suggestion
- Prevent DCT 4.2.3-specific overfitting
- Preserve defensible deterministic behavior with optional semantic blending

---

## Code Changes

### 1) `backend/map_builder.py`
- Updated manual metadata reporting in MAP payload:
  - Replaced "latest by type" banner behavior with exact manual IDs used during scoring.
  - `manuals_used` now matches pinned/loaded mapping inputs.

### 2) `backend/manual_mapper.py`
- Removed duplicate `aircraft records` synonym key overwrite.
- Added/expanded intent detection patterns:
  - `provisioning`, `distribution`, `responsibility`, `method`, `data_control`, `standards`, `measurement`, `records`, `execution`, `identification`
- Added section-side intent detection and intent/topic overlap scoring.
- Tightened topic trigger matching to boundary-aware matching.
- Increased exclusion penalties for mismatched topics.
- Added selection-stage filtering:
  - Keep anchor result
  - Keep follow-on only when close in score or strongly evidenced
  - De-duplicate subsection variants
- Fixed semantic-path cap behavior so max suggestions are respected.
- Added generic chapter-number penalty for broad section matches with weak evidence.

---

## Validation Performed

### Live API checks
- Endpoint: `GET /api/audits/<id>/map?debug=1&semantic=true`
- Spot checks:
  - `QID 00049439` (4.2.3): moved to expected `6.4.3` anchor behavior.
  - `QID 00004334` (4.2.1): reduced from noisy multi-link output to single top reference `3.1.1(c)`.

### 4.2.1 sample review
- Sampled first 10 QIDs from audit `b538aa7c-19c2-48e8-b883-36789ebd7c4a`.
- Observed reduced noise and stronger intent signaling on several rows.
- Remaining work: improve subsection precision for some CAMP/data-control/method cases.

---

## Operational Issue Found

### Backend container health status false-negative
- Container state showed `unhealthy` even while API worked.
- Root cause: healthcheck uses `curl`, but image does not include `curl`.
- Added troubleshooting guidance to `TROUBLESHOOTING.md`.

---

## Current Status
- Backend and mapping logic updated and rebuilt.
- MAP precision improved on key validation QIDs.
- Additional tuning still needed for broad 4.2.1 coverage consistency.

---

## Next Steps
1. Build a scored regression set for 4.2.1 + 4.2.3 (top-1/top-3 correctness).
2. Add intent-specific penalties/bonuses for remaining failure classes:
   - CAMP procedural control
   - Data documentation/substantiation
   - Method-of-performance questions
3. Add an optional debug export endpoint/report for rapid human review of candidate ranking.
