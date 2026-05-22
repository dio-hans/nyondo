from django.contrib import admin

# code goes here
from .models import (
    Supplier,
    PurchaseOrder,
    PurchaseItem
)
admin.site.register(Supplier)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseItem)

