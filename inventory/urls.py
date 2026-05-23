from django.urls import path
from . import views

urlpatterns = [

    path('products/', views.product_list, name='product_list'),

    path('products/create/', views.product_create, name='product_create'),

    path('products/<int:product_id>/', views.product_detail, name='product_detail'
    ),

    path('dashboard/', views.inventory_dashboard, name='inventory_dashboard'),

]