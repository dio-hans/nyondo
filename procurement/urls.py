from django.urls import path
from . import views

urlpatterns = [

    path(
        'record/',
        views.record_purchase,
        name='record_purchase'
    ),

    path(
        'supplier-debts/',
        views.supplier_debt_list,
        name='supplier_debt_list'
    ),

]