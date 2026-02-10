# Session Notes - February 9, 2026
## Fix Section Number Parsing in Manual Parser

---

## Session Overview
Fixed a regex bug in `manual_parser.py` that caused subsection numbers to be mis-parsed. Lines like `3.1.1` (standalone subsection number with no title) were being split as `section_number="3.1"` + `title=".1"`, resulting in incorrect MAP references across the board. After the fix, the MAP correctly shows full subsection numbers like `3.1.1(c)` instead of `3.1(c)`.

---

## Problem
The MAP was displaying incorrect manual references for DCT questions. Example for QID 00004334:

| Before (wrong) | After (correct) |
|---|---|
| `3.1(c)` | `3.1.1(c)` |
| `14.1(c)` | `14.1.1(c)` |
| `14(i)` | `14(i)` (unchanged) |
| `14.7(i)` | `14.7.2(i)` |

The issue affected every subsection number in the entire GMM manual — any line in the PDF that contained just a number like `3.1.1` without title text was being mis-parsed.

---

## Root Cause
In `backend/manual_parser.py`, the `SECTION_PATTERNS` list has four regex patterns tried in order:

1. `CHAPTER N` headings
2. `SECTION N.N` headings
3. **Numbered section with title** — `6.4.1 AD Management Process`
4. **Numbered section alone** — `6.4.1` or `6.4.1.`

Pattern 3's regex was: `^(\d+(?:\.\d+){1,4})\s*[-–—:]?\s*(.+)$`

The `(.+)$` at the end greedily captured any trailing characters as a "title". For a line like `3.1.1`:
- Group 1 matched `3.1` (the number)
- Group 2 matched `.1` (treated as the title)

Pattern 4 would have correctly handled this as `section_number="3.1.1"`, but Pattern 3 matched first.

---

## Fix Applied
**File:** `backend/manual_parser.py` line 27

Changed the title capture group from `(.+)` to `([A-Za-z].*)` so titles must start with a letter:

```python
# Before:
re.compile(r'^(\d+(?:\.\d+){1,4})\s*[-–—:]?\s*(.+)$')

# After:
re.compile(r'^(\d+(?:\.\d+){1,4})\s*[-–—:]?\s*([A-Za-z].*)$')
```

This one-character change (`(` → `([A-Za-z]`) ensures that `.1` is never captured as a title, so Pattern 4 correctly handles standalone section numbers.

---

## Verification

### Regex test cases (all pass):
| Input | section_number | title |
|---|---|---|
| `3.1.1 AD Management Process` | `3.1.1` | `AD Management Process` |
| `3.1.1` | `3.1.1` | `` (empty) |
| `3.1.1.` | `3.1.1` | `` (empty) |
| `3.1 General Maintenance` | `3.1` | `General Maintenance` |
| `14.7.2` | `14.7.2` | `` (empty) |

### Database verification:
- Before: 0 rows with `section_number` like `3.1.%` — all stored as `3.1`
- After: `3.1.1`, `3.1.2`, `3.1.3`, `3.1.4`, `3.1.5` correctly stored
- Total section count: 3005 → 2502 (fewer duplicates from mis-parsing)

### MAP output for QID 00004334:
- `GMM_Reference: "3.1.1(c); 14.1.1(c); 14(i); 14.7.2(i)"`
- First match `3.1.1(c)` — correct, was `3.1(c)` before

---

## Steps Performed
1. Identified the issue by querying the MAP debug endpoint for QID 00004334
2. Queried the database directly — confirmed zero `3.1.x` entries existed
3. Traced the bug to Pattern 3 regex in `manual_parser.py`
4. Applied one-line regex fix
5. Rebuilt backend Docker container (`docker-compose -f docker-compose.windows.yml build backend`)
6. Restarted backend container (`docker-compose -f docker-compose.windows.yml up -d backend`)
7. Re-parsed GMM manual via `POST /api/manuals/<id>/reparse`
8. Verified correct section numbers in database and MAP output

---

## Known Remaining Items
- MAP mapping could still be further tuned (accuracy, relevance of matched sections)
- Session was cut short due to Claude Code lockup requiring restart
- Additional QIDs should be spot-checked to confirm mapping improvements

---

## Files Changed
- `backend/manual_parser.py` — Fixed regex Pattern 3 (line 27)
- `TROUBLESHOOTING.md` — Added session log entry for this fix
