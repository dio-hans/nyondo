from django.contrib import admin

from .models import (
    Category,
    Product,
    Location,
    StockMovement
)

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Location)
admin.site.register(StockMovement)
