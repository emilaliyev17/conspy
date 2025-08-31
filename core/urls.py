from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('chart-of-accounts/', views.chart_of_accounts_view, name='chart_of_accounts'),
    path('chart-of-accounts/download/', views.download_chart_of_accounts, name='download_chart_of_accounts'),
    path('upload/chart-of-accounts/', views.upload_chart_of_accounts, name='upload_chart_of_accounts'),
    path('upload/financial-data/', views.upload_financial_data, name='upload_financial_data'),
    path('download/template/', views.download_template, name='download_template'),
    path('download/financial-data-template/', views.download_financial_data_template, name='download_financial_data_template'),
    path('reports/pl/', views.pl_report, name='pl_report'),
    path('reports/bs/', views.bs_report, name='bs_report'),
    path('reports/export/', views.export_report_excel, name='export_report_excel'),
]
