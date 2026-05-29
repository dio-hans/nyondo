from django.db import models
from inventory.models import Product
from django.utils import timezone

# code goes here
class Supplier(models.Model):

    name = models.CharField(
        max_length=150
    )

    phone_number = models.CharField(
        max_length=20
    )

    email = models.EmailField(
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    contact_person = models.CharField(
        max_length=100,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):

    PAYMENT_STATUS = [
    
        ('PAID', 'Paid'),

        ('PARTIAL', 'Partial'),

        ('PENDING', 'pending')

    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE
    )

    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='PENDING'
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)
    

    def __str__(self):

        return self.invoice_number


class PurchaseItem(models.Model):

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    

    

    def __str__(self):

        return self.product.name


class SupplierPayment(models.Model):

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_date = models.DateTimeField(
        auto_now_add=True
    )

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.supplier.name} Payment"