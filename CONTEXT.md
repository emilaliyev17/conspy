# FINANCIAL CONSOLIDATOR - CRITICAL CONTEXT

## ⚠️ PRODUCTION SYSTEM WARNING
This is a **multi-million dollar financial reporting system**. Every bug impacts real financial decisions.

## EXECUTION RULES
1. **You are an EXECUTOR, not a project manager**
2. **Make ONLY explicitly requested changes**
3. **Never optimize or refactor without explicit instruction**
4. **Every unauthorized change costs 5-6 hours of debugging**

## TECHNICAL SPECIFICATIONS

### File Paths
- P&L Report: `core/templates/core/pl_report.html`
- Views: `core/views.py`
- Models: `core/models.py`
- Project Root: `/Users/emil.aliyev/My Projects/financial_consolidator/`

### Feature Flags
- `PL_BUDGET_PARALLEL` controls dual-stream P&L (Actual companies vs Budget-only company).
- In Budget/Forecast views, consolidated Budget comes from the budget-only stream and must not appear as a per-company column.

### Critical Element IDs
- `from_month` - Starting month dropdown
- `from_year` - Starting year dropdown
- `to_month` - Ending month dropdown
- `to_year` - Ending year dropdown
- `data_type` - Actual/Budget/Forecast dropdown

### Protected Functions
- `loadPLData()` - DO NOT MODIFY
- `loadFilters()` - DO NOT MODIFY
- ag-Grid configuration - DO NOT MODIFY unless explicitly requested

### Current State Updates (Stability Alignment)
- Frontend (P&L grid): `core/templates/core/pl_report.html` is reverted to the last stable committed version. No experimental collapse/expand logic or debug logging is present.
- Backend (P&L Budget ordering): `core/views.py` updated to ensure the consolidated Budget/Forecast column appears after `TOTAL` for each period.
  - Case-insensitive checks for `data_type` when adding Budget/Forecast period columns.
  - CF Dashboard Budget/Forecast fetch uses lowercase `data_type` for consistency.
  - `display_companies` excludes the budget-only company; budget data is shown only in the consolidated `Budget` column.
  - Dual streams under `PL_BUDGET_PARALLEL` remain: Actuals from non-budget companies; Budget/Forecast from the single budget-only company (mapped into consolidated results only).

## TEST PROTOCOL (Required after ANY change)
1. ✓ Filters persist across page refresh
2. ✓ Headers visible during vertical scroll
3. ✓ Headers visible during horizontal scroll
4. ✓ No console errors
5. ✓ No performance degradation
6. ✓ Budget/Forecast view: Budget column appears after `TOTAL` for each period
7. ✓ Budget-only company is NOT shown as a per-company column; budget values appear only in the consolidated `Budget` column
8. ✓ CF Dashboard: Budget/Forecast values load for the selected periods without console/API errors

## CHANGE REQUEST FORMAT
Task: [One specific change]
File: [Exact file path]
Line: [Line numbers if known]
Constraint: [What NOT to touch]
Success: [Observable result]

Notes for Budget-related changes:
- Do not include the budget-only company in per-company display columns.
- Maintain column order per period: Company columns → `TOTAL` → `Budget` (when `data_type` is Budget/Forecast).
- Preserve `PL_BUDGET_PARALLEL` segregation of Actual vs Budget streams.

## CONSEQUENCES OF VIOLATIONS
- Cursor AI: TERMINATED for unauthorized refactoring
- Gemini CLI: TERMINATED for unsolicited improvements
- Premium subscriptions: CANCELLED

## THE ONLY RULE
**If you weren't asked to change it, DON'T TOUCH IT.**

## SHORT REMINDER FOR EACH REQUEST
Production financial system. Executor-only. No unsolicited changes. Use IDs: from_month, from_year, to_month, to_year, data_type. Touch only files/lines specified. Preserve ag-Grid behavior and loadPLData(). Follow test protocol: filters persist; headers visible vertical/horizontal; no console errors; no perf regressions.

---

## UPDATE: P&L Report Column Collapse/Expand Feature
Date: 2025-09-08
Implemented by: Claude AI Assistant with Emil

### Features Added:

#### 1. PeriodToggleHeader Component
- Location: core/templates/core/pl_report.html (lines 460-545)
- Adds [-]/[+] buttons to TOTAL column headers
- Toggles visibility of company columns (F001, GL001) per period
- Preserves TOTAL and Budget columns visibility

#### 2. Global Collapse/Expand Controls
- Added "Collapse All" and "Expand All" buttons in actions bar
- Event-based synchronization using 'periodToggleAll' custom event
- Stored grid API reference in window.plGridApi for global access

#### 3. CF Dashboard Budget Editing Fix
- Fixed: Budget cells were not editable in CF Dashboard
- Cause: Missing 'colType': 'budget' in column definition
- Solution: Added 'colType': 'budget' to views.py line 1295
- Result: Budget cells now editable and save to database

### Technical Implementation:
- AG Grid v34.1.2 compatibility confirmed
- Used getUserProvidedColDef() for accessing custom column properties
- Event listeners for state synchronization between headers
- No impact on existing features (export, print, CF editing)

### Files Modified:
- core/templates/core/pl_report.html (+142 lines)
- core/views.py (+1 line for Budget fix)

### Testing Completed:
✅ Individual period collapse/expand working
✅ Collapse All/Expand All synchronization working
✅ CF Dashboard Budget editing restored
✅ Data saves to database correctly
✅ No console errors
✅ Export/Print functionality unchanged

---

## UPDATE: Company Column Colors and Grand Total Budget Implementation
Date: 2025-01-09
Implemented by: Claude AI Assistant with Emil

### COMPLETED FEATURES:

1. Dynamic Company Column Colors
   - Each company gets unique background color from palette
   - Palette: ['#E6F7FF', '#F0F9FF', '#E6FFFA', '#F6FFED', '#FFF7E6']
   - Color assignment: palette[index % len(palette)] for visual distinction
   - Applied to both period columns and Grand Total columns
   - No red tones (per business requirement)

2. Column Styling Consistency
   - Company columns: Dynamic soft colors
   - TOTAL columns: #FFF9E6 (yellowish)
   - Budget columns: #F0F0FF (lavender)
   - Grand Total matches source column colors

3. Grand Total Budget Functionality
   - Added 'grand_total_Budget' column after 'grand_total_TOTAL'
   - Sums all Budget values across selected period
   - Works for both P&L and CF Dashboard rows
   - Non-editable (no colType to prevent editing)

4. Fixed Column Order
   - Period columns: Companies → TOTAL → Budget
   - Grand Total: Companies → TOTAL → Budget (consistent order)
   - Budget-only company Grand Total moved to end

### CRITICAL FIX - Duplicate Grand Total Budget:
- Problem: Two 'grand_total_Budget' columns appeared
- Root Cause: Budget-only company has code='Budget', creating field name collision
- Solution: Skip creating grand_total for budget-only company (was always empty)
- File: core/views.py lines 1361-1369 - loop now passes instead of appending

### Technical Implementation:
- Color mapping: core/views.py lines 1258-1262 (color_by_company dict)
- Company colors: lines 1268-1274 (period columns), 1304-1309 (grand totals)
- TOTAL color: line 1286 (period), line 1327 (grand total)
- Budget color: line 1303 (period), line 1347 (grand total)
- Grand Total Budget: lines 1341-1349 (columnDef), 1467-1478 (CF sum), 1534-1546 (P&L sum)

### Files Modified:
- core/views.py (color assignments, Grand Total Budget implementation)

### Testing Completed:
✅ Company colors display correctly
✅ Grand Total colors match their companies
✅ Budget columns show lavender
✅ Grand Total Budget calculates correctly
✅ No duplicate columns
✅ CF Dashboard Budget editing still works
✅ Export/Print functionality unchanged
✅ Collapse/Expand feature unaffected

### IMPORTANT NOTES:
- Company names can change dynamically - colors assigned by position, not name
- Budget-only company grand total intentionally removed (was empty/unused)
- All changes preserve existing functionality
- No performance impact observed

---

## UPDATE: Changes in Last 5 Days (2025-09-10 → 2025-09-15)
Implemented by: Codex CLI with Emil

### P&L Report (PL)
- Export Options
  - Added export dropdown (no Bootstrap) with two options: Formatted (with totals) and Raw Data.
  - File: `core/templates/core/pl_report.html`
  - Backend now supports `export_type` query param in `export_report_excel`.
  - For `export_type=formatted` and `type=pl`, export reuses `pl_report_data` to build hierarchical data (subtotals, totals, net income) and writes an Excel aligned to on-screen columns, with bold styling on subtotal/total rows and a light fill for totals.
  - File: `core/views.py` (updated `export_report_excel`)

- Font Size Controls
  - Added A-/A/A+ controls with localStorage persistence to adjust font size of numeric data cells only (headers and account names remain unchanged).
  - CSS targets only `.ag-cell[col-id*="_"]` to scale per-company, TOTAL, Budget, and grand total numeric columns.
  - After font changes, the grid triggers `resetRowHeights`, `refreshHeader`, and `refreshCells` for clean layout.
  - File: `core/templates/core/pl_report.html`

- Grid Readability and Layout
  - Added subtle grid lines for data cells, professional font stack with tabular numbers, reduced row height, and vertically centered cell content to increase data density and readability.
  - File: `core/templates/core/pl_report.html`

- Grand Totals Toggle Enhancements
  - Introduced `GrandTotalsToggleHeader` to toggle grand total company columns; extended global collapse/expand logic accordingly. Annotated grand total `columnDefs` with `colType` and header component for consistent control.
  - Files: `core/templates/core/pl_report.html`, `core/views.py`

- Version Pin
  - Pinned AG Grid to `31.3.2` in PL template to prevent API drift.
  - File: `core/templates/core/pl_report.html`

### Balance Sheet (BS)
- Collapse/Expand Feature
  - Added collapse/expand functionality for Balance Sheet columns; UI parity improvements with P&L.
  - File: `core/templates/core/bs_report.html`, `core/views.py`

- Version Pin
  - Pinned AG Grid to `31.3.2` in BS template to keep consistent behavior.
  - File: `core/templates/core/bs_report.html`

### Home/UI Redesign
- Major UI updates: FAES+CO branding, hero/skyline imagery, higher-quality assets, navigation icons, real USA map with active states.
- Files: `core/templates/core/home.html`, `core/static/core/images/*`

### Backend/Settings/Deployment
- Deployment pipeline
  - Added Dockerfile and configured collectstatic at build time; Procfile and runtime.txt for process management.
  - Ensured `gunicorn` present in final image and used in Procfile.
  - Files: `Dockerfile`, `Procfile`, `runtime.txt`, `requirements.txt`

- Static files
  - Migrated to Django 5.x `STORAGES` config with WhiteNoise compressed manifest storage; added a non-strict storage class for flexibility.
  - Files: `financial_consolidator/settings.py`, `core/storage.py`

- Security and Prod Config
  - Fixed redirect loop via `SECURE_PROXY_SSL_HEADER`; removed `SECURE_SSL_REDIRECT` for DigitalOcean proxy setup.
  - Dynamic `ALLOWED_HOSTS`, added `CSRF_TRUSTED_ORIGINS` for ondigitalocean.app and optional host; enabled secure cookies/SSL settings for production.
  - Added `DATABASE_URL` support for production.
  - Files: `financial_consolidator/settings.py`

- Authentication/Admin
  - Enforced authentication to protect financial data; added login template and routes.
  - Introduced `django-admin-interface` with dark theme; registered `admin_interface` and `colorfield`; set `X_FRAME_OPTIONS=SAMEORIGIN`.
  - Files: `financial_consolidator/settings.py`, `financial_consolidator/urls.py`, `core/templates/core/login.html`, `requirements.txt`

### Models & Data
- Added `ActiveState` model and migration to track active US states for the home page map; integrated in `home` view.
- Files: `core/migrations/0014_activestate.py`, `core/models.py`, `core/views.py`

### Fixes & Hygiene
- Resolved Python syntax/indentation errors in `core/views.py` found during cleanup.
- Removed debug logs and refined UI layers across templates.

### Notes
- Formatted P&L export uses the same data logic as the on-screen grid, including section headers, subtotals, and totals. Budget columns appear only for Budget/Forecast data types and follow the same order as the grid (Company → TOTAL → Budget). Grand total columns match the grid order as well.
- The raw P&L export remains unchanged (direct `FinancialData` aggregation per account) and is offered as a separate option in the dropdown.

---

## ROLLBACK: Deal Tracking Feature Fully Reverted
Date: 2025-09-16

- Restored repository to pre-deal-tracking state by hard-resetting to commit `e08583f` ("Docs: Add last 5 days of updates...").
- All changes related to ActiveState deal fields, homepage deals table, and associated view/template/admin edits have been removed.
- Force-pushed `main` to ensure production matches the last known working version prior to today's changes.
- Follow-up: Re-introduce the feature behind a branch/PR with a staging validation plan before production deployment.

---

## Recent Major Refactoring (December 2024)

### Removed All Hardcoded Subcategory Names
**Problem:** P&L report had hardcoded subcategory names throughout the codebase, making it impossible to work with different Chart of Accounts.

**Changes Made:**
1. **Backend (core/views.py):**
   - Removed hardcoded `correct_order` array
   - Replaced with dynamic sorting based on `sort_order` field from database
   - Added metadata to each row: `rowType`, `section`, `level`, `styleToken`

2. **Frontend (pl_report.html):**
   - Removed all name-based checks in `getRowClass` function
   - Replaced with metadata-driven CSS classes
   - CSS now uses generic classes instead of specific category names

3. **Database:**
   - Updated all `sort_order` values to control display order:
     - P&L Income: 100-300
     - P&L Expenses: 1100-1700
     - Balance Sheet Assets: 5100-5300
     - Balance Sheet Liabilities: 6100-6900
     - Balance Sheet Equity: 7100-7900

**Result:** System now works with ANY Chart of Accounts. Categories can be renamed, added, or reordered without any code changes.

### Important Notes:
- Sort order controls display sequence (lower numbers appear first)
- All styling is metadata-driven, not name-dependent
- CF Dashboard integration preserved
- Excel export functionality maintained

### Removed All Hardcoded Subcategory Names
**Problem:** P&L report had hardcoded subcategory names throughout the codebase, making it impossible to work with different Chart of Accounts.

**Changes Made:**
1. **Backend (core/views.py):**
   - Removed hardcoded `correct_order` array
   - Replaced with dynamic sorting based on `sort_order` field from database
   - Added metadata to each row: `rowType`, `section`, `level`, `styleToken`

2. **Frontend (pl_report.html):**
   - Removed all name-based checks in `getRowClass` function
   - Replaced with metadata-driven CSS classes
   - CSS now uses generic classes instead of specific category names

3. **Database:**
   - Updated all `sort_order` values to control display order:
     - P&L Income: 100-300
     - P&L Expenses: 1100-1700
     - Balance Sheet Assets: 5100-5300
     - Balance Sheet Liabilities: 6100-6900
     - Balance Sheet Equity: 7100-7900

**Result:** System now works with ANY Chart of Accounts. Categories can be renamed, added, or reordered without any code changes.

### Important Notes:
- Sort order controls display sequence (lower numbers appear first)
- All styling is metadata-driven, not name-dependent
- CF Dashboard integration preserved
- Excel export functionality maintained
