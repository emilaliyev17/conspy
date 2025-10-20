from django.core.management.base import BaseCommand
from core.models import Company, FinancialData, ChartOfAccounts
from datetime import date
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load test data for P&L report testing'

    def handle(self, *args, **options):
        # Create test companies
        company_a, created = Company.objects.get_or_create(code='F2001', defaults={'name': 'Company F2001', 'is_budget_only': False})
        company_b, created = Company.objects.get_or_create(code='GL001', defaults={'name': 'Company GL001', 'is_budget_only': False})
        
        # Create test Chart of Accounts
        ChartOfAccounts.objects.get_or_create(
            account_code='4000', 
            defaults={
                'account_name': 'Revenue', 
                'account_type': 'INCOME',
                'sort_order': 1,
                'parent_category': 'INCOME',
                'sub_category': 'Revenue'
            }
        )
        ChartOfAccounts.objects.get_or_create(
            account_code='5000', 
            defaults={
                'account_name': 'Expenses', 
                'account_type': 'EXPENSE',
                'sort_order': 2,
                'parent_category': 'OVERHEADS',
                'sub_category': 'Operating Expenses'
            }
        )
        
        self.stdout.write('Test data created successfully')

