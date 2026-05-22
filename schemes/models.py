from django.db import models
from django.conf import settings  # Import settings instead of django.contrib.auth
from inventory.models import Product
from sales.models import Customer

class SavingsScheme(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    nin = models.CharField(max_length=14, unique=True)
    phone_number = models.CharField(max_length=15)
    deposit = models.IntegerField()
       # FIX THIS LINE: Change User to settings.AUTH_USER_MODEL
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )

    class PaymentMethod(models.TextChoices):
        AIRTEL = 'AIRTEL', 'Airtel Money'
        MTN = 'MTN', 'MTN MoMo'
        CASH = 'CASH', 'Cash'
        VISA = 'VISA', 'Visa'
        MASTERCARD = 'MASTERCARD', 'Mastercard'

    registered_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_amount_target = models.IntegerField()
    current_balance = models.IntegerField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.customer.name

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