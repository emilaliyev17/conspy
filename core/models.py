from django.db import models
import calendar
from django.contrib.auth.models import User

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
