from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import FinancialData, ChartOfAccounts
from decimal import Decimal


class Command(BaseCommand):
    help = 'Очистка P&L данных (Income и Expense)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет удалено без фактического удаления',
        )
        parser.add_argument(
            '--account-type',
            choices=['INCOME', 'EXPENSE', 'BOTH'],
            default='BOTH',
            help='Тип счетов для очистки (INCOME, EXPENSE, BOTH)',
        )
        parser.add_argument(
            '--period-start',
            help='Начальная дата периода (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--period-end',
            help='Конечная дата периода (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--company',
            help='Код компании для очистки',
        )
        parser.add_argument(
            '--data-type',
            choices=['actual', 'budget', 'forecast'],
            default='actual',
            help='Тип данных для очистки',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        account_type = options['account_type']
        period_start = options['period_start']
        period_end = options['period_end']
        company_code = options['company']
        data_type = options['data_type']

        # Получаем P&L account_codes
        if account_type == 'BOTH':
            account_types = ['INCOME', 'EXPENSE']
        else:
            account_types = [account_type]

        pl_accounts = ChartOfAccounts.objects.filter(
            account_type__in=account_types
        ).values_list('account_code', flat=True)

        if not pl_accounts:
            self.stdout.write(
                self.style.WARNING('Не найдено P&L счетов для очистки')
            )
            return

        # Строим фильтр
        filter_kwargs = {
            'account_code__in': pl_accounts,
            'data_type': data_type
        }

        if period_start:
            filter_kwargs['period__gte'] = period_start
        if period_end:
            filter_kwargs['period__lte'] = period_end
        if company_code:
            filter_kwargs['company__code'] = company_code

        # Получаем данные для удаления
        data_to_delete = FinancialData.objects.filter(**filter_kwargs)
        count = data_to_delete.count()

        if count == 0:
            self.stdout.write(
                self.style.WARNING('Не найдено P&L данных для очистки')
            )
            return

        # Показываем статистику
        self.stdout.write(f'Найдено {count} P&L записей для удаления:')
        self.stdout.write(f'  - Тип счетов: {", ".join(account_types)}')
        self.stdout.write(f'  - Тип данных: {data_type}')
        
        if period_start:
            self.stdout.write(f'  - Период с: {period_start}')
        if period_end:
            self.stdout.write(f'  - Период по: {period_end}')
        if company_code:
            self.stdout.write(f'  - Компания: {company_code}')

        # Показываем примеры данных
        sample_data = data_to_delete[:5]
        self.stdout.write('\nПримеры данных для удаления:')
        for fd in sample_data:
            self.stdout.write(
                f'  - {fd.company.code} | {fd.account_code} | {fd.period} | {fd.amount}'
            )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nDRY RUN: Будет удалено {count} записей')
            )
            return

        # Подтверждение
        confirm = input(f'\nВы уверены что хотите удалить {count} P&L записей? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Операция отменена')
            return

        # Удаляем данные
        with transaction.atomic():
            deleted_count = data_to_delete.delete()[0]
            
        self.stdout.write(
            self.style.SUCCESS(f'Успешно удалено {deleted_count} P&L записей')
        )

        # Показываем оставшиеся P&L данные
        remaining_count = FinancialData.objects.filter(
            account_code__in=pl_accounts
        ).count()
        
        self.stdout.write(f'Осталось P&L записей в базе: {remaining_count}')
