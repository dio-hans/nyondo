from django.urls import path
from . import views

urlpatterns = [
    # This points the root of sales/ to your history table page
    path('', views.sale_history, name='sales_list'),
    
    # This points sales/record/ to your sale checkout form
    path('record/', views.make_sale, name='record_sale'),
]