from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils.timezone import make_naive
from django.db.models import Q, Sum
from django.views.decorators.csrf import csrf_exempt
from .models import Company, FinancialData, ChartOfAccounts, DataBackup, CFDashboardMetric, CFDashboardData
import pandas as pd
import csv
from datetime import datetime, date
import json
import re
from decimal import Decimal, InvalidOperation
import logging
from dateutil.relativedelta import relativedelta
import calendar

logger = logging.getLogger(__name__)

def clean_number_value(value):
    """Clean and parse number values from Excel, handling various formats including QuickBooks."""
    if value is None or pd.isna(value):
        return None
    
    value_str = str(value).strip()
    if not value_str or value_str == '':
        return None
    
    # Remove quotes and apostrophes
    value_str = value_str.strip("'\"")
    
    # Remove currency symbols ($, €, £, etc.)
    value_str = value_str.replace('$', '').replace('€', '').replace('£', '').replace('¥', '')
    
    # Remove all spaces
    value_str = value_str.replace(' ', '')
    
    # Handle negative numbers in parentheses: (1,234.56) -> -1234.56
    if value_str.startswith('(') and value_str.endswith(')'):
        value_str = '-' + value_str[1:-1]
    
    # Handle QuickBooks formats with different separators
    # Remove thousand separators (commas)
    value_str = value_str.replace(',', '')
    
    # Handle European format where comma is decimal separator
    # If there are multiple dots, assume comma is decimal separator
    if value_str.count('.') > 1:
        # Keep only the last dot as decimal separator
        parts = value_str.split('.')
        value_str = ''.join(parts[:-1]) + '.' + parts[-1]
    
    # Try to parse as decimal
    try:
        return Decimal(value_str)
    except (InvalidOperation, ValueError):
        # If still fails, try to remove any remaining non-numeric characters except . and -
        import re
        cleaned = re.sub(r'[^\d.-]', '', value_str)
        if cleaned:
            try:
                return Decimal(cleaned)
            except (InvalidOperation, ValueError):
                return None
        return None

def parse_period_header(period_header):
    """Parse period headers in various formats to date objects."""
    if not period_header:
        return None
    
    # If it's already a datetime object, convert it directly
    if isinstance(period_header, datetime):
        # Validate year range
        if 2020 <= period_header.year <= 2099:
            # Always use first day of month
            return period_header.replace(day=1).date()
        return None
    
    # If it's already a date object, validate and return
    if isinstance(period_header, date):
        if 2020 <= period_header.year <= 2099:
            return period_header.replace(day=1)
        return None
    
    # Handle string formats
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
                # Always use first day of month
                return parsed_date.replace(day=1).date()
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
                    # Skip completely empty rows
                    if row.isna().all():
                        continue
                        
                    sort_order = int(row.iloc[0]) if pd.notna(row.iloc[0]) else 0
                    account_code = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    account_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
                    account_type = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
                    parent_category = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
                    sub_category = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ''
                    
                    # Skip rows without account name
                    if not account_name:
                        continue

                    if not replace_existing and account_code and ChartOfAccounts.objects.filter(account_code=account_code).exists():
                        errors.append(f"Row {index + 2}: Account Code '{account_code}' already exists")
                        error_count += 1
                        continue

                    # Determine if this is a header row (no account code or specific account types)
                    is_header = not account_code or account_type in ['', 'HEADER', 'TOTAL']
                    
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
            
            if error_count > 0:
                error_message = f'Encountered {error_count} errors during import. '
                if errors:
                    error_message += 'First few errors: ' + '; '.join(errors[:5])
                messages.warning(request, error_message)
                
        except Exception as e:
            logger.error(f'Error processing Chart of Accounts file: {str(e)}')
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
            if len(df.columns) < 2:
                error_msg = 'File must have at least 2 columns: Account Code and at least one period column.'
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': error_msg})
                else:
                    messages.error(request, error_msg)
                    return render(request, 'core/upload_financial_data.html', {'companies': companies})
            
            # Parse period columns (starting from column 2)
            period_columns = []
            debug_info = []
            for col in df.columns[1:]:
                debug_info.append(f"Column: '{col}' (type: {type(col)})")
                period_date = parse_period_header(col)
                if period_date:
                    period_columns.append((col, period_date))
                    debug_info.append(f"  -> Parsed as: {period_date}")
                else:
                    debug_info.append(f"  -> Failed to parse")
            
            if not period_columns:
                error_msg = f'No valid period columns found. Please ensure column headers are in format like "Jan-24", "2024-01", etc. Debug info: {" | ".join(debug_info)}'
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
            
            # Collect account codes from the uploaded file
            uploaded_account_codes = set()
            for index, row in df.iterrows():
                account_code_raw = row.iloc[0]
                if pd.notna(account_code_raw):
                    if isinstance(account_code_raw, float):
                        account_code = str(int(account_code_raw))
                    else:
                        account_code = str(account_code_raw).strip()
                    if account_code:
                        uploaded_account_codes.add(account_code)
            
            # Create backup before overwriting if there's existing data
            if existing_periods:
                backup_data = []
                for col, period_date in period_columns:
                    if col in existing_periods:
                        existing_records = FinancialData.objects.filter(
                            company=company,
                            period=period_date,
                            data_type=data_type,
                            account_code__in=uploaded_account_codes  # Backup только тех записей, которые будут удалены
                        )
                        for record in existing_records:
                            backup_data.append({
                                'account_code': record.account_code,
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
                
                # Delete ONLY data for account codes that are in the uploaded file
                for col, period_date in period_columns:
                    if col in existing_periods:
                        FinancialData.objects.filter(
                            company=company,
                            period=period_date,
                            data_type=data_type,
                            account_code__in=uploaded_account_codes  # ВАЖНО: удаляем только эти коды
                        ).delete()
            
            success_count = 0
            error_count = 0
            errors = []
            debug_info = []
            
            for index, row in df.iterrows():
                try:
                    account_code_raw = row.iloc[0]
                    if pd.notna(account_code_raw):
                        # Remove .0 suffix if it's a float, then convert to string
                        if isinstance(account_code_raw, float):
                            account_code = str(int(account_code_raw))
                        else:
                            account_code = str(account_code_raw).strip()
                    else:
                        account_code = ''
                    
                    debug_info.append(f"Row {index + 2}: Account code = '{account_code}' (raw: {account_code_raw})")
                    
                    if not account_code:
                        debug_info.append(f"  -> Skipping: empty account code")
                        continue
                    
                    # Verify account exists in ChartOfAccounts (ONLY by account_code)
                    try:
                        chart_account = ChartOfAccounts.objects.get(account_code=account_code)
                        debug_info.append(f"  -> Found in Chart of Accounts: {chart_account.account_name}")
                    except ChartOfAccounts.DoesNotExist:
                        errors.append(f"Row {index + 2}: Account code '{account_code}' not found in Chart of Accounts")
                        error_count += 1
                        debug_info.append(f"  -> ERROR: Account not found")
                        continue
                    
                    # Process each period column
                    for col, period_date in period_columns:
                        amount_value = row[col]
                        debug_info.append(f"  -> Period {period_date}: value = {amount_value} (type: {type(amount_value)})")
                        
                        if pd.notna(amount_value):
                            cleaned_amount = clean_number_value(amount_value)
                            debug_info.append(f"    -> Cleaned amount: {cleaned_amount}")
                            
                            if cleaned_amount is not None:
                                FinancialData.objects.create(
                                    company=company,
                                    account_code=account_code,
                                    period=period_date,
                                    amount=cleaned_amount,
                                    data_type=data_type
                                )
                                success_count += 1
                                debug_info.append(f"    -> SUCCESS: Created record")
                            else:
                                debug_info.append(f"    -> FAILED: clean_number_value returned None")
                        else:
                            debug_info.append(f"    -> SKIPPED: pd.notna returned False")
                
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    error_count += 1
                    debug_info.append(f"  -> EXCEPTION: {str(e)}")
            
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
                error_msg = f'No valid data was uploaded. Please check your file format. Debug info: {" | ".join(debug_info[:10])}'
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

def pl_report_data(request):
    """P&L Report data in JSON format for AG Grid, с нормализацией месяцев и фильтром по диапазону."""
    logger.info("--- P&L Report Data Generation Started ---")
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    logger.info(f"Parameters: from_month={from_month}, from_year={from_year}, to_month={to_month}, to_year={to_year}, data_type={data_type}")

    # Помощники для нормализации месяцев
    def month_start(d: date) -> date:
        return date(d.year, d.month, 1)
    def next_month(d: date) -> date:
        if d.month == 12:
            return date(d.year + 1, 1, 1)
        return date(d.year, d.month + 1, 1)

    # Превращаем выбор пользователя в месячный диапазон [start, end_exclusive)
    from_date_start, _ = convert_month_year_to_date_range(from_month, from_year)
    _, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    start = month_start(from_date_start) if from_date_start else None
    end_exclusive = next_month(to_date_end) if to_date_end else None

    # Компании
    companies = list(Company.objects.all().order_by('name'))
    logger.info(f"Found {len(companies)} companies.")

    # ВАЖНОЕ ИЗМЕНЕНИЕ: Фильтруем только P&L счета (INCOME и EXPENSE)
    chart_accounts_all = list(ChartOfAccounts.objects.filter(
        account_type__in=['INCOME', 'EXPENSE']
    ).order_by('sort_order'))
    chart_accounts = [a for a in chart_accounts_all if (a.account_code or '').strip()]
    logger.info(f"P&L ChartOfAccounts: total={len(chart_accounts_all)}, with_code={len(chart_accounts)}")
    
    # Получаем список всех P&L account_codes для фильтрации
    pl_account_codes = [a.account_code for a in chart_accounts if a.account_code]

    # Периоды: берём только там, где реально есть P&L данные
    try:
        q = FinancialData.objects.filter(
            data_type=data_type,
            account_code__in=pl_account_codes  # Фильтруем только P&L счета
        )
        if start:
            q = q.filter(period__gte=start)
        if end_exclusive:
            q = q.filter(period__lt=end_exclusive)
        if companies:
            q = q.filter(company_id__in=[c.id for c in companies])
        periods = list(q.values_list('period', flat=True).distinct().order_by('period'))
        logger.info(f"Found {len(periods)} periods with P&L data.")
        
        # Если периодов нет, проверяем есть ли вообще P&L данные
        if not periods:
            all_pl_periods = list(FinancialData.objects.filter(
                account_code__in=pl_account_codes
            ).values_list('period', flat=True).distinct().order_by('period'))
            logger.warning(f"No P&L data in selected range. Available P&L periods: {all_pl_periods[:10]}")
            
            # Предлагаем использовать доступный диапазон
            if all_pl_periods:
                suggested_start = all_pl_periods[0].strftime('%B %Y')
                suggested_end = all_pl_periods[-1].strftime('%B %Y')
                return JsonResponse({
                    'columnDefs': [],
                    'rowData': [],
                    'error': f'No P&L data found for selected period. P&L data is available from {suggested_start} to {suggested_end}',
                    'available_range': {
                        'start': all_pl_periods[0].strftime('%Y-%m-%d'),
                        'end': all_pl_periods[-1].strftime('%Y-%m-%d')
                    }
                })
    except Exception as e:
        logger.error(f"Error fetching periods: {e}")
        periods = []

    if not periods:
        logger.warning("No P&L periods found, returning empty data.")
        return JsonResponse({
            'columnDefs': [],
            'rowData': [],
            'error': 'No P&L data found. Please check if Income and Expense accounts are properly loaded.'
        })

    # Загружаем только P&L данные за выбранные периоды и компании
    all_financial_data = list(
        FinancialData.objects.filter(
            data_type=data_type,
            period__in=periods,
            company_id__in=[c.id for c in companies],
            account_code__in=pl_account_codes  # Только P&L счета
        ).select_related('company')
    )
    logger.info(f"Found {len(all_financial_data)} P&L financial data records.")
    
    # Добавляем детальное отладочное логирование
    if all_financial_data:
        sample = all_financial_data[0]
        logger.info(f"Sample record: company={sample.company.code} (id={sample.company.id}), account={sample.account_code}, amount={sample.amount}, period={sample.period}")
    
    # Проверяем данные по компаниям
    for c in companies:
        company_data_count = len([fd for fd in all_financial_data if fd.company.id == c.id])
        logger.info(f"Company {c.code} (id={c.id}): {company_data_count} records")
    
    # Получаем список компаний которые реально имеют данные
    companies_with_data = list(set(fd.company for fd in all_financial_data))
    if not companies_with_data:
        logger.warning("No companies with data found, using all companies as fallback")
        companies_with_data = companies
    else:
        logger.info(f"Companies with data: {[c.code for c in companies_with_data]}")

    # Индексация: period -> company_code -> account_code -> amount
    financial_data = {}
    for p in periods:
        financial_data[p] = {}
        for c in companies_with_data:  # Используем только компании с данными
            financial_data[p][c.code] = {}
    
    # Заполняем financial_data с проверками
    for fd in all_financial_data:
        p = fd.period
        ccode = fd.company.code
        logger.debug(f"Processing: period={p}, company={ccode}, account={fd.account_code}, amount={fd.amount}")
        
        if p in financial_data and ccode in financial_data[p]:
            financial_data[p][ccode][fd.account_code] = fd.amount
            logger.debug(f"Added to financial_data[{p}][{ccode}][{fd.account_code}] = {fd.amount}")
        else:
            logger.warning(f"Failed to add: period={p}, company={ccode} not found in financial_data structure")
    
    # Проверяем что получилось в financial_data
    if periods:
        p0 = periods[0]
        logger.info(f"Financial data structure for period {p0}:")
        for ccode in financial_data[p0]:
            account_count = len(financial_data[p0][ccode])
            logger.info(f"  Company {ccode}: {account_count} accounts")
            if account_count > 0:
                sample_accounts = list(financial_data[p0][ccode].keys())[:3]
                logger.info(f"    Sample accounts: {sample_accounts}")

    # Лог первого периода
    if periods:
        p0 = periods[0]
        for c in companies[:2]:
            sample_accounts = list(financial_data[p0][c.code].keys())[:3]
            logger.info(f"Period {p0}, Company {c.code}, P&L accounts sample: {sample_accounts}")

    # Группировка COA по sub_category для структуры
    grouped_data = {}
    for acc in chart_accounts_all:
        sub_category = acc.sub_category or 'UNCATEGORIZED'
        grouped_data.setdefault(sub_category, []).append(acc)
    logger.info(f"Grouped P&L sub_categories: {list(grouped_data.keys())[:10]}")

    # Порядок разделов для P&L
    correct_order = [
        # Revenue sections
        'INTEREST + DEFAULT',
        'Other Income',
        # Expense sections  
        'COST OF FUNDS AND FEES',
        'Salaries',
        'Fund related',
        'Triple Point funding line related',
        'OakNorth funding line related',
        'Marketing',
        'Administration',
        'Other Expenses'
    ]
    all_sub = list(grouped_data.keys())
    pl_structure = [c for c in correct_order if c in all_sub] + [c for c in all_sub if c not in correct_order]
    logger.info(f"Ordered P&L sub categories: {pl_structure}")

    # Сборка отчета
    report_data = []
    debug_info = {
        'periods_count': len(periods),
        'companies_count': len(companies),
        'pl_accounts_count': len(chart_accounts),
        'financial_data_count': len(all_financial_data),
        'periods': [p.strftime('%Y-%m-%d') for p in periods[:6]],
        'companies': [c.code for c in companies],
        'companies_with_data': [c.code for c in companies_with_data],
        'companies_without_data': [c.code for c in companies if c not in companies_with_data]
    }
    
    # Добавляем счетчики по типам
    income_count = ChartOfAccounts.objects.filter(account_type='INCOME', account_code__in=pl_account_codes).count()
    expense_count = ChartOfAccounts.objects.filter(account_type='EXPENSE', account_code__in=pl_account_codes).count()
    debug_info['income_accounts'] = income_count
    debug_info['expense_accounts'] = expense_count
    
    if all_financial_data:
        debug_info['sample_financial_data'] = [{
            'company': all_financial_data[0].company.code,
            'account': all_financial_data[0].account_code,
            'period': str(all_financial_data[0].period),
            'amount': float(all_financial_data[0].amount)
        }]

    # (Removed visual REVENUE section header to simplify layout)
    
    # Обрабатываем Income счета
    income_accounts = [a for a in chart_accounts if a.account_type == 'INCOME']
    for sub_category in pl_structure:
        if sub_category not in grouped_data:
            continue
            
        # Проверяем есть ли Income счета в этой категории
        category_accounts = [a for a in grouped_data[sub_category] if a.account_type == 'INCOME' and a.account_code]
        if not category_accounts:
            continue

        # Подзаголовок
        report_data.append({
            'type': 'sub_header',
            'account_name': sub_category,
            'account_code': '',
            'periods': {},
            'grand_totals': {}
        })

        # Счета
        for acc in category_accounts:
            row = {
                'type': 'account',
                'account_name': acc.account_name,
                'account_code': acc.account_code,
                'periods': {},
                'grand_totals': {}
            }
            has_non_zero_value = False
            # Помесячно
            for p in periods:
                row['periods'][p] = {}
                period_total = Decimal('0')
                for c in companies_with_data:  # Используем только компании с данными
                    amount = financial_data[p][c.code].get(acc.account_code, Decimal('0'))
                    row['periods'][p][c.code] = float(amount or Decimal('0'))
                    period_total += amount or Decimal('0')
                    if amount != 0:
                        has_non_zero_value = True
                row['periods'][p]['TOTAL'] = float(period_total or Decimal('0'))

            # Гранд тоталы
            for c in companies_with_data:  # Используем только компании с данными
                grand_total = sum(financial_data[p][c.code].get(acc.account_code, Decimal('0')) for p in periods)
                row['grand_totals'][c.code] = float(grand_total or Decimal('0'))
            overall = sum(
                sum(financial_data[p][c.code].get(acc.account_code, Decimal('0')) for c in companies_with_data)
                for p in periods
            )
            row['grand_totals']['TOTAL'] = float(overall or Decimal('0'))

            if has_non_zero_value:
                report_data.append(row)

        # Субитог секции
        sub_total = {
            'type': 'sub_total',
            'account_name': f'Total {sub_category}',
            'account_code': '',
            'periods': {},
            'grand_totals': {}
        }
        for p in periods:
            sub_total['periods'][p] = {}
            period_total = Decimal('0')
            for c in companies_with_data:  # Используем только компании с данными
                company_total = sum(
                    financial_data[p][c.code].get(a.account_code, Decimal('0'))
                    for a in category_accounts
                )
                sub_total['periods'][p][c.code] = float(company_total or Decimal('0'))
                period_total += company_total or Decimal('0')
            sub_total['periods'][p]['TOTAL'] = float(period_total or Decimal('0'))

        for c in companies_with_data:  # Используем только компании с данными
            gtot = sum(
                sum(financial_data[p][c.code].get(a.account_code, Decimal('0')) for a in category_accounts)
                for p in periods
            )
            sub_total['grand_totals'][c.code] = float(gtot or Decimal('0'))
        overall = sum(
            sum(sum(financial_data[p][c.code].get(a.account_code, Decimal('0')) for a in category_accounts) for c in companies_with_data)
            for p in periods
        )
        sub_total['grand_totals']['TOTAL'] = float(overall or Decimal('0'))
        report_data.append(sub_total)

    # Total Revenue
    total_revenue_row = {
        'type': 'total',
        'account_name': 'TOTAL REVENUE',
        'account_code': '',
        'periods': {},
        'grand_totals': {}
    }
    for p in periods:
        total_revenue_row['periods'][p] = {}
        period_total = Decimal('0')
        for c in companies_with_data:  # Используем только компании с данными
            company_total = sum(
                financial_data[p][c.code].get(a.account_code, Decimal('0'))
                for a in income_accounts
            )
            total_revenue_row['periods'][p][c.code] = float(company_total or Decimal('0'))
            period_total += company_total or Decimal('0')
        total_revenue_row['periods'][p]['TOTAL'] = float(period_total or Decimal('0'))
    # Grand totals for revenue
    for c in companies_with_data:  # Используем только компании с данными
        gtot = sum(
            sum(financial_data[p][c.code].get(a.account_code, Decimal('0')) for a in income_accounts)
            for p in periods
        )
        total_revenue_row['grand_totals'][c.code] = float(gtot or Decimal('0'))
    overall_revenue = sum(
        sum(sum(financial_data[p][c.code].get(a.account_code, Decimal('0')) for a in income_accounts) for c in companies_with_data)
        for p in periods
    )
    total_revenue_row['grand_totals']['TOTAL'] = float(overall_revenue or Decimal('0'))
    report_data.append(total_revenue_row)
    
    # Добавляем раздел EXPENSES
    expense_total_row = {
        'type': 'section_header',
        'account_name': 'EXPENSES',
        'account_code': '',
        'periods': {},
        'grand_totals': {}
    }
    report_data.append(expense_total_row)
    
    # Обрабатываем Expense счета
    expense_accounts = [a for a in chart_accounts if a.account_type == 'EXPENSE']
    for sub_category in pl_structure:
        if sub_category not in grouped_data:
            continue
            
        # Проверяем есть ли Expense счета в этой категории
        category_accounts = [a for a in grouped_data[sub_category] if a.account_type == 'EXPENSE' and a.account_code]
        if not category_accounts:
            continue

        # Подзаголовок
        report_data.append({
            'type': 'sub_header',
            'account_name': sub_category,
            'account_code': '',
            'periods': {},
            'grand_totals': {}
        })

        # Счета (аналогично Income)
        for acc in category_accounts:
            row = {
                'type': 'account',
                'account_name': acc.account_name,
                'account_code': acc.account_code,
                'periods': {},
                'grand_totals': {}
            }
            has_non_zero_value = False
            # Помесячно
            for p in periods:
                row['periods'][p] = {}
                period_total = Decimal('0')
                for c in companies:
                    amount = financial_data[p][c.code].get(acc.account_code, 0)
                    row['periods'][p][c.code] = float(amount or 0)
                    period_total += amount or 0
                    if amount != 0:
                        has_non_zero_value = True
                row['periods'][p]['TOTAL'] = float(period_total or 0)

            # Гранд тоталы
            for c in companies:
                grand_total = sum(financial_data[p][c.code].get(acc.account_code, 0) for p in periods)
                row['grand_totals'][c.code] = float(grand_total or 0)
            overall = sum(
                sum(financial_data[p][c.code].get(acc.account_code, 0) for c in companies)
                for p in periods
            )
            row['grand_totals']['TOTAL'] = float(overall or 0)

            if has_non_zero_value:
                report_data.append(row)

        # Субитог секции
        sub_total = {
            'type': 'sub_total',
            'account_name': f'Total {sub_category}',
            'account_code': '',
            'periods': {},
            'grand_totals': {}
        }
        for p in periods:
            sub_total['periods'][p] = {}
            period_total = Decimal('0')
            for c in companies:
                company_total = sum(
                    financial_data[p][c.code].get(a.account_code, 0)
                    for a in category_accounts
                )
                sub_total['periods'][p][c.code] = float(company_total or 0)
                sub_total['periods'][p]['TOTAL'] = float(period_total or 0)

        for c in companies:
            gtot = sum(
                sum(financial_data[p][c.code].get(a.account_code, 0) for a in category_accounts)
                for p in periods
            )
            sub_total['grand_totals'][c.code] = float(gtot or 0)
        overall = sum(
            sum(sum(financial_data[p][c.code].get(a.account_code, 0) for a in category_accounts) for c in companies)
            for p in periods
        )
        sub_total['grand_totals']['TOTAL'] = float(overall or 0)
        report_data.append(sub_total)

    # Total Expenses
    total_expense_row = {
        'type': 'total',
        'account_name': 'TOTAL EXPENSES',
        'account_code': '',
        'periods': {},
        'grand_totals': {}
    }
    for p in periods:
        total_expense_row['periods'][p] = {}
        period_total = Decimal('0')
        for c in companies:
            company_total = sum(
                financial_data[p][c.code].get(a.account_code, 0)
                for a in expense_accounts
            )
            total_expense_row['periods'][p][c.code] = float(company_total or 0)
            period_total += company_total or 0
        total_expense_row['periods'][p]['TOTAL'] = float(period_total or 0)
    # Grand totals for expenses
    for c in companies:
        gtot = sum(
            sum(financial_data[p][c.code].get(a.account_code, 0) for a in expense_accounts)
            for p in periods
        )
        total_expense_row['grand_totals'][c.code] = float(gtot or 0)
    overall_expense = sum(
        sum(sum(financial_data[p][c.code].get(a.account_code, 0) for a in expense_accounts) for c in companies)
        for p in periods
    )
    total_expense_row['grand_totals']['TOTAL'] = float(overall_expense or 0)
    report_data.append(total_expense_row)
    
    # NET INCOME (Revenue - Expenses)
    net_income_row = {
        'type': 'net_income',
        'account_name': 'NET INCOME',
        'account_code': '',
        'periods': {},
        'grand_totals': {}
    }
    for p in periods:
        net_income_row['periods'][p] = {}
        period_total = Decimal('0')
        for c in companies:
            revenue = Decimal(str(total_revenue_row['periods'][p][c.code]))
            expense = Decimal(str(total_expense_row['periods'][p][c.code]))
            net = revenue - expense
            net_income_row['periods'][p][c.code] = float(net)
            period_total += net
        net_income_row['periods'][p]['TOTAL'] = float(period_total)
    # Grand totals for net income
    for c in companies:
        revenue = Decimal(str(total_revenue_row['grand_totals'][c.code]))
        expense = Decimal(str(total_expense_row['grand_totals'][c.code]))
        net_income_row['grand_totals'][c.code] = float(revenue - expense)
    net_income_row['grand_totals']['TOTAL'] = float(Decimal(str(total_revenue_row['grand_totals']['TOTAL'])) - Decimal(str(total_expense_row['grand_totals']['TOTAL'])))
    report_data.append(net_income_row)

    # Колонки AG Grid
    column_defs = [
        {
            "headerName": "+",
            "field": "toggler",
            "headerComponent": "togglerHeader",
            "width": 40,
            "pinned": "left",
            "hide": False
        },
        {
            "field": "account_code",
            "colId": "account_code",
            "headerName": "A/C",
            "headerComponent": "hideableHeader",
            "width": 90,
            "pinned": "left",
            "hide": True,
            "sortable": True
        },
        {'field': 'account_name', 'headerName': 'Account Name', 'pinned': 'left', 'width': 250}
    ]
    for p in periods:
        for c in companies:
            column_defs.append({
                'field': f'{p.strftime("%b-%y")}_{c.code}',
                'headerName': f'{p.strftime("%b-%y")} {c.code}',
                'width': 120,
                'type': 'numberColumnWithCommas',
                'cellStyle': {
                    'textAlign': 'right',
                    'backgroundColor': '#E6F3FF' if str(c.code).upper().startswith('F2') else '#E8F5E9'
                }
            })
        # P&L TOTAL per period (existing)
        column_defs.append({
            'field': f'{p.strftime("%b-%y")}_TOTAL',
            'headerName': f'{p.strftime("%b-%y")} TOTAL',
            'width': 120,
            'type': 'numberColumnWithCommas',
            'cellStyle': {
                'textAlign': 'right',
                'backgroundColor': '#FFF9E6'
            }
        })
        # Add Budget/Forecast consolidated column when viewing Budget or Forecast
        if data_type in ['budget', 'forecast']:
            column_defs.append({
                'headerName': f'{p.strftime("%b-%y")} Budget',
                'field': f'{p.strftime("%b-%y")}_Budget',
                'type': 'numberColumnWithCommas',
                'cellClass': 'budget-cell',
                'width': 120
            })
        # CF Dashboard TOTAL per period removed to avoid duplicate TOTAL columns
    for c in companies:
        column_defs.append({
            'field': f'grand_total_{c.code}',
            'headerName': f'Grand Total {c.code}',
            'width': 120,
            'type': 'numberColumnWithCommas'
        })
    column_defs.append({
        'field': 'grand_total_TOTAL',
        'headerName': 'Grand Total',
        'width': 120,
        'type': 'numberColumnWithCommas'
    })

    # CF Dashboard section - loan movements and funding metrics
    cf_metrics = CFDashboardMetric.objects.filter(is_active=True).order_by('display_order')
    cf_data = CFDashboardData.objects.filter(
        company__in=companies,
        period__gte=from_date_start,
        period__lte=to_date_end
    ).select_related('metric', 'company')
    
    # Load CF Dashboard Budget/Forecast data (consolidated, not per company)
    from .models import CFDashboardBudget
    cf_budget_data = CFDashboardBudget.objects.filter(
        data_type=data_type if data_type in ['budget', 'forecast'] else 'budget',
        period__gte=from_date_start,
        period__lte=to_date_end
    ).select_related('metric')
    
    # Build CF Dashboard rows
    cf_rows = []
    for metric in cf_metrics:
        row = {
            'account_code': '',
            'account_name': metric.metric_name,
            'is_cf_dashboard': True,
            'metric_id': metric.id
        }
        
        # Identify metric type
        name_val = metric.metric_name or ''
        is_cumulative_metric = 'Cumulative' in name_val
        is_ytd_metric = ('YTD' in name_val) and not is_cumulative_metric
        
        previous_total = 0  # for YTD accumulation of TOTAL only
        loans_advanced_row = None
        
        # If cumulative, try to find the already-built "Loans advanced in month" row
        if is_cumulative_metric:
            for existing_row in cf_rows:
                if 'Loans advanced in month' in (existing_row.get('account_name') or ''):
                    loans_advanced_row = existing_row
                    break
        
        # Process each period
        for period in periods:
            period_total = 0
            
            # Get values for each company
            for company in companies:
                period_key = f"{period.strftime('%b-%y')}_{company.code}"
                
                if is_cumulative_metric:
                    # For January: use input value for cumulative metric
                    if period.month == 1:
                        cf_value = cf_data.filter(
                            company=company,
                            period=period,
                            metric=metric
                        ).values_list('value', flat=True).first()
                        value = cf_value or 0
                    else:
                        # Feb-Dec: previous month cumulative + current month loans advanced
                        prev_month = period.month - 1
                        prev_period = period.replace(month=prev_month)
                        prev_key = f"{prev_period.strftime('%b-%y')}_{company.code}"
                        prev_cumulative = row.get(prev_key, 0)
                        current_loans = 0
                        if loans_advanced_row is not None:
                            current_loans = loans_advanced_row.get(period_key, 0) or 0
                        value = (prev_cumulative or 0) + (current_loans or 0)
                else:
                    # Regular or YTD metric: use input values per company-month
                    cf_value = cf_data.filter(
                        company=company,
                        period=period,
                        metric=metric
                    ).values_list('value', flat=True).first()
                    value = cf_value or 0
                
                row[period_key] = value
                period_total += value
            
            # Calculate TOTAL column
            period_total_key = f"{period.strftime('%b-%y')}_TOTAL"
            if is_ytd_metric:
                current_ytd_total = previous_total + period_total
                row[period_total_key] = current_ytd_total
                previous_total = current_ytd_total
            else:
                row[period_total_key] = period_total
            
            # Add Budget/Forecast consolidated value for this period (single column)
            if data_type in ['budget', 'forecast']:
                period_budget_key = f"{period.strftime('%b-%y')}_Budget"
                budget_value = cf_budget_data.filter(
                    metric=metric,
                    period=period
                ).values_list('value', flat=True).first()
                row[period_budget_key] = float(budget_value) if budget_value is not None else None
        
        cf_rows.append(row)

    # Данные строк для AG Grid
    row_data = []
    
    # Add CF Dashboard rows at the top
    for cf_row in cf_rows:
        row_data.append(cf_row)
    
    # Add visual separator after CF Dashboard
    if cf_rows:
        row_data.append({
            'account_code': '',
            'account_name': '━' * 30 + ' P&L REPORT ' + '━' * 30,
            'is_separator': True
        })
    
    # Then add regular P&L rows
    for r in report_data:
        grid_row = {
            'account_code': r['account_code'],
            'account_name': r['account_name'],
            'rowType': r['type']
        }
        for p in periods:
            for c in companies:
                field = f'{p.strftime("%b-%y")}_{c.code}'
                value = r['periods'].get(p, {}).get(c.code, 0)
                # Send None for zero values so grid shows empty cells
                grid_row[field] = None if value == 0 else float(value)
            field_total = f'{p.strftime("%b-%y")}_TOTAL'
            total_value = r['periods'].get(p, {}).get('TOTAL', 0)
            # Hide zeros in TOTAL columns as well
            grid_row[field_total] = None if total_value == 0 else float(total_value)
        for c in companies:
            field = f'grand_total_{c.code}'
            gt_val = r['grand_totals'].get(c.code, 0)
            # Hide zero company grand totals by sending None
            grid_row[field] = None if gt_val == 0 else float(gt_val)
        # Overall grand total: hide zero as empty
        overall_total_value = r['grand_totals'].get('TOTAL', 0)
        grid_row['grand_total_TOTAL'] = None if overall_total_value == 0 else float(overall_total_value)

        # Стили для разных типов строк
        if r['type'] == 'section_header':
            grid_row['cellStyle'] = {'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'fontSize': '15px'}
        elif r['type'] == 'sub_header':
            grid_row['cellStyle'] = {'backgroundColor': '#f0f8ff', 'fontWeight': 'bold'}
        elif r['type'] == 'sub_total':
            grid_row['cellStyle'] = {'backgroundColor': '#fff8dc', 'fontWeight': 'bold'}
        elif r['type'] == 'total':
            grid_row['cellStyle'] = {'backgroundColor': '#e8f5e8', 'fontWeight': 'bold', 'fontSize': '14px'}
        elif r['type'] == 'net_income':
            grid_row['cellStyle'] = {'backgroundColor': '#ffeaa7', 'fontWeight': 'bold', 'fontSize': '15px'}

        row_data.append(grid_row)

    logger.info(f"Final P&L report data count: {len(report_data)}")
    logger.info("--- P&L Report Data Generation Finished ---")

    debug_info['ping'] = 'pl_report_data v4 - Fixed indexing and Decimal types'

    return JsonResponse({
        'columnDefs': column_defs,
        'rowData': row_data,
        'debug_info': debug_info
    })

def bs_report_data(request):
    """Balance Sheet Report data in JSON format for AG Grid."""
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    
    from_date_start, from_date_end = convert_month_year_to_date_range(from_month, from_year)
    to_date_start, to_date_end = convert_month_year_to_date_range(to_month, to_year)
    
    # Get all companies
    companies = list(Company.objects.all().order_by('name'))
    
    # Get ASSET, LIABILITY, EQUITY accounts from ChartOfAccounts
    bs_types = [
        'ASSET', 'LIABILITY', 'EQUITY',
        'Bank', 'Fixed Asset', 'Other Current Asset', 'Other Asset',
        'Other Current Liabilities', 'Other Current Liability',
        'Equity'
    ]
    q_objects = Q()
    for t in bs_types:
        q_objects |= Q(account_type__iexact=t)
    chart_accounts = list(ChartOfAccounts.objects.filter(q_objects).order_by('sort_order'))
    
    # If ChartOfAccounts is empty, return empty data
    if not chart_accounts:
        logger.warning("ChartOfAccounts is empty for Balance Sheet")
        return JsonResponse({
            'columnDefs': [],
            'rowData': []
        })
    
    # Get unique periods from FinancialData with proper filtering
    try:
        financial_data_query = FinancialData.objects.filter(data_type=data_type)
        
        if from_date_start:
            financial_data_query = financial_data_query.filter(period__gte=from_date_start)
        if to_date_end:
            financial_data_query = financial_data_query.filter(period__lte=to_date_end)
        
        periods = list(financial_data_query.values_list('period', flat=True).distinct().order_by('period'))
    except Exception as e:
        periods = []
    
    # If no periods, return empty data
    if not periods:
        return JsonResponse({
            'columnDefs': [],
            'rowData': []
        })
    
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
    ).select_related('company')
    
    # Organize financial data by period, company, and account
    for fd in all_financial_data:
        if fd.period in financial_data and fd.company.code in financial_data[fd.period]:
            financial_data[fd.period][fd.company.code][fd.account_code] = fd.amount
    
    # Group accounts by parent_category and sub_category from ChartOfAccounts
    grouped_data = {}
    
    for account in chart_accounts:
        # Use parent_category and sub_category directly from ChartOfAccounts
        parent_category = account.parent_category or 'UNCATEGORIZED'
        sub_category = account.sub_category or 'UNCATEGORIZED'
        
        # Create parent category if it doesn't exist
        if parent_category not in grouped_data:
            grouped_data[parent_category] = {}
        
        # Create sub category if it doesn't exist
        if sub_category not in grouped_data[parent_category]:
            grouped_data[parent_category][sub_category] = []
        
        # Add account to sub category
        grouped_data[parent_category][sub_category].append(account)
    
    # Build report data with hierarchical structure
    report_data = []
    
    # Fixed order for Balance Sheet structure - use parent categories (current abbreviations)
    bs_structure = ['BA', 'FA', 'OCA', 'OCL', 'OC', 'EQ']
    
    # Process each parent category in the fixed order
    for parent_category in bs_structure:
        if parent_category not in grouped_data:
            continue
        
        # Add parent header
        report_data.append({
            'type': 'parent_header',
            'account_name': parent_category,
            'account_code': '',
            'periods': {},
            'grand_totals': {}
        })
        
        # Process sub categories
        for sub_category, accounts in grouped_data[parent_category].items():
            # Add sub header
            report_data.append({
                'type': 'sub_header',
                'account_name': sub_category,
                'account_code': '',
                'periods': {},
                'grand_totals': {}
            })
            
            # Process individual accounts
            for account in accounts:
                row_data = {
                    'type': 'account',
                    'account_name': account.account_name,
                    'account_code': account.account_code,
                    'periods': {},
                    'grand_totals': {}
                }
                
                # Calculate period totals for each company
                for period in periods:
                    row_data['periods'][period] = {}
                    period_total = 0
                    
                    for company in companies:
                        amount = financial_data[period][company.code].get(account.account_code, 0)
                        # Convert to float for AG Grid
                        row_data['periods'][period][company.code] = float(amount or 0)
                        period_total += amount or 0
                    
                    row_data['periods'][period]['TOTAL'] = float(period_total or 0)
                
                # Calculate grand totals
                for company in companies:
                    grand_total = sum(
                        financial_data[period][company.code].get(account.account_code, 0)
                        for period in periods
                    )
                    row_data['grand_totals'][company.code] = float(grand_total or 0)
                
                # Calculate overall grand total
                overall_grand_total = sum(
                    sum(financial_data[period][company.code].get(account.account_code, 0) for company in companies)
                    for period in periods
                )
                row_data['grand_totals']['TOTAL'] = float(overall_grand_total or 0)
                
                report_data.append(row_data)
            
            # Add sub total
            sub_total_data = {
                'type': 'sub_total',
                'account_name': f'Total {sub_category}',
                'account_code': '',
                'periods': {},
                'grand_totals': {}
            }
            
            # Calculate sub totals
            for period in periods:
                sub_total_data['periods'][period] = {}
                period_total = 0
                
                for company in companies:
                    company_total = sum(
                        financial_data[period][company.code].get(account.account_code, 0)
                        for account in accounts
                    )
                    sub_total_data['periods'][period][company.code] = float(company_total or 0)
                    period_total += company_total or 0
                
                sub_total_data['periods'][period]['TOTAL'] = float(period_total or 0)
            
            # Calculate grand totals for sub category
            for company in companies:
                grand_total = sum(
                    sum(financial_data[period][company.code].get(account.account_code, 0) for account in accounts)
                    for period in periods
                )
                sub_total_data['grand_totals'][company.code] = float(grand_total or 0)
            
            # Calculate overall grand total for sub category
            overall_grand_total = sum(
                sum(sum(financial_data[period][company.code].get(account.account_code, 0) for account in accounts) for company in companies)
                for period in periods
            )
            sub_total_data['grand_totals']['TOTAL'] = float(overall_grand_total or 0)
            
            report_data.append(sub_total_data)
        
        # Add parent total
        parent_total_data = {
            'type': 'parent_total',
            'account_name': f'TOTAL {parent_category}',
            'account_code': '',
            'periods': {},
            'grand_totals': {}
        }
        
        # Calculate parent totals
        for period in periods:
            parent_total_data['periods'][period] = {}
            period_total = 0
            
            for company in companies:
                company_total = sum(
                    sum(financial_data[period][company.code].get(account.account_code, 0) for account in sub_accounts)
                    for sub_accounts in grouped_data[parent_category].values()
                )
                parent_total_data['periods'][period][company.code] = float(company_total or 0)
                period_total += company_total or 0
            
            parent_total_data['periods'][period]['TOTAL'] = float(period_total or 0)
        
        # Calculate grand totals for parent category
        for company in companies:
            grand_total = sum(
                sum(sum(financial_data[period][company.code].get(account.account_code, 0) for account in sub_accounts) for sub_accounts in grouped_data[parent_category].values())
                for period in periods
            )
            parent_total_data['grand_totals'][company.code] = float(grand_total or 0)
        
        # Calculate overall grand total for parent category
        overall_grand_total = sum(
            sum(sum(sum(financial_data[period][company.code].get(account.account_code, 0) for account in sub_accounts) for sub_accounts in grouped_data[parent_category].values()) for company in companies)
            for period in periods
        )
        parent_total_data['grand_totals']['TOTAL'] = float(overall_grand_total or 0)
        
        report_data.append(parent_total_data)
    
    # Add CHECK row at bottom: TOTAL ASSETS - TOTAL LIABILITIES - TOTAL EQUITY (should equal 0)
    if 'ASSETS' in grouped_data and ('LIABILITIES' in grouped_data or 'EQUITY' in grouped_data):
        # Calculate totals for each category
        assets_total = 0
        liabilities_total = 0
        equity_total = 0
        
        if 'ASSETS' in grouped_data:
            assets_total = sum(
                sum(sum(financial_data[period][company.code].get(account.account_code, 0) for account in sub_accounts) for sub_accounts in grouped_data['ASSETS'].values())
                for period in periods
                for company in companies
            )
        
        if 'LIABILITIES' in grouped_data:
            liabilities_total = sum(
                sum(sum(financial_data[period][company.code].get(account.account_code, 0) for account in sub_accounts) for sub_accounts in grouped_data['LIABILITIES'].values())
                for period in periods
                for company in companies
            )
        
        if 'EQUITY' in grouped_data:
            equity_total = sum(
                sum(sum(financial_data[period][company.code].get(account.account_code, 0) for account in sub_accounts) for sub_accounts in grouped_data['EQUITY'].values())
                for period in periods
                for company in companies
            )
        
        check_value = assets_total - liabilities_total - equity_total
        
        report_data.append({
            'type': 'check_row',
            'account_name': 'CHECK (Assets - Liabilities - Equity)',
            'account_code': '',
            'periods': {period: {'TOTAL': float(check_value or 0)} for period in periods},
            'grand_totals': {'TOTAL': float(check_value or 0)}
        })
    
    # Prepare column definitions for AG Grid
    column_defs = [
        # The NEW toggler column
        {
            "headerName": "+", 
            "field": "toggler", # Can be any unique name
            "headerComponent": "togglerHeader", # We will create this in JavaScript
            "width": 40,
            "pinned": "left",
            "hide": False # This column is initially visible
        },
        # The MODIFIED A/C column
        {
            "field": "account_code", 
            "colId": "account_code", # Use colId for reliable access
            "headerName": "A/C",
            "headerComponent": "hideableHeader", # Custom header with a "-" button
            "width": 90, 
            "pinned": "left",
            "hide": True # This column is initially HIDDEN
        },
        {'field': 'account_name', 'headerName': 'Account Name', 'pinned': 'left', 'width': 250}
    ]
    
    # Add period columns
    for period in periods:
        for company in companies:
            column_defs.append({
                'field': f'{period.strftime("%b-%y")}_{company.code}',
                'headerName': f'{period.strftime("%b-%y")} {company.code}',
                'width': 120,
                'type': 'numberColumnWithCommas',
                'cellStyle': {
                    'textAlign': 'right',
                    'backgroundColor': '#E6F3FF' if str(company.code).upper().startswith('F2') else '#E8F5E9'
                }
            })
        column_defs.append({
            'field': f'{period.strftime("%b-%y")}_TOTAL',
            'headerName': f'{period.strftime("%b-%y")} TOTAL',
            'width': 120,
            'type': 'numberColumnWithCommas',
            'cellStyle': {
                'textAlign': 'right',
                'backgroundColor': '#FFF9E6'
            }
        })
    
    
    # Prepare row data for AG Grid
    row_data = []
    for row in report_data:
        grid_row = {
            'account_code': row['account_code'],
            'account_name': row['account_name'],
            'rowType': row['type']
        }
        
        # Add period data
        for period in periods:
            for company in companies:
                field_name = f'{period.strftime("%b-%y")}_{company.code}'
                value = row['periods'].get(period, {}).get(company.code, 0)
                grid_row[field_name] = float(value or 0)
            
            field_name = f'{period.strftime("%b-%y")}_TOTAL'
            value = row['periods'].get(period, {}).get('TOTAL', 0)
            grid_row[field_name] = float(value or 0)
        
        # Apply row styling based on type
        if row['type'] == 'parent_header':
            grid_row['cellStyle'] = {'backgroundColor': '#e8f5e8', 'fontWeight': 'bold', 'fontSize': '14px'}
        elif row['type'] == 'sub_header':
            grid_row['cellStyle'] = {'backgroundColor': '#f0f8ff', 'fontWeight': 'bold'}
        elif row['type'] == 'sub_total':
            grid_row['cellStyle'] = {'backgroundColor': '#fff8dc', 'fontWeight': 'bold'}
        elif row['type'] == 'parent_total':
            grid_row['cellStyle'] = {'backgroundColor': '#f0fff0', 'fontWeight': 'bold'}
        elif row['type'] == 'check_row':
            grid_row['cellStyle'] = {'backgroundColor': '#ffe6e6', 'fontWeight': 'bold'}
        
        row_data.append(grid_row)
    
    return JsonResponse({
        'columnDefs': column_defs,
        'rowData': row_data
    })

def pl_report(request):
    """P&L Report view - simplified to only render template, data comes from JSON endpoint."""
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')
    
    year_range = range(2023, 2031)
    
    context = {
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'data_type': data_type,
        'report_type': 'pl',
        'year_range': year_range
    }
    
    return render(request, 'core/pl_report.html', context)

def bs_report(request):
    """Balance Sheet Report view - simplified to only render template, data comes from JSON endpoint."""
    from_month = request.GET.get('from_month', '')
    from_year = request.GET.get('from_year', '')
    to_month = request.GET.get('to_month', '')
    to_year = request.GET.get('to_year', '')
    data_type = request.GET.get('data_type', 'actual')

    year_range = range(2023, 2031)

    context = {
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
    
    account_codes = accounts.values_list('account_code', flat=True)
    periods_query = FinancialData.objects.filter(account_code__in=account_codes)
    
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
                amount = FinancialData.objects.filter(
                    company=company,
                    account_code=account.account_code,
                    period=period,
                    data_type=data_type
                ).aggregate(total=Sum('amount'))['total'] or 0
                row.append(float(amount))
                period_total += amount
            row.append(float(period_total))
        
        excel_data.append(row)
    
    # Create DataFrame and export
    df = pd.DataFrame(excel_data[1:], columns=excel_data[0])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{report_title.lower().replace(" ", "_")}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=report_title, index=False)
    
    return response


@csrf_exempt
def update_cf_dashboard(request):
    """API endpoint for updating CF Dashboard values from inline editing"""
    print(f"Request method: {request.method}")
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            print(f"Received data: {data}")
            
            # Parse period from different formats
            period_str = data['period']
            print(f"Period string received: {period_str}")
            
            # Handle format "Jan-24" or "202401"
            if '-' in period_str:
                # Format: "Jan-24"
                month_map = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month_str, year_str = period_str.split('-')
                month = month_map.get(month_str, 1)
                year = 2000 + int(year_str) if len(year_str) == 2 else int(year_str)
            else:
                # Format: "202401"
                year = int(period_str[:4])
                month = int(period_str[4:6])
            
            period_date = date(year, month, 1)
            print(f"Parsed date: {period_date}")
            
            # Get company by code
            company = Company.objects.get(code__iexact=data['company_code'])
            print(f"Found company: {company}")
            
            # Get metric
            metric = CFDashboardMetric.objects.get(id=data['metric_id'])
            print(f"Found metric: {metric}")
            
            # Update or create the data
            cf_data, created = CFDashboardData.objects.update_or_create(
                company=company,
                period=period_date,
                metric=metric,
                defaults={'value': data['value']}
            )
            print(f"Data saved: {cf_data}, created: {created}")
            
            return JsonResponse({'status': 'success', 'created': created})
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
