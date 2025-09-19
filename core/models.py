from django.db import models
import calendar
from django.contrib.auth.models import User
from django.conf import settings

# Create your models here.

class Company(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    is_budget_only = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        verbose_name_plural = "Companies"

class FinancialData(models.Model):
    DATA_TYPES = [
        ('actual', 'Actual'),
        ('budget', 'Budget'),
        ('forecast', 'Forecast'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='financial_data')
    account_code = models.CharField(max_length=50, null=True, blank=True)  # Changed from ForeignKey to CharField
    period = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    
    def __str__(self):
        return f"{self.company.code} - {self.account_code} - {self.period} - {self.amount}"
    
    class Meta:
        verbose_name_plural = "Financial Data"
        unique_together = ['company', 'account_code', 'period', 'data_type']

class ChartOfAccounts(models.Model):
    ACCOUNT_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
    ]
    
    account_code = models.CharField(max_length=50, blank=True, null=True)
    account_name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, blank=True)
    parent_category = models.CharField(max_length=100, blank=True)
    sub_category = models.CharField(max_length=100, blank=True)
    formula = models.TextField(blank=True)
    sort_order = models.IntegerField()
    is_header = models.BooleanField(default=False)
    
    def __str__(self):
        if self.account_code:
            return f"{self.account_code} - {self.account_name}"
        else:
            return f"{self.account_name}"
    
    class Meta:
        verbose_name_plural = "Chart of Accounts"
        ordering = ['sort_order']

class SalaryData(models.Model):
    employee_id = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    month = models.IntegerField(choices=[(i, calendar.month_abbr[i]) for i in range(1, 13)])
    year = models.IntegerField()
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['employee_id', 'company', 'month', 'year']
        permissions = [
            ("view_salary_details", "Can view salary breakdown"),
        ]
        ordering = ['company', 'year', 'month', 'employee_name']
        
    def __str__(self):
        return f"{self.employee_name} - {self.company.code} - {self.month}/{self.year}"

class DataBackup(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='data_backups')
    backup_date = models.DateTimeField(auto_now_add=True)
    data_type = models.CharField(max_length=20, choices=FinancialData.DATA_TYPES)
    periods = models.TextField(help_text='JSON list of periods that were backed up')
    backup_data = models.JSONField(help_text='JSON data of all backed up records')
    user = models.CharField(max_length=100, blank=True, help_text='User who made the upload')
    description = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.company.code} - {self.data_type} - {self.backup_date.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        verbose_name_plural = "Data Backups"
        ordering = ['-backup_date']


class CFDashboardMetric(models.Model):
    """Flexible metrics for CF Dashboard - loan movements and funding"""
    metric_name = models.CharField(max_length=100, unique=True)  # e.g. "Loans advanced in month"
    metric_code = models.CharField(max_length=50, unique=True)  # e.g. "loans_advanced"
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['display_order', 'metric_name']
    
    def __str__(self):
        return self.metric_name


class CFDashboardData(models.Model):
    """Actual data values for CF Dashboard metrics"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    period = models.DateField()
    metric = models.ForeignKey(CFDashboardMetric, on_delete=models.CASCADE)
    value = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    
    class Meta:
        unique_together = ['company', 'period', 'metric']
        ordering = ['period', 'company', 'metric__display_order']
    
    def __str__(self):
        return f"{self.company.name} - {self.period} - {self.metric.metric_name}: {self.value}"


class CFDashboardBudget(models.Model):
    """
    Stores consolidated budget/forecast for CF Dashboard.
    One value per metric per period (not per company).
    """
    metric = models.ForeignKey(CFDashboardMetric, on_delete=models.CASCADE)
    period = models.DateField()
    value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    data_type = models.CharField(
        max_length=20,
        choices=[('budget', 'Budget'), ('forecast', 'Forecast')],
        default='budget'
    )
    
    class Meta:
        unique_together = ('metric', 'period', 'data_type')
        ordering = ['period', 'metric__display_order']
    
    def __str__(self):
        return f"{self.metric.metric_name} - {self.period.strftime('%b-%y')} - {self.data_type}"


class ActiveState(models.Model):
    state_code = models.CharField(max_length=2, unique=True)  # TX, CA, NY
    state_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deal_count = models.PositiveIntegerField(default=0)
    deal_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['state_name']
        verbose_name = 'Active State'
        verbose_name_plural = 'Active States'

    def __str__(self):
        return f"{self.state_name} ({self.state_code})"


class PLComment(models.Model):
    """Threaded comments for P&L report cells."""

    row_key = models.CharField(max_length=160, db_index=True)
    column_key = models.CharField(max_length=160, db_index=True)
    row_label = models.CharField(max_length=255, blank=True)
    column_label = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pl_comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['row_key', 'column_key']),
        ]

    def __str__(self):
        preview = (self.message[:30] + '...') if len(self.message) > 30 else self.message
        return f"Comment {self.id} on {self.row_key}/{self.column_key}: {preview}"

    @property
    def root(self):
        """Return the top-level comment in the thread."""
        return self.parent.root if self.parent else self


class HubSpotData(models.Model):
    """Stores HubSpot CRM objects that have been synced into the platform."""

    class RecordType(models.TextChoices):
        DEAL = 'deal', 'Deal'
        COMPANY = 'company', 'Company'
        CONTACT = 'contact', 'Contact'

    record_type = models.CharField(max_length=20, choices=RecordType.choices)
    hubspot_id = models.CharField(max_length=128)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('record_type', 'hubspot_id')
        ordering = ['record_type', 'hubspot_id']
        verbose_name = 'HubSpot Data Record'
        verbose_name_plural = 'HubSpot Data Records'

    def __str__(self):
        return f"{self.record_type}:{self.hubspot_id}"


class HubSpotSyncLog(models.Model):
    """Captures the status of HubSpot synchronization runs."""

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILURE = 'failure', 'Failure'
        PARTIAL = 'partial', 'Partial'

    sync_type = models.CharField(max_length=50, help_text='Scope of the sync (deals, contacts, companies, full, etc.)')
    status = models.CharField(max_length=20, choices=Status.choices)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'HubSpot Sync Log'
        verbose_name_plural = 'HubSpot Sync Logs'

    def __str__(self):
        return f"{self.sync_type} [{self.status}] @ {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
