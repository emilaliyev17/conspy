from django.core.management.base import BaseCommand
from core.models import ChartOfAccounts

class Command(BaseCommand):
    help = 'Fix account types based on ChartOfAccounts'

    def handle(self, *args, **options):
        type_mapping = {
            # Standard mappings
            'ASSET': 'ASSET',
            'LIABILITY': 'LIABILITY',
            'EQUITY': 'EQUITY',
            'INCOME': 'INCOME',
            'EXPENSE': 'EXPENSE',
            
            # QuickBooks-style mappings for Balance Sheet
            'BANK': 'ASSET',
            'FIXED ASSET': 'ASSET',
            'OTHER CURRENT ASSET': 'ASSET',
            'OTHER ASSET': 'ASSET',
            'OTHER CURRENT LIABILITIES': 'LIABILITY',
            'OTHER CURRENT LIABILITY': 'LIABILITY',
            
            # QuickBooks-style mappings for P&L
            'COST OF GOODS SOLD': 'EXPENSE',
            'COGS': 'EXPENSE',
        }
        
        updated_count = 0
        for chart_account in ChartOfAccounts.objects.all():
            if chart_account.account_type:
                original_type = chart_account.account_type
                new_type = type_mapping.get(
                    original_type.upper(), 
                    original_type
                )
                if original_type != new_type:
                    chart_account.account_type = new_type
                    chart_account.save()
                    updated_count += 1
                    self.stdout.write(
                        f"Updated {chart_account.account_code}: {original_type} -> {new_type}"
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} accounts')
        )
