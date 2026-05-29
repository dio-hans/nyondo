from django.urls import path
from . import views

urlpatterns = [

    path('enroll/',views.enroll_customer, name='enroll_customer'),

    path('deposit/<int:customer_id>/', views.record_deposit, name='record_deposit'),

    path('customer/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('receipt/<int:deposit_id>/', views.view_receipt, name='view_receipt'),
    path('schemes_list/', views.schemes_list, name='schemes_list'),
    
    

]