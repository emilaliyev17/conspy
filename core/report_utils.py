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
