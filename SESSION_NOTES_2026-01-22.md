# Session Notes - January 22, 2026
## FAA DCT Compliance Engine - Phase 2: Ownership Assignment Logic

---

## Session Overview

This session focused on initiating **Phase 2: Ownership Assignment Logic** for the FAA DCT Compliance Engine. We established the complete project scope, created a detailed implementation plan, and completed the first milestone (database models and migration).

---

## Key Accomplishments

### 1. Project Scope Documentation
✅ Created and committed [PROJECT_SCOPE.md](PROJECT_SCOPE.md) documenting the full 6-phase workflow:
- **Phase 1**: DCT Ingestion & Validation (COMPLETE)
- **Phase 2**: Ownership Assignment Logic (IN PROGRESS)
- **Phase 3**: Audit Scoping with Full Accountability
- **Phase 4**: MAP Construction
- **Phase 5**: Dashboard & Risk Visualization
- **Phase 6**: PDF Assembly

**Core Philosophy**: This is a **deterministic compliance engine**, not AI. Every decision must be traceable, repeatable, and defensible under PMI scrutiny.

### 2. Phase 2 Requirements Clarified

**The 7 Authorized Functions** (no others allowed):
1. Maintenance Planning (MP)
2. Maintenance Operations Center (MOC)
3. Director of Maintenance (DOM)
4. Aircraft Records
5. Quality
6. Training
7. Safety

**Assignment Logic Must Use**:
- **Keyword Analysis**: inspect/inspection → Aircraft Records; control/dispatch → MOC; program/task card → MP
- **Regulatory Context**: 14 CFR 121.369 → MP; 14 CFR 121.379 → MOC; 14 CFR 135.427 → DOM
- **AIP/GMM Cross-Reference**: Which manual section addresses this requirement?
- **Operational Reality**: Who actually executes this in practice?

**Each Assignment Needs**:
- Primary owner (single point of accountability)
- Supporting functions (coordinating roles)
- Rationale statement (citing DCT language + manual reference)
- Confidence score (High/Medium/Low)

**Critical User Requirement Added**:
> "The initial mapping needs to be done by the tool. It must read the uploaded company manuals and from that content make a determination if it can be linked or not."

This means:
- Tool must parse AIP/GMM PDFs
- Extract sections and CFR citations automatically
- Cross-reference DCT questions to manual sections
- Intelligent CFR-to-Manual linkage discovery

### 3. User Decisions Made

**Q: When should ownership assignment happen?**
✅ **Automatically on PDF upload** (can review/override afterwards)

**Q: Do you have CFR-to-Manual mappings documented?**
✅ **Tool must create mappings** by parsing uploaded company manuals (AIP/GMM)

**Q: Include admin UI for managing rules?**
✅ **Yes, include basic admin UI in Phase 2** for managing keyword patterns and CFR mappings

---

## Implementation Plan Created

Created comprehensive plan at: [.claude/plans/squishy-prancing-candle.md](.claude/plans/squishy-prancing-candle.md)

**6-Week Timeline**:
- **Week 1**: Database & Manual Parser ← WE ARE HERE
- **Week 2**: Cross-Reference & Assignment Engine Core
- **Week 3**: API Endpoints & Database Operations
- **Week 4**: Frontend - Core Components (Manual Upload, Dashboard)
- **Week 5**: Frontend - Table & Editor
- **Week 6**: Admin UI & Testing

**Architecture Overview**:
```
DCT PDF Upload → Parser extracts questions with CFR references
Company Manuals Upload → Parser extracts sections + CFR citations
Cross-Reference Engine → Links questions to manual sections
Ownership Engine → Analyzes signals and assigns functions
   ├── Keyword Analyzer (question text)
   ├── CFR Analyzer (regulatory citations)
   ├── Manual Reference Analyzer (linked sections)
   └── Confidence Calculator (weighted scoring)
Output → Assignment + Rationale + Confidence Score
User Review → Dashboard shows assignments, flags low-confidence
Manual Override → User can adjust with justification
Export → Complete ownership table for PMI review
```

---

## Code Implementation Completed (Week 1, Day 1-2)

### Database Models Added

Modified [backend/models.py](backend/models.py) to add 4 new models:

#### 1. **Manual**
Stores uploaded company manuals (AIP/GMM).
- `id`, `filename`, `manual_type` (AIP/GMM), `upload_date`, `version`, `page_count`, `status`
- Relationship: `sections` (one-to-many with ManualSection)

#### 2. **ManualSection**
Extracted sections from company manuals.
- `section_number`, `section_title`, `section_text`, `page_number`
- `cfr_citations` (JSON array of CFR citations found in section)
- `suggested_owner` (auto-detected based on content)
- Relationship: `manual` (many-to-one with Manual)

#### 3. **OwnershipAssignment**
Assignment results for each question.
- **Primary assignment**: `primary_function`, `supporting_functions`
- **Rationale**: `rationale`, `confidence_score` (High/Med/Low), `confidence_value` (0.0-1.0)
- **Signal breakdown**: `keyword_matches`, `cfr_matches`, `manual_section_links`
- **Override support**: `is_manual_override`, `override_reason`, `override_by`, `override_date`
- **Metadata**: `assigned_date`, `assignment_version`
- Relationship: `question` (one-to-one with Question)

#### 4. **OwnershipRule**
Configurable assignment rules.
- `rule_type` (keyword/cfr), `pattern`, `target_function`, `weight`
- `is_active`, `created_date`, `notes`

#### Updated Question Model
- Added `ownership_assignment` relationship (one-to-one with cascade delete)

### Migration Script Created

Created [backend/migrations/add_ownership_models.py](backend/migrations/add_ownership_models.py):

**Features**:
- Creates all 4 new tables
- Seeds 17 default rules:
  - **10 Keyword Rules**: inspect→Aircraft Records, control→MOC, program→MP, training→Training, etc.
  - **7 CFR Rules**: 14 CFR 121.369→MP, 14 CFR 121.379→MOC, 14 CFR 121.380→Aircraft Records, etc.
- Logging and verification

**Migration Results** (Successfully Executed):
```
✅ 4 new tables created
✅ 17 rules seeded (10 keyword, 7 CFR)
✅ All relationships properly configured
```

### Git Commits

**Commit 1**: Added PROJECT_SCOPE.md
- Comprehensive documentation of all 6 phases
- Pushed to GitHub: https://github.com/schonn0129/FAA-Audit

**Commit 2**: Added database models and migration
- 4 new models with complete relationships
- Migration script with default rules
- Successfully tested
- Pushed to GitHub

---

## Current Status

### ✅ Completed (Week 1, Day 1-2)
- [x] Created comprehensive project scope documentation
- [x] Created detailed Phase 2 implementation plan
- [x] Added 4 new database models (Manual, ManualSection, OwnershipAssignment, OwnershipRule)
- [x] Updated Question model with ownership relationship
- [x] Created and tested database migration script
- [x] Seeded 17 default rules (10 keyword + 7 CFR)
- [x] Committed and pushed all changes to GitHub

### 🔨 Next Tasks (Week 1, Day 3-5)
- [ ] Create `backend/manual_parser.py` - Parse AIP/GMM PDFs
- [ ] Implement section extraction logic
- [ ] Implement CFR citation extraction
- [ ] Implement section owner suggestion (keyword-based)
- [ ] Test manual parser with sample PDFs

---

## Technical Details

### Database Schema

**New Tables**:
1. `manuals` - Uploaded company manuals
2. `manual_sections` - Extracted sections with CFR citations
3. `ownership_assignments` - Question ownership with rationale
4. `ownership_rules` - Configurable keyword and CFR rules

**Updated Tables**:
1. `questions` - Added `ownership_assignment` relationship

### Default Rules Seeded

**Keyword Rules** (Pattern → Function):
- `inspect|inspection|inspected` → Aircraft Records (weight: 1.5)
- `control|dispatch|release` → MOC (weight: 1.5)
- `program|task card|scheduled maintenance` → Maintenance Planning (weight: 1.5)
- `record|logbook|documentation` → Aircraft Records (weight: 1.2)
- `training|curriculum|qualification` → Training (weight: 1.5)
- `audit|surveillance|quality assurance` → Quality (weight: 1.3)
- `safety|hazard|risk assessment` → Safety (weight: 1.3)
- `director|management approval` → Director of Maintenance (weight: 1.0)
- `preventive|corrective|repair` → Maintenance Planning (weight: 1.1)
- `operational control|flight dispatch` → MOC (weight: 1.4)

**CFR Rules** (CFR Citation → Function):
- `14 CFR 121.369` → Maintenance Planning (weight: 1.5)
- `14 CFR 121.373` → Maintenance Planning (weight: 1.5)
- `14 CFR 121.379` → MOC (weight: 1.5)
- `14 CFR 121.380` → Aircraft Records (weight: 1.5)
- `14 CFR 135.427` → Director of Maintenance (weight: 1.5)
- `14 CFR 121.135` → Training (weight: 1.4)
- `14 CFR 121.375` → Quality (weight: 1.3)

---

## Files Modified/Created

### New Files
- `PROJECT_SCOPE.md` - Complete 6-phase workflow documentation
- `.claude/plans/squishy-prancing-candle.md` - Detailed Phase 2 implementation plan
- `backend/migrations/add_ownership_models.py` - Database migration script

### Modified Files
- `backend/models.py` - Added 4 new models + updated Question model

### Database
- `backend/faa_audit.db` - Updated with new tables and seeded rules

---

## Key Design Decisions

### 1. Deterministic Assignment Engine
- Same DCT + same manuals = same assignments
- Every decision must trace back to rules
- Version control on rules and assignments

### 2. Multi-Signal Analysis
- **Keyword Analyzer**: Matches question text against patterns
- **CFR Analyzer**: Maps CFR citations to functions
- **Manual Reference Analyzer**: Links questions to AIP/GMM sections
- **Confidence Calculator**: Weighted scoring algorithm (High/Med/Low)

### 3. PMI Defensibility
- Complete rationale with source citations
- Manual override tracking with justification
- Export includes full audit trail
- Format: "Assigned to X because [DCT excerpt] and [AIP §Y] states..."

### 4. Confidence Scoring Algorithm
```python
High (0.75-1.0):   Multiple strong signals agree, or one very strong signal
Medium (0.50-0.74): Moderate signals, some disagreement acceptable
Low (0.0-0.49):    Weak signals, conflicting indicators, or no matches
```

### 5. Manual Document Parser Strategy
- Extract sections using pattern detection (Section X.Y.Z, Chapter X)
- Extract CFR citations using regex (reuse from DCT parser)
- Suggest owner based on section content keywords
- Handle multi-page sections
- Track which section contains each citation

---

## Example Assignment Output (from Plan)

**Question**:
- QID: 00004334
- Element: 4.2.1
- Question: "Does the operator maintain a master minimum equipment list (MMEL) that is specific to each aircraft type in the operator's fleet?"
- CFR References: ["14 CFR 121.373"]

**Signal Analysis**:
- Keyword matches: "MMEL" (1.2), "maintain" (1.1), "equipment list" (1.2) → Aircraft Records (score: 3.5)
- CFR match: "14 CFR 121.373" → Maintenance Planning (score: 1.5)
- Manual links: AIP 5.2.3 (owner: MP), GMM Ch 7 (owner: Aircraft Records)

**Assignment Result**:
- **Primary Function**: Maintenance Planning (highest weighted: 1.5 CFR + 1.2 manual)
- **Supporting Functions**: Aircraft Records (strong keyword signals)
- **Confidence**: High (0.82) - multiple signals agree
- **Rationale**:
  ```
  Assigned to Maintenance Planning based on:
  - Question text contains 'MMEL', 'equipment list' (keyword match)
  - References 14 CFR 121.373 which governs MP requirements (regulatory match)
  - AIP Section 5.2.3 addresses MMEL management
  - Supporting function: Aircraft Records (maintains MMEL documentation)
  High confidence assignment.
  ```

---

## Important Context for Home

### Repository Location
- **GitHub**: https://github.com/schonn0129/FAA-Audit
- **Local** (work): C:\Users\SchonnUnderwood\FAA-Audit
- **Branch**: main

### Dependencies Installed
```
Flask==3.0.0
Flask-CORS==4.0.0
pdfplumber==0.10.3
python-dateutil==2.8.2
SQLAlchemy>=2.0.30
```

### To Resume Work
1. Clone/pull latest from GitHub
2. Install dependencies: `pip install -r backend/requirements.txt`
3. Database is already set up with migration run
4. Next task: Create `backend/manual_parser.py`

### Key Reference Files
- **Plan**: `.claude/plans/squishy-prancing-candle.md` (comprehensive Phase 2 plan)
- **Scope**: `PROJECT_SCOPE.md` (all 6 phases documented)
- **Models**: `backend/models.py` (lines 179-331 for new models)
- **Migration**: `backend/migrations/add_ownership_models.py`

---

## Questions to Consider for Next Session

1. Do you have sample AIP/GMM PDFs to test the manual parser?
2. What format do your company manuals use for section numbering?
3. Should the manual parser handle multi-column layouts?
4. How should we handle manual version control (multiple versions of AIP/GMM)?

---

## Success Metrics (Phase 2 Complete)

Phase 2 will be complete when:
- ✅ Manuals (AIP/GMM) can be uploaded and parsed
- ✅ CFR citations extracted from manuals with 90%+ accuracy
- ✅ Questions automatically linked to manual sections
- ✅ Ownership assigned to all questions with rationale
- ✅ Confidence scores calculated (High/Med/Low)
- ✅ Users can override assignments with justification
- ✅ Admin can add/edit keyword and CFR rules
- ✅ Export includes complete ownership table
- ✅ 70%+ of assignments are "High" confidence on sample data
- ✅ Same DCT + manuals = same assignments (deterministic)

---

**Session End**: January 22, 2026
**Next Session**: Continue with manual parser implementation (Week 1, Day 3-5)
