from django.db import models
from django.conf import settings 
from inventory.models import Product
from sales.models import Customer

class SavingsScheme(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    nin = models.CharField(max_length=14, unique=True)
    phone_number = models.CharField(max_length=15)
    deposit = models.IntegerField(default=0)
    total_amount_target = models.IntegerField()
    current_balance = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    # 🆕 DEEP PROFILING OPERATIONAL FIELDS (Safe for Migrations)
    address = models.TextField(blank=True, null=True)
    employer_tag = models.CharField(max_length=200, blank=True, null=True)
    next_of_kin_name = models.CharField(max_length=100, blank=True, null=True)
    next_of_kin_phone = models.CharField(max_length=15, blank=True, null=True)
    next_of_kin_relationship = models.CharField(max_length=50, blank=True, null=True)
    frequency_commitment = models.CharField(max_length=20, default='MONTHLY')
    is_price_locked = models.BooleanField(default=False)

    # Cleaned up recorded_by relation (No duplicates)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
    )

    class PaymentMethod(models.TextChoices):
        AIRTEL = 'AIRTEL', 'Airtel Money'
        MTN = 'MTN', 'MTN MoMo'
        CASH = 'CASH', 'Cash'
        VISA = 'VISA', 'Visa'
        MASTERCARD = 'MASTERCARD', 'Mastercard'

    def __str__(self):
        return f"{self.customer.name} - Scheme Ledger"


class SchemeProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    eligible = models.BooleanField(default=True)

    def __str__(self):
        return self.product.name


class SchemeDeposit(models.Model):
    scheme = models.ForeignKey(SavingsScheme, on_delete=models.CASCADE)
    amount = models.IntegerField()
    deposited_at = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    material_allocation = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return self.receipt_number


class SchemeWithdrawal(models.Model):
    scheme = models.ForeignKey(SavingsScheme, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    picked_at = models.DateTimeField(auto_now_add=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.scheme.customer.name} Pickup"