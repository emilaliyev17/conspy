from django.core.management.base import BaseCommand
from core.models import FinancialData

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Fix all periods to use first day of month
        for record in FinancialData.objects.all():
            record.period = record.period.replace(day=1)
            record.save()
        print("Fixed all period dates to first of month")
