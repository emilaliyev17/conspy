# PROJECT STATUS - Django Financial Consolidator
Last Updated: September 2025
Previous PM: Claude (Session 1)
Owner: Emil Aliyev

## 🎯 PROJECT OVERVIEW
- **Type:** Enterprise financial consolidation system (handles $10M+ revenue)
- **Purpose:** Consolidate P&L, Balance Sheet, CF Dashboard for multiple companies
- **Stack:** Django 4.2, PostgreSQL, ag-Grid, Python 3.13
- **GitHub:** https://github.com/emilaliyev17/conspy (public repo)
- **Reference:** https://docs.google.com/spreadsheets/d/1v5TDUH2coPmyioVuLhP8F139TtBRMriXpL6Ls42Cg80/

## ⚠️ CRITICAL PRINCIPLES
1. **NEVER hardcode company names** - always use database queries
2. **Company names are temporary** (F2Fin, GLOB will change after deploy)
3. **Test before changes** - modules are interconnected
4. **Small incremental changes** - one feature at a time
5. **Protect from "optimizations"** - devs see only fragments

## ✅ COMPLETED WORK (Current Session)

### CF Dashboard
- All 9 metrics working with inline editing
- YTD calculations fixed (TOTAL accumulates correctly)
- "Loan book at month end" implemented
- Metrics list: Loans advanced, Loans repaid (YTD), Cumulative loan completions (YTD), Loan book at month end, Fund LLC, Faes & Co US, OK, Triple Point, Fund investment received

### P&L Report Improvements
- Removed empty REVENUE header row
- Hidden zero values (empty cells instead of 0.00)
- Sub-category headers bold (INTEREST + DEFAULT, etc.)
- Database-driven grouping via ChartOfAccounts.sub_category

## 🚧 IN PROGRESS: Budget/Forecast Integration

### Current Problem
- Budget/Forecast is consolidated (one for all companies)
- System expects per-company data
- Need to show only TOTAL column for Budget/Forecast

### Target Structure
Actual: | Jan-24 F2 | Jan-24 Global | Jan-24 TOTAL |
Budget: |           Jan-24 Budget TOTAL           |

### Critical Dependencies Found
- Periods depend on FinancialData filtered by data_type
- CF Dashboard uses P&L periods but lacks data_type field
- TOTAL calculations assume summation (breaks for Budget)
- 14 places calculate TOTAL (6 P&L, 8 Balance Sheet)

## 📋 NEXT TASKS
1. Complete Budget/Forecast integration
2. Add GROSS PROFIT = Income + Interest - Cost of Funds
3. Add NET PROFIT = GROSS PROFIT - OVERHEADS
4. Balance Sheet implementation
5. Drill-down for Salaries

## 🔧 TECHNICAL DETAILS

### Key Files
- core/views.py - Main logic (pl_report_data starts line 558)
- core/models.py - Data models
- core/templates/core/pl_report.html - Frontend

### Database Structure
- Company: name, code (unique)
- FinancialData: company(FK), account_code, period, amount, data_type
- ChartOfAccounts: account_code, account_name, sub_category
- CFDashboardMetric/Data: Separate CF system

## 🔄 RUN COMMANDS
```bash
cd "/Users/emil.aliyev/My Projects/financial_consolidator"
venv/bin/python manage.py runserver
# P&L: http://127.0.0.1:8000/reports/pl/
# Admin: http://127.0.0.1:8000/admin/
```

⚠️ PROMPT TEMPLATE FOR CODEX
Always use:
⚠️ CRITICAL INSTRUCTION FOR CODEX ⚠️
📋 MANDATORY: Read CONTEXT.md and PROJECT_STATUS.md FIRST
[CONTEXT: description]
IMPORTANT:

❌ DO NOT DELETE [specify]
✅ ONLY [task]

## 🔍 PERIOD LOGIC ANALYSIS
- Current logic:
  - Periods for P&L are derived from `FinancialData` filtered by `data_type`, limited to P&L accounts, optional company set, and the selected date range. Core block: `core/views.py:596-609` and response on empty: `core/views.py:611-641`.
  - Date range handling is inclusive of the selected months by computing `[start, end_exclusive)` where `start = first_day(from_month)` and `end_exclusive = first_day(to_month + 1)`. Helpers: `month_start`, `next_month`; range setup: `core/views.py:572-579`.
  - Period list is built as `periods = list(q.values_list('period', flat=True).distinct().order_by('period'))` — `core/views.py:608`.
- Dependencies (usage of `periods`):
  - Column generation loops over `periods` to add per-company and per-period TOTAL columns — `core/views.py:1063-1098`.
  - Data matrix initialization and all calculations iterate `periods` to populate row values and totals (multiple spots: income/expense rows, subtotals, totals, net income) — e.g., `core/views.py:796-1038`.
  - CF Dashboard iterates the same `periods` when building CF rows (regular, YTD, Cumulative) — `core/views.py:1135`.
  - Balance Sheet uses its own period derivation in `bs_report_data` (separate function) and is unaffected by P&L `periods`.
- CF Dashboard dependency:
  - Uses the same `periods` list from P&L; CF queries its own data (`CFDashboardData`) over the selected date range, but rendering rows runs inside `for period in periods` — `core/views.py:1101-1167`, `core/views.py:1135`.
  - If `periods` is empty, P&L returns early with empty JSON, so CF section never executes.
- Behavior when `periods` is empty:
  - Column generation: no period columns (returns `columnDefs: []`) — `core/views.py:637-641`.
  - Row calculations: skipped; `rowData: []` returned — `core/views.py:637-641`.
  - CF Dashboard: not executed because function returns early before CF block — `core/views.py:635-641`.
  - TOTAL calculations: none performed (the rows that compute TOTALs are not built).
- `data_type` filtering chain and impact:
  - `data_type` captured from querystring with default `'actual'` — `core/views.py:565`.
  - Applied to period discovery and data fetch: `FinancialData.objects.filter(data_type=data_type, ...)` — `core/views.py:598-601`, `core/views.py:644-651`.
  - Direct impact: if Budget/Forecast data is not present for the selected range, `periods` becomes empty → entire P&L (and CF Dashboard) return empty structures for that request.
  - CF Dashboard does not filter by `data_type`, but still depends on `periods` computed from P&L, so absence of Budget/Forecast FinancialData suppresses CF rendering.
- Risk points:
  - Tight coupling of CF Dashboard to P&L `periods` means Budget/Forecast views without matching FinancialData hide CF entirely.
  - Inclusive date range relies on correct parsing of from/to month-year; malformed inputs yield empty `periods`.
  - P&L limits periods to P&L accounts (`INCOME`/`EXPENSE` via account_code filter); missing COA codes or mismatches reduce visible periods.
- Safe to change: yes, with conditions:
  - If introducing Budget/Forecast display without per-company data, either (a) seed `FinancialData` for the target `data_type` and period range, or (b) decouple CF periods from P&L’s `periods` and/or relax period derivation to use explicit date range when no data exists.
  - Preserve `[start, end_exclusive)` logic to avoid off-by-one month errors.

## 🔍 CF DASHBOARD BUDGET ANALYSIS
### Current Structure:
- Models:
  - `CFDashboardMetric(id, metric_name, metric_code, display_order, is_active)` with ordering on `display_order, metric_name` — defines the set and order of metrics.
  - `CFDashboardData(id, company(FK), period(Date), metric(FK), value)` with `unique_together = (company, period, metric)` — one value per company-month-metric.
- Views (P&L endpoint `pl_report_data`):
  - CF block starts after P&L columnDefs; metrics fetched via `CFDashboardMetric.objects.filter(is_active=True)`.
  - CF data fetched via `CFDashboardData` filtered by selected companies and by `from_date_start..to_date_end` (no `data_type`).
  - Rows built per metric with flags `is_cf_dashboard=True` and `metric_id` attached for editing.
  - Iterates the same `periods` list as P&L; per-company fields use the same column naming `"%b-%y"_COMPANYCODE` ensuring alignment.
  - Supports two behaviors by metric name: contains "Cumulative" (running total using prior month + "Loans advanced in month") and contains "YTD" (year-to-date accumulation at TOTAL level).
- Frontend (pl_report.html):
  - Grid cells are editable only when `row.is_cf_dashboard === true`.
  - `onCellValueChanged` parses `colId` as `<Mon-YY>_<COMPANYCODE>`, posts JSON to `/api/cf-dashboard/update/` with `{metric_id, company_code, period, value}` and optimistic UI update; on failure rolls back.
- Update endpoint (`update_cf_dashboard`):
  - Parses `period` in two formats: `Mon-YY` or `YYYYMM` → first day of month.
  - Resolves `Company` by `company_code` (case-insensitive) and `CFDashboardMetric` by `metric_id`.
  - Upserts `CFDashboardData` via `update_or_create`.

### Integration Points:
1. Periods list from P&L drives CF columns and iteration.
2. Column naming shares the P&L convention `<Mon-YY>_<COMPANYCODE>` so CF aligns under the same headers.
3. CF data range uses filter `from_date_start..to_date_end` (independent of `data_type`).
4. Editable gating via `is_cf_dashboard` flag in row objects.
5. AJAX payload schema `{metric_id, company_code, period, value}` matches server expectations.
6. Metric semantics controlled by `metric_name` (contains "Cumulative"/"YTD").

### Risks:
- Adding a Budget column without corresponding `periods` (when viewing Budget `data_type` and no Budget FinancialData) results in CF not rendering at all, because CF loops the P&L `periods` and the view returns early on empty periods.
- Introducing Budget values for CF without separating them from Actual could commingle data, since `CFDashboardData` has no `data_type`; writing Budget into the same rows would overwrite Actual.
- Column alignment must remain identical to P&L; any alternative header naming for Budget would break `onCellValueChanged` parsing logic.
- Inline editing currently assumes company-specific cells; a single Budget TOTAL column (no company split) would not map cleanly to `<Mon-YY>_<COMPANYCODE>` parsing.

### Safe Implementation Path:
1. Decide storage model for Budget CF: either extend `CFDashboardData` with a `data_type` field or create a parallel table; avoid overwriting Actual.
2. Period sourcing: when viewing Budget, ensure `periods` is non-empty (seed minimal `FinancialData` for Budget or decouple CF periods from P&L by deriving from date selectors when `periods` is empty).
3. Column design: keep the same `<Mon-YY>_<COMPANYCODE>` convention; if only TOTAL is needed for Budget, introduce a synthetic company code like `BUDGET` consistently, or add separate `'<Mon-YY>_TOTAL'` mapping with custom edit handler.
4. Inline editing: preserve `is_cf_dashboard` flag; extend `onCellValueChanged` to recognize the Budget column mapping while keeping the existing Actual path intact (server must distinguish Actual vs Budget).
5. Update endpoint: accept an optional `data_type` or `scope` parameter to route writes to Budget storage; maintain backward compatibility for existing Actual writes.
6. Validation: test with mixed views (Actual vs Budget) to confirm CF rows render and edits commit to the correct dataset; verify no changes to P&L calculations and columnDefs under Actual.
