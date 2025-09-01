from core.models import ChartOfAccounts, FinancialData
from django.db.models import Sum
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def get_report_structure(report_type='PL'):
    """
    Получает структуру отчета на основе ChartOfAccounts.
    report_type: 'PL' для P&L или 'BS' для Balance Sheet
    """
    if report_type == 'PL':
        account_types = ['INCOME', 'EXPENSE']
    else:  # BS
        account_types = ['ASSET', 'LIABILITY', 'EQUITY']
    
    # Получаем все счета нужного типа
    accounts = ChartOfAccounts.objects.filter(
        account_type__in=account_types
    ).order_by('sort_order')
    
    # Строим иерархию
    structure = []
    parent_map = {}
    
    for account in accounts:
        if not account.account_code:  # Это заголовок/категория
            structure.append({
                'type': 'header',
                'name': account.account_name,
                'parent_category': account.parent_category,
                'sub_category': account.sub_category,
                'sort_order': account.sort_order,
                'children': []
            })
            parent_map[account.account_name] = structure[-1]
        else:  # Это счет с кодом
            account_data = {
                'type': 'account',
                'code': account.account_code,
                'name': account.account_name,
                'account_type': account.account_type,
                'parent_category': account.parent_category,
                'sub_category': account.sub_category,
                'sort_order': account.sort_order
            }
            
            # Добавляем в правильное место иерархии
            if account.sub_category and account.sub_category in parent_map:
                parent_map[account.sub_category]['children'].append(account_data)
            elif account.parent_category and account.parent_category in parent_map:
                parent_map[account.parent_category]['children'].append(account_data)
            else:
                structure.append(account_data)
    
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
