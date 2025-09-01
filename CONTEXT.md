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

## TEST PROTOCOL (Required after ANY change)
1. ✓ Filters persist across page refresh
2. ✓ Headers visible during vertical scroll
3. ✓ Headers visible during horizontal scroll
4. ✓ No console errors
5. ✓ No performance degradation

## CHANGE REQUEST FORMAT
Task: [One specific change]
File: [Exact file path]
Line: [Line numbers if known]
Constraint: [What NOT to touch]
Success: [Observable result]

## CONSEQUENCES OF VIOLATIONS
- Cursor AI: TERMINATED for unauthorized refactoring
- Gemini CLI: TERMINATED for unsolicited improvements
- Premium subscriptions: CANCELLED

## THE ONLY RULE
**If you weren't asked to change it, DON'T TOUCH IT.**

## SHORT REMINDER FOR EACH REQUEST
Production financial system. Executor-only. No unsolicited changes. Use IDs: from_month, from_year, to_month, to_year, data_type. Touch only files/lines specified. Preserve ag-Grid behavior and loadPLData(). Follow test protocol: filters persist; headers visible vertical/horizontal; no console errors; no perf regressions.

