from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from .models import Company, FinancialData, ChartOfAccounts, DataBackup, CFDashboardMetric, CFDashboardData
import json
from datetime import datetime

# Register your models here.

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    ordering = ['code']



@admin.register(FinancialData)
class FinancialDataAdmin(admin.ModelAdmin):
    list_display = ['company', 'account_code', 'period', 'amount', 'data_type']
    list_filter = ['company', 'data_type', 'period']
    search_fields = ['company__name', 'company__code', 'account_code']
    date_hierarchy = 'period'
    ordering = ['-period', 'company', 'account_code']

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ['sort_order', 'account_code', 'account_name', 'account_type', 'parent_category', 'sub_category', 'is_header']
    list_filter = ['account_type', 'parent_category', 'sub_category', 'is_header']
    search_fields = ['account_code', 'account_name', 'parent_category', 'sub_category']
    ordering = ['sort_order']
    list_editable = ['sort_order']
    list_display_links = ['account_name']

@admin.register(DataBackup)
class DataBackupAdmin(admin.ModelAdmin):
    list_display = ['backup_date', 'company', 'data_type', 'periods_summary', 'user', 'description', 'restore_button']
    list_filter = ['company', 'data_type', 'backup_date']
    search_fields = ['company__name', 'company__code', 'user', 'description']
    ordering = ['-backup_date']
    readonly_fields = ['backup_date', 'periods', 'backup_data', 'user', 'description']
    
    def periods_summary(self, obj):
        """Show a summary of backed up periods."""
        try:
            periods = json.loads(obj.periods)
            if len(periods) <= 3:
                return ", ".join(periods)
            else:
                return f"{periods[0]} to {periods[-1]} ({len(periods)} periods)"
        except:
            return "Invalid periods data"
    periods_summary.short_description = "Periods"
    
    def restore_button(self, obj):
        """Create a restore button for each backup."""
        return format_html(
            '<a class="button" href="{}">Restore</a>',
            f'/admin/core/databackup/{obj.id}/restore/'
        )
    restore_button.short_description = "Actions"
    
    def get_urls(self):
        """Add custom URL for restore functionality."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:backup_id>/restore/',
                self.admin_site.admin_view(self.restore_backup),
                name='core_databackup_restore',
            ),
        ]
        return custom_urls + urls
    
    def restore_backup(self, request, backup_id):
        """Restore data from backup."""
        try:
            backup = DataBackup.objects.get(id=backup_id)
            
            # Create backup of current data before restoring
            current_data = FinancialData.objects.filter(
                company=backup.company,
                data_type=backup.data_type
            )
            
            if current_data.exists():
                # Get current periods
                current_periods = list(current_data.values_list('period', flat=True).distinct())
                current_periods_str = [p.strftime('%Y-%m-%d') for p in current_periods]
                
                # Create backup of current data
                current_backup_data = []
                for record in current_data:
                    current_backup_data.append({
                        'company_id': record.company.id,
                        'account_code': record.account_code,
                        'period': record.period.strftime('%Y-%m-%d'),
                        'amount': str(record.amount),
                        'data_type': record.data_type
                    })
                
                # Save current backup
                DataBackup.objects.create(
                    company=backup.company,
                    data_type=backup.data_type,
                    periods=json.dumps(current_periods_str),
                    backup_data=current_backup_data,
                    user=request.user.username if request.user.is_authenticated else 'Admin',
                    description=f"Auto-backup before restore on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            
            # Delete current data for this company and data type
            current_data.delete()
            
            # Restore backup data
            restored_count = 0
            for record_data in backup.backup_data:
                try:
                    # Get account
                    chart_of_account = ChartOfAccounts.objects.get(account_code=record_data['account_code'])
                    
                    # Create financial data record
                    FinancialData.objects.create(
                        company=backup.company,
                        account_code=chart_of_account.account_code,
                        period=datetime.strptime(record_data['period'], '%Y-%m-%d').date(),
                        amount=record_data['amount'],
                        data_type=backup.data_type
                    )
                    restored_count += 1
                except Exception as e:
                    messages.error(request, f"Error restoring record: {e}")
            
            messages.success(request, f"Successfully restored {restored_count} records from backup. Previous data was backed up.")
            
        except DataBackup.DoesNotExist:
            messages.error(request, "Backup not found.")
        except Exception as e:
            messages.error(request, f"Error restoring backup: {e}")
        
        return HttpResponseRedirect('/admin/core/databackup/')


@admin.register(CFDashboardMetric)
class CFDashboardMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'metric_code', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    ordering = ['display_order']


@admin.register(CFDashboardData)
class CFDashboardDataAdmin(admin.ModelAdmin):
    list_display = ['company', 'period', 'metric', 'value']
    list_filter = ['company', 'period', 'metric']
    search_fields = ['company__name', 'metric__metric_name']
    ordering = ['-period', 'company', 'metric__display_order']
    list_editable = ['value']  # Allow inline editing in admin
