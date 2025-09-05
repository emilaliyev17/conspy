from django.core.management.base import BaseCommand
from core.models import Company, Account, FinancialData, ChartOfAccounts
from datetime import date
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load test data for P&L report testing'

    def handle(self, *args, **options):
        Company.objects.get_or_create(code='A', defaults={'name': 'Company A', 'is_budget_only': False})
        Company.objects.get_or_create(code='B', defaults={'name': 'Company B', 'is_budget_only': False})
        Company.objects.get_or_create(code='F', defaults={'name': 'Company F', 'is_budget_only': True})
        Account.objects.get_or_create(code='4000', defaults={'name': 'Revenue', 'type': 'INCOME'})
        Account.objects.get_or_create(code='5000', defaults={'name': 'Expenses', 'type': 'EXPENSE'})
        self.stdout.write('Test data created')

