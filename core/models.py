from django.db import models

# Create your models here.

class Company(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        verbose_name_plural = "Companies"

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class FinancialData(models.Model):
    DATA_TYPES = [
        ('actual', 'Actual'),
        ('budget', 'Budget'),
        ('forecast', 'Forecast'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='financial_data')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='financial_data')
    period = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    
    def __str__(self):
        return f"{self.company.code} - {self.account.code} - {self.period} - {self.amount}"
    
    class Meta:
        verbose_name_plural = "Financial Data"
        unique_together = ['company', 'account', 'period', 'data_type']

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
