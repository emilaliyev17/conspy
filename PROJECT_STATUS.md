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
