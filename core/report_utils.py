from core.models import ChartOfAccounts, FinancialData
from django.db.models import Sum
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def get_report_structure(report_type='PL'):
    """
    Получает структуру отчета на основе ChartOfAccounts.
    Группирует счета по sub_category автоматически.
    """
    if report_type == 'PL':
        account_types = ['INCOME', 'EXPENSE']
    else:  # BS
        account_types = ['ASSET', 'LIABILITY', 'EQUITY']
    
    # Получаем все счета с кодами
    accounts = ChartOfAccounts.objects.filter(
        account_type__in=account_types,
        account_code__isnull=False
    ).exclude(
        account_code=''
    ).order_by('sort_order')
    
    # Группируем по sub_category
    structure = []
    categories = {}
    
    for account in accounts:
        sub_cat = account.sub_category or 'UNCATEGORIZED'
        
        # Создаем категорию если её еще нет
        if sub_cat not in categories:
            category = {
                'type': 'header',
                'name': sub_cat,
                'sort_order': account.sort_order,  # Берем sort_order первого счета
                'children': []
            }
            categories[sub_cat] = category
            structure.append(category)
        
        # Добавляем счет в категорию
        account_data = {
            'type': 'account',
            'code': account.account_code,
            'name': account.account_name,
            'account_type': account.account_type,
            'sort_order': account.sort_order
        }
        categories[sub_cat]['children'].append(account_data)
    
    # Сортируем структуру по sort_order
    structure.sort(key=lambda x: x['sort_order'])
    
    return structure

def test_structure():
    """Тестовая функция для проверки структуры"""
    pl_structure = get_report_structure('PL')
    logger.info(f"P&L Structure items: {len(pl_structure)}")
    
    bs_structure = get_report_structure('BS')
    logger.info(f"BS Structure items: {len(bs_structure)}")
    
    return {
        'pl_count': len(pl_structure),
        'bs_count': len(bs_structure)
    }

def generate_report_data(company, periods, report_type='PL'):
    """
    Генерирует данные отчета на основе структуры ChartOfAccounts.
    
    Args:
        company: объект Company
        periods: список дат (date objects)
        report_type: 'PL' или 'BS'
    
    Returns:
        list: список строк отчета с данными
    """
    from decimal import Decimal
    
    structure = get_report_structure(report_type)
    
    # Получаем все account_codes из структуры
    all_account_codes = []
    for category in structure:
        for child in category.get('children', []):
            if child.get('code'):
                all_account_codes.append(child['code'])
    
    # Получаем данные из FinancialData
    financial_data = FinancialData.objects.filter(
        company=company,
        period__in=periods,
        account_code__in=all_account_codes
    )
    
    # Индексируем данные для быстрого доступа
    data_index = {}
    for fd in financial_data:
        key = (fd.period, fd.account_code)
        data_index[key] = fd.amount
    
    # Формируем отчет
    report_rows = []
    
    for category in structure:
        # Добавляем заголовок категории
        header_row = {
            'type': 'header',
            'name': category['name'],
            'code': '',
            'periods': {p: None for p in periods}
        }
        report_rows.append(header_row)
        
        # Обрабатываем счета в категории
        category_totals = {p: Decimal('0') for p in periods}
        
        for account in category.get('children', []):
            account_row = {
                'type': 'account',
                'name': account['name'],
                'code': account['code'],
                'periods': {}
            }
            
            for period in periods:
                amount = data_index.get((period, account['code']), Decimal('0'))
                account_row['periods'][period] = float(amount)
                category_totals[period] += amount
            
            report_rows.append(account_row)
        
        # Добавляем итог по категории
        subtotal_row = {
            'type': 'subtotal',
            'name': f"Total {category['name']}",
            'code': '',
            'periods': {p: float(category_totals[p]) for p in periods}
        }
        report_rows.append(subtotal_row)
    
    return report_rows
