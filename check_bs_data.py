#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financial_consolidator.settings')
django.setup()

from core.models import ChartOfAccounts, FinancialData

print("=== BALANCE SHEET DATA INVESTIGATION ===")
print()

# Check Chart of Accounts for Balance Sheet account types
print("1. Checking Chart of Accounts for Balance Sheet account types:")
try:
    assets = ChartOfAccounts.objects.filter(account_type='ASSET').count()
    liabilities = ChartOfAccounts.objects.filter(account_type='LIABILITY').count()  
    equity = ChartOfAccounts.objects.filter(account_type='EQUITY').count()
    print(f"   ASSET accounts: {assets}")
    print(f"   LIABILITY accounts: {liabilities}")
    print(f"   EQUITY accounts: {equity}")
except Exception as e:
    print(f"   Error checking account types: {e}")

print()

# Check what account types actually exist
print("2. Checking what account types actually exist:")
try:
    types = ChartOfAccounts.objects.values_list('account_type', flat=True).distinct()
    print("   Account types in database:", list(types))
except Exception as e:
    print(f"   Error checking account types: {e}")

print()

# Check if there's any FinancialData for Balance Sheet accounts
print("3. Checking FinancialData for Balance Sheet accounts:")
try:
    bs_accounts = ChartOfAccounts.objects.filter(account_type__in=['ASSET', 'LIABILITY', 'EQUITY'])
    print(f"   Found {bs_accounts.count()} Balance Sheet accounts in Chart of Accounts")
    
    if bs_accounts.exists():
        bs_data = FinancialData.objects.filter(account_code__in=bs_accounts.values_list('account_code', flat=True)).count()
        print(f"   FinancialData entries for Balance Sheet accounts: {bs_data}")
    else:
        print("   No Balance Sheet accounts found, so no FinancialData to check")
except Exception as e:
    print(f"   Error checking FinancialData: {e}")

print()

# Check total Chart of Accounts entries
print("4. Total Chart of Accounts entries:")
try:
    total_accounts = ChartOfAccounts.objects.count()
    print(f"   Total Chart of Accounts entries: {total_accounts}")
except Exception as e:
    print(f"   Error counting accounts: {e}")

print()

# Check total FinancialData entries
print("5. Total FinancialData entries:")
try:
    total_financial_data = FinancialData.objects.count()
    print(f"   Total FinancialData entries: {total_financial_data}")
except Exception as e:
    print(f"   Error counting financial data: {e}")

print()

# Check sample account names and types
print("6. Sample Chart of Accounts entries:")
try:
    sample_accounts = ChartOfAccounts.objects.all()[:10]
    for account in sample_accounts:
        print(f"   {account.account_code} - {account.account_name} - {account.account_type}")
except Exception as e:
    print(f"   Error getting sample accounts: {e}")

print()
print("=== INVESTIGATION COMPLETE ===")

