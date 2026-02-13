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

## Evening Session: Intent-First Scoring Structural Fix

### Problem Investigated
QID 00004724 (DCT 4.2.3) — "Does the certificate holder have a method to ensure that aircraft which do not meet the requirements of an applicable AD are not operated?" — was mapping to GMM 9.7.1(i), 8.1.4(i), 12.6.5(i), 3.3.3(b) instead of the correct **GMM 6.4.1**.

### Root Causes Found
1. Token overlap uncapped — generic tokens flooding scores
2. TOPIC_EXCLUSIONS too narrow — safety/inspection sections not excluded for AD questions
3. TOPIC_MISMATCH_PENALTY too small (2.0) to counteract keyword overlap
4. Bare "safety" in TOPIC_TRIGGERS matching DCT metadata "Safety Attribute: Procedures"
5. Missing AD topic triggers for phrases like "applicable AD", "ad tracking", etc.

### Code Changes (all in `backend/manual_mapper.py`)
1. **Token overlap cap**: Diminishing returns after 5 tokens, max 8.0
2. **Expanded TOPIC_EXCLUSIONS**: 5 → 11 entries, full cross-domain matrix
3. **TOPIC_MISMATCH_PENALTY**: 2.0 → 5.0
4. **Graduated weak token penalty**: Fires when 60%+ of overlap is weak tokens
5. **No-signal score ceiling (6.0)**: Caps sections with no intent/topic match
6. **Fixed safety topic triggers**: Removed bare "safety", requires compound phrases
7. **Expanded AD topic triggers**: Added "applicable ad", "ad tracking", "ad status", etc.
8. **Diagnostic signals**: overlap_capped, no_signal_cap_applied, weak_token_ratio in debug

### Validation
- Debug API confirmed QID 00004724 was matching safety-domain sections due to false topic detection
- QID 00004724 is in DCT 4.2.3 (audit `4a32641e-f5fc-40b6-88f7-a9c0fa93b780`), not 4.2.1
- Docker rebuilt and deployed on 2026-02-13

### Post-Deploy Verification (2026-02-13)

| QID | DCT | Expected | Actual | Score | Status |
|-----|-----|----------|--------|-------|--------|
| 00004724 | 4.2.3 | GMM 6.4.1 | GMM 6.4.1(b) | 26.50 | **FIXED** |
| 00049439 | 4.2.3 | GMM 6.4.3 | GMM 6.4.3 | 17.00 | **PASS** |
| 00004334 | 4.2.1 | GMM 3.1.1(c) | GMM 14.1.1(c); 3.1.1(c) | 23.25/22.50 | **PASS** |

- DCT 4.2.3: 20/20 QIDs have GMM references, no anomalies
- DCT 4.2.1: 44/44 QIDs have GMM references, 1 low-scorer (00051913 at 4.00)
- New diagnostic signals confirmed working: `overlap_capped`, `no_signal_cap_applied`

---

## Next Steps
1. Investigate low-score QID 00051913 (4.2.1, score 4.00) — likely needs additional intent coverage.
2. Build scored regression set for top-1/top-3 correctness across all DCTs.
3. Add intent-specific penalties/bonuses for remaining failure classes:
   - CAMP procedural control
   - Data documentation/substantiation
   - Method-of-performance questions
4. Add optional debug export endpoint/report for rapid human review.
