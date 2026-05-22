from django.contrib import admin

# Register your models here.

from .models import (
    SavingsScheme,
    SchemeProduct,
    SchemeDeposit,
    SchemeWithdrawal
)

admin.site.register(SavingsScheme)
admin.site.register(SchemeProduct)
admin.site.register(SchemeDeposit)
admin.site.register(SchemeWithdrawal)