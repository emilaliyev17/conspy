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
