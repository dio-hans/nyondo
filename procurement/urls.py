# Inside procurement/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Overview (The main landing page for procurement)
    path('dashboard/', views.procurement_dashboard, name='procurement_dashboard'),
    path('record/', views.record_purchase, name='record_purchase'),
    path('supplier-debts/', views.supplier_debt_list, name='supplier_debt_list'),
    path('receive-credit-stock/', views.receive_credit_stock, name='receive_credit_stock'),
]