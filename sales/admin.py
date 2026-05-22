from django.contrib import admin

# Register your models here.

from .models import (
    Customer,
    SalesOrder,
    SalesOrderItem,
    Receipt
)

admin.site.register(Customer)
admin.site.register(SalesOrder)
admin.site.register(SalesOrderItem)
admin.site.register(Receipt)