#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financial_consolidator.settings')
django.setup()

from core.models import ChartOfAccounts

def create_chart_accounts():
    """Create ChartOfAccounts entries for P&L accounts."""
    
    # P&L Account structure
    accounts_data = [
        # INCOME accounts
        {'account_code': '4113000', 'account_name': 'Interest Income - Deposits', 'parent_category': 'INCOME', 'sub_category': 'Interest Income', 'account_type': 'INCOME', 'sort_order': 1},
        {'account_code': '4113200', 'account_name': 'Interest Income - Loans', 'parent_category': 'INCOME', 'sub_category': 'Interest Income', 'account_type': 'INCOME', 'sort_order': 2},
        {'account_code': '4115100', 'account_name': 'Fee Income - Account Maintenance', 'parent_category': 'INCOME', 'sub_category': 'Fee Income', 'account_type': 'INCOME', 'sort_order': 3},
        
        # COST OF FUNDS accounts
        {'account_code': '5215000', 'account_name': 'Interest Expense - Deposits', 'parent_category': 'COST OF FUNDS', 'sub_category': 'Interest Expense', 'account_type': 'EXPENSE', 'sort_order': 4},
        {'account_code': '5216000', 'account_name': 'Interest Expense - Borrowings', 'parent_category': 'COST OF FUNDS', 'sub_category': 'Interest Expense', 'account_type': 'EXPENSE', 'sort_order': 5},
        
        # OVERHEADS accounts
        {'account_code': '6011100', 'account_name': 'Basic Salary', 'parent_category': 'OVERHEADS', 'sub_category': 'Salaries', 'account_type': 'EXPENSE', 'sort_order': 6},
        {'account_code': '6011200', 'account_name': 'Overtime', 'parent_category': 'OVERHEADS', 'sub_category': 'Salaries', 'account_type': 'EXPENSE', 'sort_order': 7},
        {'account_code': '6011202', 'account_name': 'Marketing Expense', 'parent_category': 'OVERHEADS', 'sub_category': 'Marketing', 'account_type': 'EXPENSE', 'sort_order': 8},
        
        # TAXES accounts
        {'account_code': '7010000', 'account_name': 'Income Tax', 'parent_category': 'TAXES', 'sub_category': 'Income Tax', 'account_type': 'EXPENSE', 'sort_order': 9},
    ]
    
    created_count = 0
    for account_data in accounts_data:
        account, created = ChartOfAccounts.objects.get_or_create(
            account_code=account_data['account_code'],
            defaults=account_data
        )
        if created:
            created_count += 1
            print(f"Created: {account.account_code} - {account.account_name}")
        else:
            print(f"Already exists: {account.account_code} - {account.account_name}")
    
    print(f"\nTotal created: {created_count}")

if __name__ == '__main__':
    create_chart_accounts()
