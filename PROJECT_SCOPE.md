# FAA DCT Compliance Engine - Project Scope & Workflow

## Core Design Philosophy

This is a **deterministic compliance engine**, not a generative AI task. Every decision must be traceable, repeatable, and defensible under PMI scrutiny. The workflow locks in quality gates before proceeding.

---

## Execution Approach

### Phase 1: DCT Ingestion & Validation ✅ COMPLETE

**Objective:** Parse the DCT PDF to extract 100% of QIDs with associated question text, intent, and regulatory references.
**Note:** QID counts vary by DCT edition/version; completeness is validated against the specific uploaded DCT, not a fixed number.

**Implementation Status:** Complete
- Parser extracts: Element_ID, QID, Question_Text_Full, Question_Text_Condensed, Data_Collection_Guidance, References (CFR, FAA Guidance, Other), PDF_Page_Number
- Location: `backend/pdf_parser.py`

**Deliverables:**
- [x] Parse DCT PDF to extract all QIDs
- [x] Build completeness hash (total QID count) as validation checkpoint
- [ ] Flag ambiguous questions for human review before ownership assignment
- [x] Create immutable QID registry as audit's source of truth

---

### Phase 2: Ownership Assignment Logic ✅ COMPLETE

**Objective:** Apply rules-based decision tree to assign each QID to a responsible function.

**Implementation Status:** Complete

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
- [x] Build keyword analysis engine
- [x] Map CFR references to functions
- [x] Create manual cross-reference lookup (company manuals)
- [x] Implement confidence scoring algorithm
- [x] Generate ownership assignment table for all QIDs

---

### Phase 3: Audit Scoping with Full Accountability ✅ COMPLETE

**Objective:** Allow user to define audit focus while maintaining full QID accountability.

**Implementation Status:** Complete

**Functionality:**
- User defines focus (e.g., "MP and Aircraft Records only")
- Out-of-scope QIDs remain documented in ownership table
- Dashboard shows % coverage by function
- PDF package includes "Deferred Items" appendix listing non-audited QIDs with their owners

**PMI Requirement:**
> "This ensures PMI can see you accounted for everything, even if you didn't audit everything."

**Deliverables:**
- [x] Build scope selection UI
- [x] Implement in-scope vs. deferred tracking
- [x] Create coverage metrics calculation
- [x] Generate deferred items report

---

### Phase 4: MAP Construction ✅ COMPLETE

**Objective:** Build the Mapping Audit Package for in-scope functions.

**Implementation Status:** Complete

**MAP Table Structure:**

| QID | Question Text | AIP Reference | GMM Reference | Other Manual References | Evidence Required | Applicability Status | Applicability Reason | Audit Finding | Compliance Status |
|-----|---------------|---------------|---------------|-------------------------|-------------------|----------------------|----------------------|---------------|-------------------|
| ... | ...           | ...           | ...           | ...                     | ...               | Applicable/Not Applicable | *(optional)* | *(empty)*     | *(empty)*         |

**Features:**
- Pre-populate references from latest uploaded company manuals (AIP/GMM/Other)
- Leave Finding/Status columns empty for auditor completion
- Include evidence guidance from DCT "Data Collection Guidance"
- Track applicability (auditor can mark Not Applicable; tool can auto-detect)

**Deliverables:**
- [x] Design MAP data structure
- [x] Build MAP generator from in-scope QIDs
- [x] Pre-populate manual references (AIP/GMM/Other)
- [x] Add evidence guidance suggestions
- [x] Export MAP to Excel/CSV format
- [x] Include applicability status/reason columns

---

### Phase 5: Dashboard & Risk Visualization ✅ COMPLETE

**Objective:** Generate executive summary with visual analytics.

**Implementation Status:** Complete

**Required Visualizations:**
1. **Pie Chart:** QID distribution by owner
2. **Bar Chart:** In-scope vs. deferred
3. **Risk Heatmap:** Questions with weak manual references flagged yellow
4. **Coverage Metrics:** % of DCT accounted for, % audited this cycle

**Deliverables:**
- [x] Build dashboard UI
- [x] Implement pie chart (QID distribution)
- [x] Implement bar chart (scope coverage)
- [x] Implement risk heatmap
- [x] Calculate and display coverage metrics

**Implementation Details:**
- Charts implemented using recharts library
- CoverageDashboard component enhanced with executive summary cards
- Risk heatmap shows confidence vs manual reference matrix
- Items flagged for review: low confidence, missing manual references

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

## Phase 7: Mapping Memory (Reference Learning) 🧠 PLANNED

**Objective:** When an auditor finalizes an element, persist the approved manual references and apply them automatically on the next audit of the same DCT edition/version and element.

**Key Behavior:**
- Auditor marks an element as “finalized”
- System saves manual references as the preferred mapping for that element
- On future audits with the same DCT edition/version, the system pre-populates those references
- Manual overrides still allowed; auditors can update mappings and re-save

**Deliverables:**
- [ ] Element finalization workflow (UI + API)
- [ ] Persisted reference mapping store (by DCT edition/version + element + QID)
- [ ] Auto-apply saved mappings during MAP generation
- [ ] Override and re-save workflow with audit trail

---

## Phase 8: Manual Structure & Compliance Gap Analysis 🧾 PLANNED

**Objective:** Analyze the GMM and the first two chapters of the AIP to verify required structure, detect missing content, and flag policy/procedure conflicts tied to DCT/8900.1 guidance expectations.

**Scope:**
- GMM (all chapters)
- AIP Chapters 1–2 only (AIP overall structure differs; later phases can expand)

**Key Behavior:**
- Validate section structure against the expected template (e.g., General, Responsibility & Authority, Policy, Procedure)
- Identify missing required sections and ownership clarity gaps
- Detect conflicts between policy and procedure (or conflicting statements across sections)
- Distinguish **regulatory gaps** (CFR-required, highest severity) from **guidance gaps** (AC/8900.1 best-practice)
- When DCT or 8900.1 guidance indicates a required program element, flag missing/weak coverage as a **guidance gap** with elevated safety impact (but not regulatory non-compliance)

**Deliverables:**
- [ ] Manual structure validator (configurable headings/aliases)
- [ ] Gap detection engine with severity scoring (high impact for DCT/8900.1 required items)
- [ ] Conflict detection rules (policy vs procedure, inconsistent ownership)
- [ ] Report output (by manual, chapter, section; with evidence excerpts)

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
- Startup script auto-selects free ports for repeatable local testing

---

## What This Enables

A quality manager can hand this package to a PMI and say:

> "Here are all 44 QIDs from ED 4.2.1 (Version 29)"
> "Here's why we assigned each to its owner"
> "Here are the QIDs we're auditing this cycle"
> "Here are the QIDs we're deferring, with their documented owners"
> "Everything is accounted for. Nothing is orphaned."

---

## Current Implementation Status

### ✅ Completed
- Phase 1: PDF parser extracts QIDs with full metadata
- Phase 2: Ownership assignment logic with confidence scoring
- Phase 3: Audit scoping interface with coverage metrics
- Phase 4: MAP generation with manual cross-references
- Phase 5: Dashboard visualizations (pie chart, bar chart, risk heatmap)
- Database layer for audit storage
- React frontend with full navigation

### 🔨 In Progress
- None currently

### ❌ Not Started
- Phase 6: PDF export package

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
│   ├── app.py                 # Flask API (✅ All endpoints)
│   ├── pdf_parser.py          # DCT PDF parser (✅ Phase 1)
│   ├── database.py            # Database layer (✅ Phase 1)
│   ├── ownership.py           # ✅ Phase 2: Ownership assignment
│   ├── scoping.py             # ✅ Phase 3: Audit scoping
│   ├── map_builder.py         # ✅ Phase 4: MAP construction
│   ├── export_map.py          # ✅ Phase 4: MAP export
│   ├── manual_parser.py       # ✅ Manual parsing
│   ├── manual_mapper.py       # ✅ Manual cross-reference
│   ├── pdf_export.py          # ❌ Phase 6: PDF assembly
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx            # Main UI with navigation
│       ├── App.css            # Styles including chart styles
│       ├── components/
│       │   ├── CoverageDashboard.jsx  # ✅ Phase 5: Dashboard
│       │   ├── ScopeSelector.jsx      # ✅ Phase 3: Scope UI
│       │   ├── DeferredItemsList.jsx  # ✅ Phase 3: Deferred items
│       │   ├── MapTable.jsx           # ✅ Phase 4: MAP view
│       │   ├── ManualManager.jsx      # ✅ Manual upload
│       │   └── charts/
│       │       ├── OwnershipPieChart.jsx  # ✅ Phase 5
│       │       ├── ScopeBarChart.jsx      # ✅ Phase 5
│       │       ├── RiskHeatmap.jsx        # ✅ Phase 5
│       │       └── index.js
│       └── services/
│           └── api.js         # ✅ Full API integration
├── PROJECT_SCOPE.md           # This file
├── README.md
├── DEVELOPMENT.md
└── SETUP.md
```

---

## Glossary & Severity Definitions

- **Regulatory Gap (CFR):** A required element mandated by 14 CFR is missing or insufficiently documented. This is treated as the highest severity because it represents potential non-compliance.
- **Guidance Gap (AC/8900.1/DCT):** A best-practice element recommended by Advisory Circulars, FAA 8900.1 guidance, or DCT expectations is missing or weak. This is flagged as high safety impact but **not** labeled as regulatory non-compliance.
- **Policy/Procedure Conflict:** A policy statement conflicts with a procedure, or procedures conflict across sections, creating ambiguity or inconsistent execution.
- **Ownership Gap:** A required responsibility/authority is not assigned or is unclear in the manual.
- **Manual Structure Compliance:** Presence and order of expected sections (e.g., General, Responsibility & Authority, Policy, Procedure) for applicable manuals/chapters.

## Version Control

- **Document Version:** 1.1
- **Last Updated:** 2026-01-26
- **DCT Version:** ED 4.2.1 (Version 29) — 44 questions (note: other DCTs will have different question counts)
- **AIP Version:** TBD (specify when implementing)
- **GMM Version:** TBD (specify when implementing)
