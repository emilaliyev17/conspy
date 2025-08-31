from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q, Sum
from django.views.decorators.csrf import csrf_exempt
from .models import Company, Account, FinancialData, ChartOfAccounts, DataBackup
import pandas as pd
import csv
from datetime import datetime, date
import json
import re
from decimal import Decimal, InvalidOperation
import logging
import calendar

logger = logging.getLogger(__name__)

def clean_number_value(value):
    """Clean and parse number values from Excel, handling various formats."""
    if value is None or pd.isna(value):
        return None
    
    value_str = str(value).strip()
    if not value_str or value_str == '':
        return None
    
    value_str = value_str.strip("'\"")
    value_str = value_str.replace(' ', '')
    
    if value_str.startswith('(') and value_str.endswith(')'):
        value_str = '-' + value_str[1:-1]
    
    value_str = value_str.replace(',', '')
    
    try:
        return Decimal(value_str)
    except (InvalidOperation, ValueError):
        return None

def parse_period_header(period_header):
    """Parse period headers in various formats to date objects."""
    if not period_header:
        return None
    
    period_str = str(period_header).strip()
    
    # Try different date formats
    formats_to_try = [
        '%Y-%m', '%m/%Y', '%Y/%m', '%b-%y', '%y-%b', '%B %Y', '%Y %B'
    ]
    
    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(period_str, fmt)
            # If year is 2 digits, assume 20xx
            if parsed_date.year < 100:
                parsed_date = parsed_date.replace(year=2000 + parsed_date.year)
            # Validate year range
            if 2020 <= parsed_date.year <= 2099:
                return parsed_date.date()
        except ValueError:
            continue
    
    return None

def convert_month_year_to_date_range(month, year):
    """Convert separate month and year to date range (first day to last day of month)."""
    if not month or not year:
        return None, None
    
    try:
        month_int = int(month)
        year_int = int(year)
        first_day = date(year_int, month_int, 1)
        last_day = date(year_int, month_int, calendar.monthrange(year_int, month_int)[1])
        return first_day, last_day
    except (ValueError, AttributeError):
        return None, None

def home(request):
    """Home page view with navigation to upload functionality."""
    return render(request, 'core/home.html')

def chart_of_accounts_view(request):
    """View for displaying Chart of Accounts with search and hierarchical display."""
    search_query = request.GET.get('search', '')
    accounts = ChartOfAccounts.objects.all().order_by('sort_order')
    
    if search_query:
        accounts = accounts.filter(
            Q(account_code__icontains=search_query) |
            Q(account_name__icontains=search_query) |
            Q(account_type__icontains=search_query) |
            Q(parent_category__icontains=search_query) |
            Q(sub_category__icontains=search_query)
        )
    
    hierarchical_accounts = []
    parent_categories = {}
    
    for account in accounts:
        if account.parent_category:
            if account.parent_category not in parent_categories:
                parent_categories[account.parent_category] = []
            parent_categories[account.parent_category].append(account)
        else:
            hierarchical_accounts.append(account)
    
    for parent_category, sub_accounts in parent_categories.items():
        parent_header = next((acc for acc in hierarchical_accounts if acc.account_name == parent_category), None)
        if not parent_header:
            hierarchical_accounts.append(ChartOfAccounts(
                account_name=parent_category,
                account_type='',
                parent_category='',
                sub_category='',
                sort_order=0,
                is_header=True
            ))
        hierarchical_accounts.extend(sub_accounts)
    
    context = {
        'accounts': hierarchical_accounts,
        'search_query': search_query
    }
    return render(request, 'core/chart_of_accounts_simple.html', context)

@csrf_exempt
def download_chart_of_accounts(request):
    """Download Chart of Accounts as CSV/Excel."""
    accounts = ChartOfAccounts.objects.all().order_by('sort_order')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="chart_of_accounts.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Sort Order', 'Account Code', 'Account Name', 'Type', 'Parent Category', 'Sub Category'])
    
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

def upload_chart_of_accounts(request):
    """Upload Chart of Accounts from CSV/Excel file."""
    if request.method == 'POST':
        uploaded_file = request.FILES['file']
        replace_existing = request.POST.get('replace_existing') == 'on'

        try:
            if replace_existing:
                existing_count = ChartOfAccounts.objects.count()
                if existing_count > 0:
                    ChartOfAccounts.objects.all().delete()
                    logger.info(f"Deleted {existing_count} existing ChartOfAccounts records for replacement")
                    messages.warning(request, f'Deleted {existing_count} existing Chart of Accounts records. Proceeding with import.')
                else:
                    messages.info(request, 'No existing Chart of Accounts to replace.')

            # Read file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Check column count
            if len(df.columns) < 6:
                messages.error(request, f'File must have at least 6 columns. Found {len(df.columns)} columns.')
                return render(request, 'core/upload_chart_of_accounts.html')
            
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    sort_order = int(row.iloc[0]) if pd.notna(row.iloc[0]) else 0
                    account_code = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    account_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
                    account_type = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
                    parent_category = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
                    sub_category = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ''

                    if not replace_existing and account_code and ChartOfAccounts.objects.filter(account_code=account_code).exists():
                        errors.append(f"Row {index + 2}: Account Code '{account_code}' already exists")
                        error_count += 1
                        continue

                    ChartOfAccounts.objects.create(
                        sort_order=sort_order,
                        account_code=account_code if account_code else None,
                        account_name=account_name,
                        account_type=account_type if account_type else '',
                        parent_category=parent_category,
                        sub_category=sub_category,
                        formula='',
                        is_header=is_header
                    )
                    success_count += 1
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    error_count += 1
            
            if success_count > 0:
                if replace_existing:
                    messages.success(request, f'Successfully replaced Chart of Accounts with {success_count} new records.')
                else:
                    messages.success(request, f'Successfully added/updated {success_count} records.')
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
    
    return render(request, 'core/upload_chart_of_accounts.html')

def upload_financial_data(request):
    """Upload Financial Data from CSV/Excel file."""
    companies = Company.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            uploaded_file = request.FILES['file']
            company_id = request.POST.get('company')
            data_type = request.POST.get('data_type', 'actual')
            
            if not company_id:
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Please select a company.'})
                else:
                    messages.error(request, 'Please select a company.')
                    return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            company = Company.objects.get(id=company_id)
            
            # Read file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Check minimum columns
            if len(df.columns) < 3:
                error_msg = 'File must have at least 3 columns: Account Code, Account Name, and at least one period column.'
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': error_msg})
                else:
                    messages.error(request, error_msg)
                    return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            # Parse period columns (starting from column 3)
            period_columns = []
            for col in df.columns[2:]:
                period_date = parse_period_header(col)
                if period_date:
                    period_columns.append((col, period_date))
            
            if not period_columns:
                error_msg = 'No valid period columns found. Please ensure column headers are in format like "Jan-24", "2024-01", etc.'
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': error_msg})
                else:
                    messages.error(request, error_msg)
                    return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            # Check for existing data
            existing_periods = []
            for col, period_date in period_columns:
                existing_data = FinancialData.objects.filter(
                    company=company,
                    period=period_date,
                    data_type=data_type
                )
                if existing_data.exists():
                    existing_periods.append(col)
            
            # If there's existing data and no confirmation, ask for confirmation
            if existing_periods and not request.POST.get('confirm_overwrite'):
                if is_ajax:
                    return JsonResponse({
                        'status': 'confirmation_needed',
                        'message': f'Data already exists for periods: {", ".join(existing_periods)}. Do you want to overwrite it?'
                    })
                else:
                    messages.warning(request, f'Data already exists for periods: {", ".join(existing_periods)}. Please confirm overwrite.')
                    return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            # Create backup before overwriting if there's existing data
            if existing_periods:
                backup_data = []
                for col, period_date in period_columns:
                    if col in existing_periods:
                        existing_records = FinancialData.objects.filter(
                            company=company,
                            period=period_date,
                            data_type=data_type
                        )
                        for record in existing_records:
                            backup_data.append({
                                'account_code': record.account.code,
                                'amount': float(record.amount),
                                'period': record.period.isoformat()
                            })
                
                if backup_data:
                    DataBackup.objects.create(
                        company=company,
                        data_type=data_type,
                        periods=json.dumps([col for col, _ in period_columns if col in existing_periods]),
                        backup_data=backup_data,
                        user=request.user.username if request.user.is_authenticated else 'Anonymous',
                        description=f"Backup before upload on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    backup_msg = f'Backup created for existing data in periods: {", ".join(existing_periods)}. You can restore previous data from Admin panel.'
                    if is_ajax:
                        # We'll include this in the success message
                        pass
                    else:
                        messages.warning(request, backup_msg)
                
                # Delete existing data
                for col, period_date in period_columns:
                    if col in existing_periods:
                        FinancialData.objects.filter(
                            company=company,
                            period=period_date,
                            data_type=data_type
                        ).delete()
            
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    account_code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    account_name = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    
                    if not account_code:
                        continue
                    
                    # Get or create account
                    account, created = Account.objects.get_or_create(
                        code=account_code,
                        defaults={'name': account_name, 'type': 'asset'}
                    )
                    
                    # Process each period column
                    for col, period_date in period_columns:
                        amount_value = row[col]
                        if pd.notna(amount_value):
                            cleaned_amount = clean_number_value(amount_value)
                            if cleaned_amount is not None:
                                FinancialData.objects.create(
                                    company=company,
                                    account=account,
                                    period=period_date,
                                    amount=cleaned_amount,
                                    data_type=data_type
                                )
                                success_count += 1
                
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    error_count += 1
            
            # Prepare response message
            if success_count > 0:
                success_msg = f'Successfully uploaded {success_count} records for {len(period_columns)} periods.'
                if existing_periods:
                    success_msg += f' Backup created for overwritten data.'
                if errors:
                    success_msg += f' Encountered {len(errors)} errors. Please check the data format.'
                
                if is_ajax:
                    return JsonResponse({'status': 'success', 'message': success_msg})
                else:
                    messages.success(request, success_msg)
            else:
                error_msg = 'No valid data was uploaded. Please check your file format.'
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': error_msg})
                else:
                    messages.error(request, error_msg)
        
        except Exception as e:
            error_msg = f'Error processing file: {str(e)}'
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': error_msg})
            else:
                messages.error(request, error_msg)
    
    return render(request, 'core/upload_financial_data.html', {'companies': companies})

@csrf_exempt
def download_financial_data_template(request):
    """Download Financial Data template as Excel."""
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="financial_data_template.xlsx"'
    
    # Create sample data
    sample_data = [
        ['4113000', 'Interest Income', 60000, 80000, 104363, 130182, 150000, 175000],
        ['5216100', 'Interest Expense', 20000, 25000, 30000, 35000, 40000, 45000],
        ['6011100', 'Basic Salary', 50000, 50000, 52000, 52000, 54000, 54000]
    ]
    
    # Create DataFrame
    df = pd.DataFrame(sample_data, columns=[
        'Account Code', 'Account Name', 'Jan-24', 'Feb-24', 'Mar-24', 'Apr-24', 'May-24', 'Jun-24'
    ])
    
    # Write to Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Financial Data', index=False)
    
    return response

@csrf_exempt
def download_template(request):
    """Download Chart of Accounts template as CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="chart_of_accounts_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Sort Order', 'Account Code', 'Account Name', 'Type', 'Parent Category', 'Sub Category'])
    
    # Sample data
    sample_data = [
        [1, '', 'TOTAL INCOME', '', '', ''],
        [2, '4113000', 'Interest Income', 'INCOME', 'TOTAL INCOME', ''],
        [45, '', 'COST OF FUNDS', '', '', ''],
        [46, '5216100', 'Interest Expense', 'EXPENSE', 'COST OF FUNDS', ''],
        [49, 'GROSS_PROFIT', 'Gross Profit', '', '', ''],
        [60, '', 'OVERHEADS', '', '', ''],
        [95, '', 'Marketing', '', 'OVERHEADS', ''],
        [96, '6011202', 'Marketing Expense', 'EXPENSE', 'OVERHEADS', 'Marketing']
    ]
    
    for row in sample_data:
        writer.writerow(row)
    
    return response

def pl_report(request):
    """P&L Report view with hierarchical grouping by parent_category and sub_category."""
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    
    from_date_start, from_date_end = convert_month_year_to_date_range(from_month, from_year)
    to_date_start, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    
    year_range = range(2023, 2031)
    
    logger.info(f"P&L Report - Filters: from_month={from_month}, from_year={from_year}, to_month={to_month}, to_year={to_year}, data_type={data_type}")
    
    # Get all companies
    companies = list(Company.objects.all().order_by('name'))
    logger.info(f"Found {len(companies)} companies")
    
    # Get INCOME and EXPENSE accounts from ChartOfAccounts
    chart_accounts = list(ChartOfAccounts.objects.filter(
        account_type__in=['INCOME', 'EXPENSE', 'Income', 'Expense']
    ).order_by('sort_order'))
    logger.info(f"Found {len(chart_accounts)} INCOME/EXPENSE accounts in ChartOfAccounts")
    
    # Debug: Log parent categories found
    parent_categories = set(acc.parent_category for acc in chart_accounts if acc.parent_category)
    logger.info(f"Parent categories found: {parent_categories}")
    
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
    if not periods or not chart_accounts:
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
                'accounts_found': len(chart_accounts),
                'companies_found': len(companies),
                'periods_found': len(periods)
            }
        }
        return render(request, 'core/pl_report.html', context)
    
    # Pre-fetch all FinancialData for better performance
    financial_data = {}
    for period in periods:
        financial_data[period] = {}
        for company in companies:
            financial_data[period][company.code] = {}
    
    # Get all FinancialData in one query
    all_financial_data = FinancialData.objects.filter(
        data_type=data_type,
        period__in=periods
    ).select_related('company', 'account')
    
    # Organize financial data by period, company, and account
    for fd in all_financial_data:
        if fd.period in financial_data and fd.company.code in financial_data[fd.period]:
            financial_data[fd.period][fd.company.code][fd.account.code] = fd.amount
    
    # Group accounts by parent_category and sub_category
    grouped_data = {}
    
    for account in chart_accounts:
        parent_category = account.parent_category or 'UNCATEGORIZED'
        sub_category = account.sub_category or 'UNCATEGORIZED'
        
        if parent_category not in grouped_data:
            grouped_data[parent_category] = {}
        
        if sub_category not in grouped_data[parent_category]:
            grouped_data[parent_category][sub_category] = []
        
        grouped_data[parent_category][sub_category].append(account)
        logger.info(f"Grouped account {account.account_code} under {parent_category} -> {sub_category}")
    
    # Define P&L structure order
    pl_structure = ['INCOME', 'COST OF FUNDS', 'OVERHEADS', 'TAXES']
    
    # Calculate all totals first
    parent_totals = {}
    sub_category_totals = {}
    
    # Initialize totals structure
    for parent_category in pl_structure:
        parent_totals[parent_category] = {}
        for period in periods:
            parent_totals[parent_category][period] = {}
            for company in companies:
                parent_totals[parent_category][period][company.code] = 0
            parent_totals[parent_category][period]['TOTAL'] = 0
    
    # Calculate totals for each account (only once)
    for parent_category, sub_categories in grouped_data.items():
        for sub_category, sub_accounts in sub_categories.items():
            sub_category_key = f"{parent_category}_{sub_category}"
            sub_category_totals[sub_category_key] = {}
            
            for period in periods:
                sub_category_totals[sub_category_key][period] = {}
                for company in companies:
                    sub_category_totals[sub_category_key][period][company.code] = 0
                sub_category_totals[sub_category_key][period]['TOTAL'] = 0
            
            for account in sub_accounts:
                if not account.account_code:
                    continue
                    
                for period in periods:
                    for company in companies:
                        # Get amount from pre-fetched data
                        amount = financial_data[period][company.code].get(account.account_code, 0)
                        
                        # Add to sub category total
                        sub_category_totals[sub_category_key][period][company.code] += amount
                        sub_category_totals[sub_category_key][period]['TOTAL'] += amount
                        
                        # Add to parent category total
                        if parent_category in parent_totals:
                            parent_totals[parent_category][period][company.code] += amount
                            parent_totals[parent_category][period]['TOTAL'] += amount
    
    # Build hierarchical report structure
    report_data = []
    
    for parent_category in pl_structure:
        if parent_category not in grouped_data:
            logger.info(f"Parent category {parent_category} not found in grouped_data")
            continue
            
        # Calculate grand totals for parent category
        parent_grand_totals = {}
        parent_grand_total_overall = 0
        
        for company in companies:
            company_total = 0
            for period in periods:
                company_total += parent_totals[parent_category][period][company.code]
            parent_grand_totals[company.code] = company_total
            parent_grand_total_overall += company_total
        
        parent_grand_totals['TOTAL'] = parent_grand_total_overall
        
        # Add parent category header
        report_data.append({
            'type': 'parent_header',
            'account_code': '',
            'account_name': parent_category,
            'account_type': '',
            'parent_category': parent_category,
            'sub_category': '',
            'is_header': True,
            'periods': parent_totals[parent_category],
            'grand_totals': parent_grand_totals
        })
        
        # Process sub categories
        for sub_category, sub_accounts in grouped_data[parent_category].items():
            # Calculate grand totals for sub category
            sub_grand_totals = {}
            sub_grand_total_overall = 0
            sub_category_key = f"{parent_category}_{sub_category}"
            
            for company in companies:
                company_total = 0
                for period in periods:
                    company_total += sub_category_totals[sub_category_key][period][company.code]
                sub_grand_totals[company.code] = company_total
                sub_grand_total_overall += company_total
            
            sub_grand_totals['TOTAL'] = sub_grand_total_overall
            
            # Add sub category header
            report_data.append({
                'type': 'sub_header',
                'account_code': '',
                'account_name': sub_category,
                'account_type': '',
                'parent_category': parent_category,
                'sub_category': sub_category,
                'is_header': True,
                'periods': sub_category_totals[sub_category_key],
                'grand_totals': sub_grand_totals
            })
            
            # Add individual accounts
            for account in sub_accounts:
                if not account.account_code:
                    continue
                    
                account_data = {
                    'type': 'account',
                    'account_code': account.account_code,
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
                        amount = financial_data[period][company.code].get(account.account_code, 0)
                        period_data[company.code] = amount
                        period_total += amount
                    
                    period_data['TOTAL'] = period_total
                    account_data['periods'][period] = period_data
                
                report_data.append(account_data)
        
        # Add parent category total
        report_data.append({
            'type': 'parent_total',
            'account_code': '',
            'account_name': f'TOTAL {parent_category}',
            'account_type': '',
            'parent_category': parent_category,
            'sub_category': '',
            'is_header': True,
            'periods': parent_totals[parent_category],
            'grand_totals': {}
        })
    
    # Add calculated totals after all parent categories are processed
    # GROSS PROFIT = TOTAL INCOME - TOTAL COST OF FUNDS
    if 'INCOME' in parent_totals and 'COST OF FUNDS' in parent_totals:
        gross_profit = {}
        for period in periods:
            gross_profit[period] = {}
            for company in companies:
                income = parent_totals['INCOME'][period][company.code]
                cost_of_funds = parent_totals['COST OF FUNDS'][period][company.code]
                gross_profit[period][company.code] = income - cost_of_funds
            gross_profit[period]['TOTAL'] = parent_totals['INCOME'][period]['TOTAL'] - parent_totals['COST OF FUNDS'][period]['TOTAL']
        
        report_data.append({
            'type': 'calculated_total',
            'account_code': '',
            'account_name': 'GROSS PROFIT',
            'account_type': '',
            'parent_category': 'CALCULATED',
            'sub_category': '',
            'is_header': True,
            'periods': gross_profit,
            'grand_totals': {}
        })
    
    # NET PROFIT BEFORE TAX = GROSS PROFIT - TOTAL OVERHEADS
    if 'INCOME' in parent_totals and 'COST OF FUNDS' in parent_totals and 'OVERHEADS' in parent_totals:
        net_profit_before_tax = {}
        for period in periods:
            net_profit_before_tax[period] = {}
            for company in companies:
                income = parent_totals['INCOME'][period][company.code]
                cost_of_funds = parent_totals['COST OF FUNDS'][period][company.code]
                overheads = parent_totals['OVERHEADS'][period][company.code]
                net_profit_before_tax[period][company.code] = (income - cost_of_funds) - overheads
            net_profit_before_tax[period]['TOTAL'] = (parent_totals['INCOME'][period]['TOTAL'] - parent_totals['COST OF FUNDS'][period]['TOTAL']) - parent_totals['OVERHEADS'][period]['TOTAL']
        
        report_data.append({
            'type': 'calculated_total',
            'account_code': '',
            'account_name': 'NET PROFIT BEFORE TAX',
            'account_type': '',
            'parent_category': 'CALCULATED',
            'sub_category': '',
            'is_header': True,
            'periods': net_profit_before_tax,
            'grand_totals': {}
        })
    
    # NET PROFIT AFTER TAX = NET PROFIT BEFORE TAX - TOTAL TAXES
    if 'INCOME' in parent_totals and 'COST OF FUNDS' in parent_totals and 'OVERHEADS' in parent_totals and 'TAXES' in parent_totals:
        net_profit_after_tax = {}
        for period in periods:
            net_profit_after_tax[period] = {}
            for company in companies:
                income = parent_totals['INCOME'][period][company.code]
                cost_of_funds = parent_totals['COST OF FUNDS'][period][company.code]
                overheads = parent_totals['OVERHEADS'][period][company.code]
                taxes = parent_totals['TAXES'][period][company.code]
                net_profit_after_tax[period][company.code] = ((income - cost_of_funds) - overheads) - taxes
            net_profit_after_tax[period]['TOTAL'] = ((parent_totals['INCOME'][period]['TOTAL'] - parent_totals['COST OF FUNDS'][period]['TOTAL']) - parent_totals['OVERHEADS'][period]['TOTAL']) - parent_totals['TAXES'][period]['TOTAL']
        
        report_data.append({
            'type': 'calculated_total',
            'account_code': '',
            'account_name': 'NET PROFIT AFTER TAX',
            'account_type': '',
            'parent_category': 'CALCULATED',
            'sub_category': '',
            'is_header': True,
            'periods': net_profit_after_tax,
            'grand_totals': {}
        })
    
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
            'accounts_found': len(chart_accounts),
            'companies_found': len(companies),
            'periods_found': len(periods),
            'parent_categories': list(parent_categories)
        }
    }
    
    return render(request, 'core/pl_report.html', context)

def bs_report(request):
    """Balance Sheet Report view."""
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    
    from_date_start, from_date_end = convert_month_year_to_date_range(from_month, from_year)
    to_date_start, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    
    year_range = range(2023, 2031)
    
    companies = Company.objects.all().order_by('name')
    
    bs_types = [
        'ASSET', 'LIABILITY', 'EQUITY',
        'Bank', 'Fixed Asset', 'Other Current Asset', 'Other Asset',
        'Other Current Liabilities', 'Other Current Liability',
        'Equity'
    ]
    accounts = ChartOfAccounts.objects.filter(
        account_type__in=bs_types
    ).order_by('sort_order')
    
    try:
        periods_query = FinancialData.objects.filter(
            account__type__in=['asset', 'liability', 'equity']
        )
        
        if from_date_start:
            periods_query = periods_query.filter(period__gte=from_date_start)
        if to_date_end:
            periods_query = periods_query.filter(period__lte=to_date_end)
        
        periods = list(periods_query.values_list('period', flat=True).distinct().order_by('period'))
    except:
        periods = []
    
    report_data = []
    
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
    
    # Define Balance Sheet structure order
    bs_structure = ['ASSETS', 'LIABILITIES', 'EQUITY']
    
    # Calculate all totals first
    parent_totals = {}
    sub_category_totals = {}
    
    # Initialize totals structure
    for parent_category in bs_structure:
        parent_totals[parent_category] = {}
        for period in periods:
            parent_totals[parent_category][period] = {}
            for company in companies:
                parent_totals[parent_category][period][company.code] = 0
            parent_totals[parent_category][period]['TOTAL'] = 0
    
    # Calculate totals for each account
    for parent_category, sub_categories in grouped_data.items():
        for sub_category, sub_accounts in sub_categories.items():
            sub_category_totals[f"{parent_category}_{sub_category}"] = {}
            for period in periods:
                sub_category_totals[f"{parent_category}_{sub_category}"][period] = {}
                for company in companies:
                    sub_category_totals[f"{parent_category}_{sub_category}"][period][company.code] = 0
                sub_category_totals[f"{parent_category}_{sub_category}"][period]['TOTAL'] = 0
            
            for account in sub_accounts:
                for period in periods:
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
                            
                            # Add to sub category total
                            sub_category_totals[f"{parent_category}_{sub_category}"][period][company.code] += amount
                            sub_category_totals[f"{parent_category}_{sub_category}"][period]['TOTAL'] += amount
                            
                            # Add to parent category total
                            parent_totals[parent_category][period][company.code] += amount
                            parent_totals[parent_category][period]['TOTAL'] += amount
                            
                        except Account.DoesNotExist:
                            continue
    
    # Build hierarchical report structure
    for parent_category in bs_structure:
        if parent_category not in grouped_data:
            continue
            
        # Calculate grand totals for parent category
        parent_grand_totals = {}
        parent_grand_total_overall = 0
        
        for company in companies:
            company_total = 0
            for period in periods:
                company_total += parent_totals[parent_category][period][company.code]
            parent_grand_totals[company.code] = company_total
            parent_grand_total_overall += company_total
        
        parent_grand_totals['TOTAL'] = parent_grand_total_overall
        
        # Add parent category header
        report_data.append({
            'type': 'parent_header',
            'account_code': '',
            'account_name': parent_category,
            'account_type': '',
            'parent_category': parent_category,
            'sub_category': '',
            'is_header': True,
            'periods': parent_totals[parent_category],
            'grand_totals': parent_grand_totals
        })
        
        # Process sub categories
        for sub_category, sub_accounts in grouped_data[parent_category].items():
            # Calculate grand totals for sub category
            sub_grand_totals = {}
            sub_grand_total_overall = 0
            
            for company in companies:
                company_total = 0
                for period in periods:
                    company_total += sub_category_totals[f"{parent_category}_{sub_category}"][period][company.code]
                sub_grand_totals[company.code] = company_total
                sub_grand_total_overall += company_total
            
            sub_grand_totals['TOTAL'] = sub_grand_total_overall
            
            # Add sub category header
            report_data.append({
                'type': 'sub_header',
                'account_code': '',
                'account_name': sub_category,
                'account_type': '',
                'parent_category': parent_category,
                'sub_category': sub_category,
                'is_header': True,
                'periods': sub_category_totals[f"{parent_category}_{sub_category}"],
                'grand_totals': sub_grand_totals
            })
            
            # Add individual accounts
            for account in sub_accounts:
                account_data = {
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
                    account_data['periods'][period] = period_data
                
                report_data.append(account_data)
        
        # Add sub category subtotal
        if parent_category in grouped_data:
            for sub_category in grouped_data[parent_category].keys():
                report_data.append({
                    'type': 'sub_total',
                    'account_code': '',
                    'account_name': f'Subtotal {sub_category}',
                    'account_type': '',
                    'parent_category': parent_category,
                    'sub_category': sub_category,
                    'is_header': True,
                    'periods': sub_category_totals[f"{parent_category}_{sub_category}"],
                    'grand_totals': {}
                })
        
        # Add parent category total
        report_data.append({
            'type': 'parent_total',
            'account_code': '',
            'account_name': f'TOTAL {parent_category}',
            'account_type': '',
            'parent_category': parent_category,
            'sub_category': '',
            'is_header': True,
            'periods': parent_totals[parent_category],
            'grand_totals': {}
        })
    
    # Add CHECK row at bottom: TOTAL ASSETS - TOTAL LIABILITIES - TOTAL EQUITY (should equal 0)
    check_row = {}
    for period in periods:
        check_row[period] = {}
        for company in companies:
            total_assets = parent_totals.get('ASSETS', {}).get(period, {}).get(company.code, 0)
            total_liabilities = parent_totals.get('LIABILITIES', {}).get(period, {}).get(company.code, 0)
            total_equity = parent_totals.get('EQUITY', {}).get(period, {}).get(company.code, 0)
            check_row[period][company.code] = total_assets - total_liabilities - total_equity
        check_row[period]['TOTAL'] = (parent_totals.get('ASSETS', {}).get(period, {}).get('TOTAL', 0) - 
                                     parent_totals.get('LIABILITIES', {}).get(period, {}).get('TOTAL', 0) - 
                                     parent_totals.get('EQUITY', {}).get(period, {}).get('TOTAL', 0))
    
    report_data.append({
        'type': 'check_row',
        'account_code': '',
        'account_name': 'CHECK (Assets - Liabilities - Equity)',
        'account_type': '',
        'parent_category': 'CALCULATED',
        'sub_category': '',
        'is_header': True,
        'periods': check_row,
        'grand_totals': {}
    })
    
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
    
    from_date_start, from_date_end = convert_month_year_to_date_range(from_month, from_year)
    to_date_start, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    
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
    
    # Add headers
    header_row = ['Account Code', 'Account Name']
    for period in periods:
        for company in companies:
            header_row.append(f"{period.strftime('%Y-%m')} {company.code}")
        header_row.append(f"{period.strftime('%Y-%m')} TOTAL")
    excel_data.append(header_row)
    
    # Add data rows
    for account in accounts:
        row = [account.account_code or '', account.account_name]
        
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
                    row.append(float(amount))
                    period_total += amount
                except Account.DoesNotExist:
                    row.append(0.0)
            row.append(float(period_total))
        
        excel_data.append(row)
    
    # Create DataFrame and export
    df = pd.DataFrame(excel_data[1:], columns=excel_data[0])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{report_title.lower().replace(" ", "_")}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=report_title, index=False)
    
    return response