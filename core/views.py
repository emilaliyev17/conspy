from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from .models import Company, Account, FinancialData, ChartOfAccounts, DataBackup
import json
import pandas as pd
import csv
from datetime import datetime
import calendar
from django.db.models import Sum
from django.template.defaultfilters import register
import re
from decimal import Decimal, InvalidOperation
import logging

# Set up logging
logger = logging.getLogger(__name__)

def clean_number_value(value):
    """
    Clean and parse number values from Excel, handling various formats.
    
    Args:
        value: The raw value from Excel (could be string, number, or None)
    
    Returns:
        Decimal: Parsed number value
        None: If value is empty/null/not parseable
    """
    if value is None or pd.isna(value):
        return None
    
    # Convert to string and strip whitespace
    value_str = str(value).strip()
    
    # Handle empty strings
    if not value_str or value_str == '':
        return None
    
    # Remove apostrophes and quotes from beginning and end
    value_str = value_str.strip("'\"")
    
    # Remove spaces
    value_str = value_str.replace(' ', '')
    
    # Handle negative numbers in parentheses: (1,234.56) -> -1234.56
    if value_str.startswith('(') and value_str.endswith(')'):
        value_str = '-' + value_str[1:-1]
    
    # Remove thousand separators (commas)
    value_str = value_str.replace(',', '')
    
    # Try to parse as decimal
    try:
        return Decimal(value_str)
    except (InvalidOperation, ValueError):
        return None

def home(request):
    """Home page view with navigation to upload functionality."""
    return render(request, 'core/home.html')

def chart_of_accounts_view(request):
    """View for displaying Chart of Accounts with search and hierarchical display."""
    # Get search parameter
    search_query = request.GET.get('search', '')
    
    # Get all ChartOfAccounts records ordered by sort_order
    accounts = ChartOfAccounts.objects.all().order_by('sort_order')
    
    # Apply search filter if provided
    if search_query:
        accounts = accounts.filter(
            Q(account_code__icontains=search_query) |
            Q(account_name__icontains=search_query) |
            Q(account_type__icontains=search_query) |
            Q(parent_category__icontains=search_query) |
            Q(sub_category__icontains=search_query)
        )
    
    # Prepare hierarchical data
    hierarchical_accounts = []
    parent_categories = {}
    
    for account in accounts:
        if account.parent_category:
            if account.parent_category not in parent_categories:
                parent_categories[account.parent_category] = []
            parent_categories[account.parent_category].append(account)
        else:
            hierarchical_accounts.append(account)
    
    # Add accounts with parent categories
    for parent_category, sub_accounts in parent_categories.items():
        # Add parent category as header if it doesn't exist
        parent_header = next((acc for acc in hierarchical_accounts if acc.account_name == parent_category), None)
        if not parent_header:
            hierarchical_accounts.append(ChartOfAccounts(
                account_name=parent_category,
                is_header=True,
                sort_order=min(sub_accounts, key=lambda x: x.sort_order).sort_order - 1
            ))
        
        # Add sub-accounts
        hierarchical_accounts.extend(sub_accounts)
    
    # Sort by sort_order
    hierarchical_accounts.sort(key=lambda x: x.sort_order)
    
    context = {
        'accounts': hierarchical_accounts,
        'search_query': search_query,
    }
    
    return render(request, 'core/chart_of_accounts_simple.html', context)

@csrf_exempt
def download_chart_of_accounts(request):
    """Download Chart of Accounts as CSV/Excel."""
    # Get all ChartOfAccounts records ordered by sort_order
    accounts = ChartOfAccounts.objects.all().order_by('sort_order')
    
    # Get format parameter (csv or excel)
    format_type = request.GET.get('format', 'csv')
    
    if format_type == 'excel':
        # Create Excel file
        data = []
        for account in accounts:
            data.append([
                account.sort_order,
                account.account_code or '',
                account.account_name,
                account.account_type or '',
                account.parent_category or '',
                account.sub_category or ''
            ])
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=[
            'Sort Order', 'Account Code', 'Account Name', 'Type', 'Parent Category', 'Sub Category'
        ])
        
        # Create Excel response
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="chart_of_accounts_{datetime.now().strftime("%Y%m%d")}.xlsx"'
        
        # Write to Excel
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Chart of Accounts', index=False)
        
        return response
    else:
        # Create CSV file
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="chart_of_accounts_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow(['Sort Order', 'Account Code', 'Account Name', 'Type', 'Parent Category', 'Sub Category'])
        
        # Write data
        for account in accounts:
            writer.writerow([
                account.sort_order,
                account.account_code or '',
                account.account_name,
                account.account_type or '',
                account.parent_category or '',
                account.sub_category or ''
            ])
        
        return response

def convert_month_to_date_range(month_str):
    """Convert month string (YYYY-MM) to date range (first day to last day of month)."""
    if not month_str:
        return None, None
    
    try:
        from datetime import datetime, date
        import calendar
        
        # Parse the month string (YYYY-MM format)
        year, month = map(int, month_str.split('-'))
        
        # Get first day of month
        first_day = date(year, month, 1)
        
        # Get last day of month
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        
        return first_day, last_day
    except (ValueError, AttributeError):
        return None, None

def convert_month_year_to_date_range(month, year):
    """Convert separate month and year to date range (first day to last day of month)."""
    if not month or not year:
        return None, None
    
    try:
        from datetime import datetime, date
        import calendar
        
        # Parse month and year
        month_int = int(month)
        year_int = int(year)
        
        # Get first day of month
        first_day = date(year_int, month_int, 1)
        
        # Get last day of month
        last_day = date(year_int, month_int, calendar.monthrange(year_int, month_int)[1])
        
        return first_day, last_day
    except (ValueError, AttributeError):
        return None, None

def pl_report(request):
    """P&L Report view with hierarchical grouping by parent_category and sub_category."""
    # Get filter parameters
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    
    # Convert month/year inputs to date ranges
    from_date_start, from_date_end = convert_month_year_to_date_range(from_month, from_year)
    to_date_start, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    
    # Generate year range for dropdown (2023-2030)
    year_range = range(2023, 2031)
    
    logger.info(f"P&L Report - Filters: from_month={from_month}, from_year={from_year}, to_month={to_month}, to_year={to_year}, data_type={data_type}")
    
    # Get all companies
    companies = list(Company.objects.all().order_by('name'))
    logger.info(f"Found {len(companies)} companies")
    
    # Get INCOME and EXPENSE accounts ordered by sort_order
    accounts = list(ChartOfAccounts.objects.filter(
        account_type__in=['INCOME', 'EXPENSE', 'Income', 'Expense']
    ).order_by('sort_order'))
    logger.info(f"Found {len(accounts)} INCOME/EXPENSE accounts in ChartOfAccounts")
    
    # Get unique periods from FinancialData with proper filtering
    try:
        financial_data_query = FinancialData.objects.filter(data_type=data_type)
        
        if from_date_start:
            financial_data_query = financial_data_query.filter(period__gte=from_date_start)
        if to_date_end:
            financial_data_query = financial_data_query.filter(period__lte=to_date_end)
        
        periods = list(financial_data_query.values_list('period', flat=True).distinct().order_by('period'))
        logger.info(f"Found {len(periods)} periods in FinancialData")
    except Exception as e:
        logger.error(f"Error getting periods: {e}")
        periods = []
    
    # Debug info
    total_financial_records = FinancialData.objects.count()
    data_type_records = FinancialData.objects.filter(data_type=data_type).count()
    
    # If no periods or accounts, return empty report
    if not periods or not accounts:
        context = {
            'report_data': [],
            'companies': companies,
            'periods': [],
            'from_month': from_month,
            'from_year': from_year,
            'to_month': to_month,
            'to_year': to_year,
            'data_type': data_type,
            'report_type': 'pl',
            'year_range': year_range,
            'debug_info': {
                'total_financial_records': total_financial_records,
                'data_type_records': data_type_records,
                'accounts_found': len(accounts),
                'companies_found': len(companies),
                'periods_found': len(periods)
            }
        }
        return render(request, 'core/pl_report.html', context)
    
    # Group accounts by parent_category and sub_category
    grouped_data = {}
    
    for account in accounts:
        parent_category = account.parent_category or 'UNCATEGORIZED'
        sub_category = account.sub_category or 'UNCATEGORIZED'
        
        if parent_category not in grouped_data:
            grouped_data[parent_category] = {}
        
        if sub_category not in grouped_data[parent_category]:
            grouped_data[parent_category][sub_category] = []
        
        grouped_data[parent_category][sub_category].append(account)
    
    # Prepare hierarchical report data
    report_data = []
    
    # Process each parent category
    for parent_category, sub_categories in grouped_data.items():
        # Calculate parent category totals
        parent_totals = {}
        parent_total_overall = 0
        parent_periods = {}
        
        # Process each sub category
        for sub_category, sub_accounts in sub_categories.items():
            # Calculate sub category totals
            sub_totals = {}
            sub_total_overall = 0
            sub_periods = {}
            
            # Process individual accounts in this sub category
            for account in sub_accounts:
                logger.info(f"Processing account: {account.account_code} - {account.account_name}")
                
                row_data = {
                    'type': 'account',
                    'account_code': account.account_code or '',
                    'account_name': account.account_name,
                    'account_type': account.account_type,
                    'parent_category': account.parent_category,
                    'sub_category': account.sub_category,
                    'is_header': account.is_header,
                    'periods': {}
                }
                
                # Get data for each period and company
                for period in periods:
                    period_data = {}
                    period_total = 0
                    
                    for company in companies:
                        try:
                            account_obj = None
                            if account.account_code:
                                try:
                                    account_obj = Account.objects.get(code=account.account_code)
                                except Account.DoesNotExist:
                                    logger.warning(f"Account with code '{account.account_code}' not found in Account model")
                            
                            if account_obj:
                                financial_data = FinancialData.objects.filter(
                                    company=company,
                                    account=account_obj,
                                    period=period,
                                    data_type=data_type
                                )
                                amount = financial_data.aggregate(total=Sum('amount'))['total'] or 0
                            else:
                                amount = 0
                            
                            period_data[company.code] = amount
                            period_total += amount
                            
                        except Exception as e:
                            logger.error(f"Error processing {company.code} - {account.account_code} - {period}: {e}")
                            period_data[company.code] = 0
                    
                    period_data['TOTAL'] = period_total
                    row_data['periods'][period] = period_data
                    
                    # Add to sub category periods
                    if period not in sub_periods:
                        sub_periods[period] = {}
                    for company in companies:
                        if company.code not in sub_periods[period]:
                            sub_periods[period][company.code] = 0
                        sub_periods[period][company.code] += period_data[company.code]
                    if 'TOTAL' not in sub_periods[period]:
                        sub_periods[period]['TOTAL'] = 0
                    sub_periods[period]['TOTAL'] += period_total
                
                # Calculate Grand Totals for this account
                grand_totals = {}
                grand_total_overall = 0
                
                for company in companies:
                    company_total = 0
                    for period in periods:
                        company_total += row_data['periods'][period][company.code]
                    grand_totals[company.code] = company_total
                    grand_total_overall += company_total
                
                grand_totals['OVERALL'] = grand_total_overall
                row_data['grand_totals'] = grand_totals
                
                # Only add rows where Grand Total is not zero
                if grand_total_overall != 0:
                    report_data.append(row_data)
                    
                    # Add to sub category totals
                    for company in companies:
                        if company.code not in sub_totals:
                            sub_totals[company.code] = 0
                        sub_totals[company.code] += grand_totals[company.code]
                    sub_total_overall += grand_total_overall
                else:
                    logger.info(f"Skipping account {account.account_code} - {account.account_name} (Grand Total = 0)")
            
            # Add sub category header with calculated data
            sub_totals['OVERALL'] = sub_total_overall
            sub_header = {
                'type': 'sub_header',
                'account_code': '',
                'account_name': sub_category,
                'account_type': '',
                'parent_category': parent_category,
                'sub_category': sub_category,
                'is_header': True,
                'periods': sub_periods,
                'grand_totals': sub_totals
            }
            report_data.append(sub_header)
            
            # Add to parent category totals and periods
            for company in companies:
                if company.code not in parent_totals:
                    parent_totals[company.code] = 0
                if company.code in sub_totals:
                    parent_totals[company.code] += sub_totals[company.code]
            parent_total_overall += sub_total_overall
            
            # Add sub category periods to parent periods
            for period in sub_periods:
                if period not in parent_periods:
                    parent_periods[period] = {}
                for company in companies:
                    if company.code not in parent_periods[period]:
                        parent_periods[period][company.code] = 0
                    if company.code in sub_periods[period]:
                        parent_periods[period][company.code] += sub_periods[period][company.code]
                if 'TOTAL' not in parent_periods[period]:
                    parent_periods[period]['TOTAL'] = 0
                if 'TOTAL' in sub_periods[period]:
                    parent_periods[period]['TOTAL'] += sub_periods[period]['TOTAL']
        
        # Add parent category header with calculated data
        parent_totals['OVERALL'] = parent_total_overall
        
        # Map parent category codes to proper display names
        category_display_names = {
            'IN': 'INCOME TOTAL',
            'EX': 'EXPENSE TOTAL',
            'EXP': 'EXPENSE TOTAL',
            'AS': 'ASSET TOTAL',
            'LI': 'LIABILITY TOTAL',
            'EQ': 'EQUITY TOTAL'
        }
        
        display_name = category_display_names.get(parent_category, parent_category.upper())
        
        parent_header = {
            'type': 'parent_header',
            'account_code': '',
            'account_name': display_name,
            'account_type': '',
            'parent_category': parent_category,
            'sub_category': '',
            'is_header': True,
            'periods': parent_periods,
            'grand_totals': parent_totals
        }
        report_data.append(parent_header)
    
    logger.info(f"Generated hierarchical report with {len(report_data)} rows")
    
    context = {
        'report_data': report_data,
        'companies': companies,
        'periods': periods,
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'data_type': data_type,
        'report_type': 'pl',
        'year_range': year_range,
        'debug_info': {
            'total_financial_records': total_financial_records,
            'data_type_records': data_type_records,
            'accounts_found': len(accounts),
            'companies_found': len(companies),
            'periods_found': len(periods)
        }
    }
    
    return render(request, 'core/pl_report.html', context)

def bs_report(request):
    """Balance Sheet Report view."""
    # Get filter parameters
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    
    # Convert month/year inputs to date ranges
    from_date_start, from_date_end = convert_month_year_to_date_range(from_month, from_year)
    to_date_start, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    
    # Generate year range for dropdown (2023-2030)
    year_range = range(2023, 2031)
    
    # Get all companies
    companies = Company.objects.all().order_by('name')
    
    # Get ASSET, LIABILITY, and EQUITY accounts ordered by sort_order
    accounts = ChartOfAccounts.objects.filter(
        account_type__in=['ASSET', 'LIABILITY', 'EQUITY', 'Asset', 'Liability', 'Equity']
    ).order_by('sort_order')
    
    # Get unique periods from FinancialData
    try:
        periods_query = FinancialData.objects.filter(
            account__chartofaccounts__account_type__in=['ASSET', 'LIABILITY', 'EQUITY']
        )
        
        if from_date_start:
            periods_query = periods_query.filter(period__gte=from_date_start)
        if to_date_end:
            periods_query = periods_query.filter(period__lte=to_date_end)
        
        periods = list(periods_query.values_list('period', flat=True).distinct().order_by('period'))
    except:
        periods = []
    
    # Prepare report data
    report_data = []
    
    # If no periods or accounts, return empty report
    if not periods or not accounts:
        context = {
            'report_data': [],
            'companies': companies,
            'periods': [],
            'from_month': from_month,
            'from_year': from_year,
            'to_month': to_month,
            'to_year': to_year,
            'data_type': data_type,
            'report_type': 'bs',
            'year_range': year_range
        }
        return render(request, 'core/bs_report.html', context)
    
    for account in accounts:
        row_data = {
            'account_code': account.account_code or '',
            'account_name': account.account_name,
            'account_type': account.account_type,
            'parent_category': account.parent_category,
            'sub_category': account.sub_category,
            'is_header': account.is_header,
            'periods': {}
        }
        
        # Get data for each period and company
        for period in periods:
            period_data = {}
            period_total = 0
            
            for company in companies:
                try:
                    # Get the account from Account model
                    account_obj = Account.objects.get(code=account.account_code) if account.account_code else None
                    
                    if account_obj:
                        amount = FinancialData.objects.filter(
                            company=company,
                            account=account_obj,
                            period=period,
                            data_type=data_type
                        ).aggregate(total=Sum('amount'))['total'] or 0
                    else:
                        amount = 0
                    
                    period_data[company.code] = amount
                    period_total += amount
                except Account.DoesNotExist:
                    period_data[company.code] = 0
            
            period_data['TOTAL'] = period_total
            row_data['periods'][period] = period_data
        
        report_data.append(row_data)
    
    context = {
        'report_data': report_data,
        'companies': companies,
        'periods': periods,
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'data_type': data_type,
        'report_type': 'bs',
        'year_range': year_range
    }
    
    return render(request, 'core/bs_report.html', context)

def export_report_excel(request):
    """Export report data to Excel."""
    report_type = request.GET.get('type', 'pl')
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    
    # Convert month/year inputs to date ranges
    from_date_start, from_date_end = convert_month_year_to_date_range(from_month, from_year)
    to_date_start, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    
    # Get the same data as the report views
    companies = Company.objects.all().order_by('name')
    
    if report_type == 'pl':
        accounts = ChartOfAccounts.objects.filter(
            account_type__in=['INCOME', 'EXPENSE']
        ).order_by('sort_order')
        report_title = 'Profit & Loss Report'
    else:
        accounts = ChartOfAccounts.objects.filter(
            account_type__in=['ASSET', 'LIABILITY', 'EQUITY']
        ).order_by('sort_order')
        report_title = 'Balance Sheet Report'
    
    # Get periods
    periods_query = FinancialData.objects.filter(
        account__chartofaccounts__account_type__in=accounts.values_list('account_type', flat=True)
    )
    
    if from_date_start:
        periods_query = periods_query.filter(period__gte=from_date_start)
    if to_date_end:
        periods_query = periods_query.filter(period__lte=to_date_end)
    
    periods = periods_query.values_list('period', flat=True).distinct().order_by('period')
    
    # Prepare Excel data
    excel_data = []
    
    # Header row
    header = ['Account Code', 'Account Name', 'Type', 'Parent Category', 'Sub Category']
    for period in periods:
        for company in companies:
            header.append(f'{period.strftime("%b-%y")} - {company.code}')
        header.append(f'{period.strftime("%b-%y")} - TOTAL')
    
    excel_data.append(header)
    
    # Data rows
    for account in accounts:
        row = [
            account.account_code or '',
            account.account_name,
            account.account_type or '',
            account.parent_category or '',
            account.sub_category or ''
        ]
        
        for period in periods:
            period_total = 0
            
            for company in companies:
                try:
                    account_obj = Account.objects.get(code=account.account_code) if account.account_code else None
                    
                    if account_obj:
                        amount = FinancialData.objects.filter(
                            company=company,
                            account=account_obj,
                            period=period,
                            data_type=data_type
                        ).aggregate(total=Sum('amount'))['total'] or 0
                    else:
                        amount = 0
                    
                    row.append(amount)
                    period_total += amount
                except Account.DoesNotExist:
                    row.append(0)
            
            row.append(period_total)
        
        excel_data.append(row)
    
    # Create DataFrame and Excel response
    df = pd.DataFrame(excel_data[1:], columns=excel_data[0])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{data_type}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=report_title, index=False)
    
    return response

def upload_chart_of_accounts(request):
    """View for uploading Chart of Accounts from CSV/Excel file."""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Please select a file to upload.')
            return render(request, 'core/upload_chart_of_accounts.html')
        
        uploaded_file = request.FILES['file']
        replace_existing = request.POST.get('replace_existing') == 'on'
        
        # Check file extension
        if not uploaded_file.name.endswith(('.csv', '.xlsx', '.xls')):
            messages.error(request, 'Please upload a CSV or Excel file.')
            return render(request, 'core/upload_chart_of_accounts.html')
        
        try:
            # Handle replace option
            if replace_existing:
                existing_count = ChartOfAccounts.objects.count()
                if existing_count > 0:
                    ChartOfAccounts.objects.all().delete()
                    logger.info(f"Deleted {existing_count} existing ChartOfAccounts records for replacement")
                    messages.warning(request, f'Deleted {existing_count} existing Chart of Accounts records. Proceeding with import.')
                else:
                    messages.info(request, 'No existing Chart of Accounts to replace.')
            
            # Read the file based on its type
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Check if we have at least 6 columns
            if len(df.columns) < 6:
                messages.error(request, f'File must have at least 6 columns. Found {len(df.columns)} columns.')
                return render(request, 'core/upload_chart_of_accounts.html')
            
            logger.info(f"Uploading Chart of Accounts - File has {len(df.columns)} columns")
            logger.info(f"Column names: {list(df.columns)}")
            
            # Process each row
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Read by column index (0-5) to ensure consistency with template
                    # Column 0: Sort Order
                    # Column 1: Account Code  
                    # Column 2: Account Name
                    # Column 3: Type
                    # Column 4: Parent Category
                    # Column 5: Sub Category
                    
                    sort_order = int(row.iloc[0]) if pd.notna(row.iloc[0]) else 0
                    account_code = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    account_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
                    account_type = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
                    parent_category = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
                    sub_category = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ''
                    
                    # Debug logging for first row
                    if index == 0:
                        logger.info(f"First row data:")
                        logger.info(f"  Column 0 (Sort Order): '{row.iloc[0]}' -> {sort_order}")
                        logger.info(f"  Column 1 (Account Code): '{row.iloc[1]}' -> '{account_code}'")
                        logger.info(f"  Column 2 (Account Name): '{row.iloc[2]}' -> '{account_name}'")
                        logger.info(f"  Column 3 (Type): '{row.iloc[3]}' -> '{account_type}'")
                        logger.info(f"  Column 4 (Parent Category): '{row.iloc[4]}' -> '{parent_category}'")
                        logger.info(f"  Column 5 (Sub Category): '{row.iloc[5]}' -> '{sub_category}'")
                    
                    # Validate account name
                    if not account_name:
                        errors.append(f"Row {index + 2}: Account Name is required")
                        error_count += 1
                        continue
                    
                    # Determine if this is a header row
                    is_header = not account_code or account_name.upper() in ['TOTAL INCOME', 'COST OF FUNDS', 'OVERHEADS', 'MARKETING']
                    
                    # Check if account code already exists (only for non-header rows with codes, and only if not replacing)
                    if not replace_existing and account_code and ChartOfAccounts.objects.filter(account_code=account_code).exists():
                        errors.append(f"Row {index + 2}: Account Code '{account_code}' already exists")
                        error_count += 1
                        continue
                    
                    # Create the record
                    ChartOfAccounts.objects.create(
                        sort_order=sort_order,
                        account_code=account_code if account_code else None,
                        account_name=account_name,
                        account_type=account_type if account_type else '',
                        parent_category=parent_category,
                        sub_category=sub_category,
                        formula='',  # Set to empty string since Formula column was removed
                        is_header=is_header
                    )
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    error_count += 1
            
            # Show results
            if success_count > 0:
                if replace_existing:
                    messages.success(request, f'Successfully replaced Chart of Accounts with {success_count} new records.')
                else:
                    messages.success(request, f'Successfully added/updated {success_count} records.')
            
            if error_count > 0:
                messages.warning(request, f'Failed to import {error_count} accounts. Check the errors below.')
                for error in errors[:10]:  # Show first 10 errors
                    messages.error(request, error)
                if len(errors) > 10:
                    messages.error(request, f'... and {len(errors) - 10} more errors.')
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
    
    return render(request, 'core/upload_chart_of_accounts.html')

def upload_financial_data(request):
    """View for uploading Financial Data from CSV/Excel file."""
    companies = Company.objects.all().order_by('name')
    
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Please select a file to upload.')
            return render(request, 'core/upload_financial_data.html', {'companies': companies})
        
        uploaded_file = request.FILES['file']
        company_id = request.POST.get('company')
        data_type = request.POST.get('data_type')
        
        # Validate form data
        if not company_id:
            messages.error(request, 'Please select a company.')
            return render(request, 'core/upload_financial_data.html', {'companies': companies})
        
        if not data_type:
            messages.error(request, 'Please select a data type.')
            return render(request, 'core/upload_financial_data.html', {'companies': companies})
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            messages.error(request, 'Selected company does not exist.')
            return render(request, 'core/upload_financial_data.html', {'companies': companies})
        
        # Check file extension
        if not uploaded_file.name.endswith(('.csv', '.xlsx', '.xls')):
            messages.error(request, 'Please upload a CSV or Excel file.')
            return render(request, 'core/upload_financial_data.html', {'companies': companies})
        
        try:
            # Read the file based on its type
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Check if required columns exist
            if len(df.columns) < 3:
                messages.error(request, 'File must have at least Account Code, Account Name, and one period column.')
                return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            # Get period columns (columns C onwards)
            period_columns = df.columns[2:].tolist()
            
            if not period_columns:
                messages.error(request, 'No period columns found. File must have Account Code, Account Name, and period columns.')
                return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            # Parse all period headers first
            period_dates = []
            valid_period_columns = []
            
            for col_idx, period_header in enumerate(period_columns):
                period_date = parse_period_header(period_header)
                if period_date:
                    period_dates.append(period_date)
                    valid_period_columns.append((col_idx, period_header, period_date))
                else:
                    messages.error(request, f'Cannot parse period format "{period_header}" in column {col_idx + 3}. Supported formats: Jan-24, 24-Jan, January 2024, 01/2024, 2024-01')
                    return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            if not valid_period_columns:
                messages.error(request, 'No valid period columns found.')
                return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            # Check for existing data
            existing_periods = []
            for col_idx, period_header, period_date in valid_period_columns:
                if FinancialData.objects.filter(
                    company=company,
                    period=period_date,
                    data_type=data_type
                ).exists():
                    existing_periods.append(period_header)
            
            # If there are existing periods, create backup and show warning
            backup_created = False
            if existing_periods:
                # Create backup of existing data
                try:
                    existing_data = FinancialData.objects.filter(
                        company=company,
                        data_type=data_type
                    )
                    
                    if existing_data.exists():
                        # Prepare backup data
                        backup_data = []
                        for record in existing_data:
                            backup_data.append({
                                'company_id': record.company.id,
                                'account_id': record.account.id,
                                'period': record.period.strftime('%Y-%m-%d'),
                                'amount': str(record.amount),
                                'data_type': record.data_type
                            })
                        
                        # Get periods as strings for backup
                        periods_str = [p.strftime('%Y-%m-%d') for p in period_dates]
                        
                        # Create backup record
                        DataBackup.objects.create(
                            company=company,
                            data_type=data_type,
                            periods=json.dumps(periods_str),
                            backup_data=backup_data,
                            user=request.user.username if request.user.is_authenticated else 'Anonymous',
                            description=f"Backup before upload on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                        backup_created = True
                        
                except Exception as e:
                    messages.error(request, f'Error creating backup: {str(e)}')
                
                messages.warning(request, f'Data already exists for periods: {", ".join(existing_periods)}. Existing data will be overwritten.')
                if backup_created:
                    messages.info(request, 'Backup created. You can restore previous data from Admin panel.')
            
            # Process the upload
            success_count = 0
            updated_count = 0
            error_count = 0
            errors = []
            earliest_period = min(period_dates)
            latest_period = max(period_dates)
            
            for index, row in df.iterrows():
                try:
                    # Get account code and name
                    account_code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    account_name = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    
                    # Validate account code
                    if not account_code:
                        errors.append(f"Row {index + 2}: Account Code is required")
                        error_count += 1
                        continue
                    
                    # Get or create account
                    account, created = Account.objects.get_or_create(
                        code=account_code,
                        defaults={'name': account_name, 'type': 'asset'}  # Default type
                    )
                    
                    # Process each period column
                    for col_idx, period_header, period_date in valid_period_columns:
                        try:
                            # Get amount value
                            amount_value = row.iloc[col_idx + 2]
                            
                            # Clean and parse the number value
                            amount = clean_number_value(amount_value)
                            
                            # Skip if value is None (empty/null)
                            if amount is None:
                                continue
                            
                            # Convert Decimal to float for database storage
                            try:
                                amount_float = float(amount)
                            except (ValueError, TypeError):
                                errors.append(f"Row {index + 2}, Column {col_idx + 3}: Unable to parse number '{amount_value}'. Make sure numbers don't have text formatting in Excel.")
                                error_count += 1
                                continue
                            
                            # Check if record already exists
                            existing_record = FinancialData.objects.filter(
                                company=company,
                                account=account,
                                period=period_date,
                                data_type=data_type
                            ).first()
                            
                            if existing_record:
                                # Update existing record
                                existing_record.amount = amount_float
                                existing_record.save()
                                updated_count += 1
                            else:
                                # Create new record
                                FinancialData.objects.create(
                                    company=company,
                                    account=account,
                                    period=period_date,
                                    amount=amount_float,
                                    data_type=data_type
                                )
                                success_count += 1
                            
                        except Exception as e:
                            errors.append(f"Row {index + 2}, Column {col_idx + 3}: {str(e)}")
                            error_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    error_count += 1
            
            # Show results
            if success_count > 0 or updated_count > 0:
                period_range = f"from {earliest_period.strftime('%b %Y')} to {latest_period.strftime('%b %Y')}"
                if updated_count > 0:
                    success_msg = f'Successfully uploaded {success_count} new records and updated {updated_count} existing records for {len(valid_period_columns)} periods ({period_range}).'
                    if backup_created:
                        success_msg += ' Previous data backed up and can be restored from Admin > Data Backups.'
                    messages.success(request, success_msg)
                else:
                    messages.success(request, f'Successfully uploaded {success_count} records for {len(valid_period_columns)} periods ({period_range}).')
            
            if error_count > 0:
                messages.warning(request, f'Failed to import {error_count} records. Check the errors below.')
                for error in errors[:10]:  # Show first 10 errors
                    messages.error(request, error)
                if len(errors) > 10:
                    messages.error(request, f'... and {len(errors) - 10} more errors.')
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
    
    return render(request, 'core/upload_financial_data.html', {'companies': companies})

@csrf_exempt
def download_financial_data_template(request):
    """View for downloading the Financial Data template."""
    # Create sample data with diverse period headers
    period_headers = ['Jan-24', 'Feb-24', 'Mar-24', 'Apr-24', 'May-24', 'Jun-24', 'Jul-24', 'Aug-24']
    
    # Create Excel file using pandas with various number formats
    sample_data = [
        ['1000000', 'Cash', 100000, 105000, 110000, 115000, 120000, 125000, 130000, 135000],
        ['2000000', 'Accounts Payable', 50000, 52000, 54000, 56000, 58000, 60000, 62000, 64000],
        ['4113000', 'Interest Income', 5000, 5200, 5400, 5600, 5800, 6000, 6200, 6400],
        ['5216100', 'Interest Expense', -2000, -2100, -2200, -2300, -2400, -2500, -2600, -2700],
        ['6011202', 'Marketing Expense', 15000, 16000, 17000, 18000, 19000, 20000, 21000, 22000],
    ]
    
    # Create DataFrame
    columns = ['Account Code', 'Account Name'] + period_headers
    df = pd.DataFrame(sample_data, columns=columns)
    
    # Create Excel response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="financial_data_template.xlsx"'
    
    # Write to Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Financial Data', index=False)
    
    return response

@csrf_exempt
def download_template(request):
    """View for downloading the Chart of Accounts template."""
    # Create sample data with hierarchical structure (6 columns)
    sample_data = [
        [1, '', 'TOTAL INCOME', '', '', ''],
        [2, '4113000', 'Interest Income', 'INCOME', 'TOTAL INCOME', ''],
        [45, '', 'COST OF FUNDS', '', '', ''],
        [46, '5216100', 'Interest Expense', 'EXPENSE', 'COST OF FUNDS', ''],
        [49, 'GROSS_PROFIT', 'Gross Profit', '', '', ''],
        [60, '', 'OVERHEADS', '', '', ''],
        [95, '', 'Marketing', '', 'OVERHEADS', ''],
        [96, '6011202', 'Marketing Expense', 'EXPENSE', 'OVERHEADS', 'Marketing'],
    ]
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="chart_of_accounts_template.csv"'
    
    writer = csv.writer(response)
    
    # Write headers (6 columns without Formula)
    writer.writerow(['Sort Order', 'Account Code', 'Account Name', 'Type', 'Parent Category', 'Sub Category'])
    
    # Write sample data
    for row in sample_data:
        writer.writerow(row)
    
    return response

def parse_period_header(period_header):
    """Parse period header to date object supporting multiple formats."""
    try:
        period_header = str(period_header).strip()
        
        # Month name mapping
        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }
        
        # Format 1: 'YY-Mon' (e.g., '24-Jan', '25-Feb')
        if '-' in period_header and len(period_header.split('-')) == 2:
            parts = period_header.split('-')
            year_part = parts[0].strip()
            month_part = parts[1].strip().lower()
            
            if month_part in month_map and year_part.isdigit():
                month = month_map[month_part]
                # Interpret YY as 20YY
                full_year = 2000 + int(year_part)
                if 2020 <= full_year <= 2099:  # Extended range for financial data
                    return datetime(full_year, month, 1).date()
        
        # Format 2: 'Mon-YY' (e.g., 'Jan-24', 'Feb-25')
        if '-' in period_header and len(period_header.split('-')) == 2:
            parts = period_header.split('-')
            month_part = parts[0].strip().lower()
            year_part = parts[1].strip()
            
            if month_part in month_map and year_part.isdigit():
                month = month_map[month_part]
                # Interpret YY as 20YY
                full_year = 2000 + int(year_part)
                if 2020 <= full_year <= 2099:  # Extended range for financial data
                    return datetime(full_year, month, 1).date()
        
        # Format 3: 'Month YYYY' (e.g., 'January 2024', 'Feb 2025')
        for month_name, month_num in month_map.items():
            if month_name in period_header.lower():
                # Extract year from the string
                import re
                year_match = re.search(r'\b(20\d{2})\b', period_header)
                if year_match:
                    full_year = int(year_match.group(1))
                    if 2020 <= full_year <= 2099:
                        return datetime(full_year, month_num, 1).date()
        
        # Format 4: 'MM/YYYY' (e.g., '01/2024', '12/2025')
        if '/' in period_header:
            parts = period_header.split('/')
            if len(parts) == 2:
                month_part = parts[0].strip()
                year_part = parts[1].strip()
                
                if month_part.isdigit() and year_part.isdigit():
                    month = int(month_part)
                    full_year = int(year_part)
                    
                    if 1 <= month <= 12 and 2020 <= full_year <= 2099:
                        return datetime(full_year, month, 1).date()
        
        # Format 5: 'YYYY-MM' (e.g., '2024-01', '2025-12')
        if '-' in period_header and len(period_header.split('-')) == 2:
            parts = period_header.split('-')
            year_part = parts[0].strip()
            month_part = parts[1].strip()
            
            if year_part.isdigit() and month_part.isdigit():
                full_year = int(year_part)
                month = int(month_part)
                
                if 1 <= month <= 12 and 2020 <= full_year <= 2099:
                    return datetime(full_year, month, 1).date()
        
        return None
        
    except Exception as e:
        return None
