from django.urls import path
from . import views

urlpatterns = [
    path('dashboard', views.business_dashboard, name='dashboard'),
    path('financial-statement/', views.financial_statement_view, name='financial_statement'),
    path('supplier-credit/', views.business_dashboard, name='unpaid_supplier'),
    path('cashier-performance/', views.business_dashboard, name='cashier_performance'),
    path('stock-history/', views.business_dashboard, name='stock_history'),
    path('highest-profit/', views.business_dashboard, name='highest_profit'),
    path('least-selling/', views.business_dashboard, name='least_selling'),
    path('transport-revenue/', views.business_dashboard, name='transport_revenue'),
]