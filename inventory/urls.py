from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & General Stock Lists
    path('dashboard/', views.inventory_dashboard, name='inventory_dashboard'),
    path('', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),

    # 🚀 The New Unified Simple Create & Edit Route
    # Both points use the same 'product_save' view function safely!
    path('products/add/', views.product_save, name='product_add'),
    path('products/<int:product_id>/edit/', views.product_save, name='product_edit'),

    # Advanced Procurement Restocking Workflow 
    path('products/create/', views.product_create, name='product_create'),
]