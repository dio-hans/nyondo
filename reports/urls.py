from django.urls import path
from . import views

urlpatterns = [
    path('business_dashboard/', views.business_dashboard, name='admin_dashboard'),
    path('financial-statement/', views.financial_statement_view, name='financial_statement'),
    path('supplier-credit/', views.unpaid_supplier_view, name='unpaid_supplier'),
    path('cashier-performance/', views.cashier_performance_view, name='cashier_performance'),
    path('stock-history/', views.stock_history_view, name='stock_history'),
    path('highest-profit/', views.highest_profit_view, name='highest_profit'),
    path('least-selling/', views.least_selling_view, name='least_selling'),
    path('transport-revenue/', views.transport_revenue_view, name='transport_revenue'),
    path('reports_index/', views.reports_index_view, name='reports_index'),

]
    
