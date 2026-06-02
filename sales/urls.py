from django.urls import path
from . import views

urlpatterns = [
    # This points the root of sales/ to your history table page
    path('sales_list', views.sale_history, name='sales_list'),
    
    # This points sales/record/ to your sale checkout form
    path('record/', views.make_sale, name='record_sale'),
    path('review_checkout', views.review_checkout, name='review_checkout'),
    # In sales/urls.py
    path('order_queue', views.order_queue_dashboard, name='order_queue'),
    path('queue/clear/<int:order_id>/', views.process_queue_clearance, name='process_queue_clearance'),
    path('queue/checkout/<int:order_id>/', views.checkout_collection_detail, name='checkout_collection_detail'),
    path('clear_order', views.review_checkout, name='review_checkout'),
    path('invoice/<int:order_id>/', views.invoice_detail_receipt, name='invoice_detail'),
    
]
