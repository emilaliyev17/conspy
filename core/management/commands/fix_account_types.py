from django.core.management.base import BaseCommand
from core.models import Account, ChartOfAccounts

class Command(BaseCommand):
    help = 'Fix account types based on ChartOfAccounts'

    def handle(self, *args, **options):
        type_mapping = {
            # Standard mappings
            'ASSET': 'asset',
            'LIABILITY': 'liability',
            'EQUITY': 'equity',
            'INCOME': 'revenue',
            'EXPENSE': 'expense',
            
            # QuickBooks-style mappings for Balance Sheet
            'BANK': 'asset',
            'FIXED ASSET': 'asset',
            'OTHER CURRENT ASSET': 'asset',
            'OTHER ASSET': 'asset',
            'OTHER CURRENT LIABILITIES': 'liability',
            'OTHER CURRENT LIABILITY': 'liability',
            
            # QuickBooks-style mappings for P&L
            'INCOME': 'revenue',
            'COST OF GOODS SOLD': 'expense',
            'COGS': 'expense',
        }
        
        updated_count = 0
        for account in Account.objects.all():
            chart_account = ChartOfAccounts.objects.filter(
                account_code=account.code
            ).first()
            
            if chart_account and chart_account.account_type:
                new_type = type_mapping.get(
                    chart_account.account_type.upper(), 
                    account.type
                )
                if account.type != new_type:
                    account.type = new_type
                    account.save()
                    updated_count += 1
                    self.stdout.write(
                        f"Updated {account.code}: {account.type} -> {new_type}"
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} accounts')
        )
