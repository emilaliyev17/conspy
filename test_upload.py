#!/usr/bin/env python3
"""
Simple test script for Chart of Accounts and Financial Data upload functionality.
Run this after setting up the database and running migrations.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financial_consolidator.settings')
django.setup()

from django.test import RequestFactory
from core.views import download_template, upload_chart_of_accounts, download_financial_data_template, upload_financial_data
from core.models import ChartOfAccounts, Company, Account, FinancialData

def test_download_template():
    """Test the Chart of Accounts template download functionality."""
    print("Testing Chart of Accounts template download...")
    
    rf = RequestFactory()
    request = rf.get('/download/template/')
    response = download_template(request)
    
    if response.status_code == 200:
        print("✓ Chart of Accounts template download works correctly")
        print(f"  Content-Type: {response['Content-Type']}")
        print(f"  Content-Disposition: {response['Content-Disposition']}")
        return True
    else:
        print(f"✗ Chart of Accounts template download failed with status code: {response.status_code}")
        return False

def test_download_financial_data_template():
    """Test the Financial Data template download functionality."""
    print("\nTesting Financial Data template download...")
    
    rf = RequestFactory()
    request = rf.get('/download/financial-data-template/')
    response = download_financial_data_template(request)
    
    if response.status_code == 200:
        print("✓ Financial Data template download works correctly")
        print(f"  Content-Type: {response['Content-Type']}")
        print(f"  Content-Disposition: {response['Content-Disposition']}")
        return True
    else:
        print(f"✗ Financial Data template download failed with status code: {response.status_code}")
        return False

def test_upload_chart_of_accounts_view():
    """Test the Chart of Accounts upload view renders correctly."""
    print("\nTesting Chart of Accounts upload view...")
    
    rf = RequestFactory()
    request = rf.get('/upload/chart-of-accounts/')
    response = upload_chart_of_accounts(request)
    
    if response.status_code == 200:
        print("✓ Chart of Accounts upload view renders correctly")
        return True
    else:
        print(f"✗ Chart of Accounts upload view failed with status code: {response.status_code}")
        return False

def test_upload_financial_data_view():
    """Test the Financial Data upload view renders correctly."""
    print("\nTesting Financial Data upload view...")
    
    rf = RequestFactory()
    request = rf.get('/upload/financial-data/')
    response = upload_financial_data(request)
    
    if response.status_code == 200:
        print("✓ Financial Data upload view renders correctly")
        return True
    else:
        print(f"✗ Financial Data upload view failed with status code: {response.status_code}")
        return False

def test_chart_of_accounts_model_creation():
    """Test creating a ChartOfAccounts record."""
    print("\nTesting ChartOfAccounts model creation...")
    
    try:
        # Create a test record
        account = ChartOfAccounts.objects.create(
            account_code='TEST001',
            account_name='Test Account',
            account_type='ASSET',
            parent_category='TEST_CATEGORY',
            sub_category='',
            formula='',
            sort_order=1,
            is_header=False
        )
        print(f"✓ Created test Chart of Accounts: {account}")
        
        # Clean up
        account.delete()
        print("✓ Test Chart of Accounts deleted successfully")
        return True
    except Exception as e:
        print(f"✗ ChartOfAccounts model creation failed: {e}")
        return False

def test_financial_data_model_creation():
    """Test creating a FinancialData record."""
    print("\nTesting FinancialData model creation...")
    
    try:
        # Get or create test company and account
        company, _ = Company.objects.get_or_create(
            code='TEST_COMP',
            defaults={'name': 'Test Company for Financial Data'}
        )
        
        account, _ = Account.objects.get_or_create(
            code='TEST_ACC',
            defaults={'name': 'Test Account for Financial Data', 'type': 'asset'}
        )
        
        # Create a test financial data record
        from datetime import date
        financial_data = FinancialData.objects.create(
            company=company,
            account=account,
            period=date(2024, 1, 1),
            amount=1000.00,
            data_type='actual'
        )
        print(f"✓ Created test Financial Data: {financial_data}")
        
        # Clean up
        financial_data.delete()
        print("✓ Test Financial Data deleted successfully")
        return True
    except Exception as e:
        print(f"✗ FinancialData model creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Chart of Accounts & Financial Data Upload Functionality Tests")
    print("=" * 60)
    
    tests = [
        test_download_template,
        test_download_financial_data_template,
        test_upload_chart_of_accounts_view,
        test_upload_financial_data_view,
        test_chart_of_accounts_model_creation,
        test_financial_data_model_creation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The upload functionality is working correctly.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
