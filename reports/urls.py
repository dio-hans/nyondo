from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.business_dashboard, name='business_dashboard'),
    path('financials/', views.financial_statement_view, name='financial_statement'),

]
    
