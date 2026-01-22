# FAA DCT Compliance Engine - Project Scope & Workflow

## Core Design Philosophy

This is a **deterministic compliance engine**, not a generative AI task. Every decision must be traceable, repeatable, and defensible under PMI scrutiny. The workflow locks in quality gates before proceeding.

---

## Execution Approach

### Phase 1: DCT Ingestion & Validation ✅ COMPLETE

**Objective:** Parse the DCT PDF to extract 100% of QIDs with associated question text, intent, and regulatory references.

**Implementation Status:** Complete
- Parser extracts: Element_ID, QID, Question_Text_Full, Question_Text_Condensed, Data_Collection_Guidance, References (CFR, FAA Guidance, Other), PDF_Page_Number
- Location: `backend/pdf_parser.py`

**Deliverables:**
- [x] Parse DCT PDF to extract all QIDs
- [x] Build completeness hash (total QID count) as validation checkpoint
- [ ] Flag ambiguous questions for human review before ownership assignment
- [x] Create immutable QID registry as audit's source of truth

---

### Phase 2: Ownership Assignment Logic 🔨 IN PROGRESS

**Objective:** Apply rules-based decision tree to assign each QID to a responsible function.

**Implementation Status:** Not started

**The 7 Authorized Functions:**
1. Maintenance Planning (MP)
2. Maintenance Operations Center (MOC)
3. Director of Maintenance (DOM)
4. Aircraft Records
5. Quality
6. Training
7. Safety

**Assignment Signals:**
1. **Keyword Analysis**
   - `inspect/inspection` → Aircraft Records
   - `control/dispatch` → MOC
   - `program/task card` → MP
   - *(More patterns to be defined)*

2. **Regulatory Context**
   - `14 CFR 121.369` → MP
   - `14 CFR 121.379` → MOC
   - `14 CFR 135.427` → DOM
   - *(More mappings to be defined)*

3. **AIP/GMM Cross-Reference**
   - Which manual section addresses this requirement?

4. **Operational Reality**
   - Who actually executes this in practice?

**Each Assignment Includes:**
- Primary owner (single point of accountability)
- Supporting functions (coordinating roles)
- Rationale statement citing DCT language + company manual reference
- Confidence score (High/Medium/Low based on clarity of signals)

**Deliverables:**
- [ ] Build keyword analysis engine
- [ ] Map CFR references to functions
- [ ] Create AIP/GMM cross-reference lookup
- [ ] Implement confidence scoring algorithm
- [ ] Generate ownership assignment table for all QIDs

---

### Phase 3: Audit Scoping with Full Accountability 🔨 NOT STARTED

**Objective:** Allow user to define audit focus while maintaining full QID accountability.

**Implementation Status:** Not started

**Functionality:**
- User defines focus (e.g., "MP and Aircraft Records only")
- Out-of-scope QIDs remain documented in ownership table
- Dashboard shows % coverage by function
- PDF package includes "Deferred Items" appendix listing non-audited QIDs with their owners

**PMI Requirement:**
> "This ensures PMI can see you accounted for everything, even if you didn't audit everything."

**Deliverables:**
- [ ] Build scope selection UI
- [ ] Implement in-scope vs. deferred tracking
- [ ] Create coverage metrics calculation
- [ ] Generate deferred items report

---

### Phase 4: MAP Construction 🔨 NOT STARTED

**Objective:** Build the Mapping Audit Package for in-scope functions.

**Implementation Status:** Not started

**MAP Table Structure:**

| QID | Question Text | AIP Reference | GMM Reference | Evidence Required | Audit Finding | Compliance Status |
|-----|---------------|---------------|---------------|-------------------|---------------|-------------------|
| ... | ...           | ...           | ...           | ...               | *(empty)*     | *(empty)*         |

**Features:**
- Pre-populate references from ownership rationale
- Leave Finding/Status columns empty for auditor completion
- Include "Evidence Guidance" column with suggested artifacts

**Deliverables:**
- [ ] Design MAP data structure
- [ ] Build MAP generator from in-scope QIDs
- [ ] Pre-populate AIP/GMM references
- [ ] Add evidence guidance suggestions
- [ ] Export MAP to Excel format

---

### Phase 5: Dashboard & Risk Visualization 🔨 NOT STARTED

**Objective:** Generate executive summary with visual analytics.

**Implementation Status:** Not started

**Required Visualizations:**
1. **Pie Chart:** QID distribution by owner
2. **Bar Chart:** In-scope vs. deferred
3. **Risk Heatmap:** Questions with weak manual references flagged yellow
4. **Coverage Metrics:** % of DCT accounted for, % audited this cycle

**Deliverables:**
- [ ] Build dashboard UI
- [ ] Implement pie chart (QID distribution)
- [ ] Implement bar chart (scope coverage)
- [ ] Implement risk heatmap
- [ ] Calculate and display coverage metrics

---

### Phase 6: PDF Assembly 🔨 NOT STARTED

**Objective:** Generate structured compliance package for PMI review.

**Implementation Status:** Not started

**PDF Package Structure:**
1. **Executive Summary**
   - Scope definition
   - Methodology overview
   - Coverage statistics

2. **QID Functional Ownership Table**
   - ALL QIDs with assignments
   - Rationale for each assignment
   - Confidence scores

3. **In-Scope MAP**
   - Audit-ready worksheets for selected functions
   - Pre-populated references
   - Evidence guidance

4. **Deferred Items Log**
   - Out-of-scope QIDs with documented owners
   - Justification for deferral

5. **Methodology Appendix**
   - Decision rules documentation
   - Source hierarchy explanation
   - Version control info (DCT/AIP/GMM versions used)

6. **Sign-off Page**
   - For PMI review and approval

**Deliverables:**
- [ ] Build PDF generation engine
- [ ] Create executive summary template
- [ ] Generate ownership table export
- [ ] Generate MAP export
- [ ] Generate deferred items log
- [ ] Create methodology appendix
- [ ] Add sign-off page template

---

## Key Defensive Measures

### Scope Creep Prevention
- ✅ No QID additions beyond the DCT
- ✅ No custom ownership categories beyond the 7 authorized
- ✅ Audit focus is a filter, not a modification of the full accounting

### PMI Defensibility
- Every ownership assignment cites specific DCT language + manual section
  - Format: *"We assigned X to Y because [DCT excerpt] and [AIP §Z] states..."*
- Low-confidence assignments flagged for management validation pre-audit

### Repeatability
- Same DCT + same manuals = same ownership table (deterministic)
- Version control on DCT/AIP/GMM used (include in PDF header)

---

## What This Enables

A quality manager can hand this package to a PMI and say:

> "Here are all 247 QIDs from ED 4.1.2"
> "Here's why we assigned each to its owner"
> "Here are the 89 we're auditing this cycle"
> "Here are the 158 we're deferring, with their documented owners"
> "Everything is accounted for. Nothing is orphaned."

---

## Current Implementation Status

### ✅ Completed
- PDF parser extracts QIDs with full metadata
- Database layer for audit storage
- Basic upload API endpoint
- React frontend for PDF upload

### 🔨 In Progress
- None currently

### ❌ Not Started
- Ownership assignment logic (Phase 2)
- Audit scoping interface (Phase 3)
- MAP generation (Phase 4)
- Dashboard visualizations (Phase 5)
- PDF export package (Phase 6)

---

## Next Steps

1. **Define Ownership Rules**
   - Document keyword patterns for each function
   - Map all relevant CFR sections to functions
   - Define AIP/GMM lookup strategy

2. **Build Ownership Assignment Engine**
   - Implement rules-based decision tree
   - Add confidence scoring
   - Create ownership table data structure

3. **Develop Scoping Interface**
   - UI for function selection
   - In-scope vs. deferred tracking
   - Coverage metrics

4. **Implement MAP Generation**
   - Excel export functionality
   - Reference pre-population
   - Evidence guidance

5. **Build Dashboard**
   - Visual analytics
   - Risk indicators
   - Executive summary

6. **PDF Assembly**
   - Complete compliance package generation
   - All required sections
   - PMI-ready format

---

## Repository Structure

```
FAA-Audit/
├── backend/
│   ├── app.py                 # Flask API (✅ Phase 1 complete)
│   ├── pdf_parser.py          # DCT PDF parser (✅ Phase 1 complete)
│   ├── database.py            # Database layer (✅ Phase 1 complete)
│   ├── ownership.py           # ❌ Phase 2: Ownership assignment logic
│   ├── map_generator.py       # ❌ Phase 4: MAP construction
│   ├── pdf_export.py          # ❌ Phase 6: PDF assembly
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx            # Main UI (✅ Basic upload complete)
│       ├── components/
│       │   ├── Dashboard.jsx  # ❌ Phase 5: Visualizations
│       │   ├── OwnershipTable.jsx  # ❌ Phase 2: View assignments
│       │   └── ScopeSelector.jsx   # ❌ Phase 3: Audit scoping
│       └── services/
│           └── api.js         # ✅ Basic API integration
├── PROJECT_SCOPE.md           # This file
├── README.md
├── DEVELOPMENT.md
└── SETUP.md
```

---

## Version Control

- **Document Version:** 1.0
- **Last Updated:** 2026-01-22
- **DCT Version:** TBD (specify when implementing)
- **AIP Version:** TBD (specify when implementing)
- **GMM Version:** TBD (specify when implementing)
