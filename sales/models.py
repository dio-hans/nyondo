from django.db import models

from inventory.models import Product

from django.conf import settings  # Always use this to reference custom users


# =========================================
# CUSTOMER MODEL
# =========================================

class Customer(models.Model):

    CUSTOMER_TYPES = [

        ('INDIVIDUAL', 'Individual'),

        ('RETAILER', 'Retailer'),

        ('WHOLESALER', 'Wholesaler'),

    ]

    name = models.CharField(
        max_length=50
    )

    phone = models.CharField(
        max_length=15
    )

    email = models.EmailField(
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPES,
        default='INDIVIDUAL'
    )

    def __str__(self):

        return self.name


# =========================================
# SALES ORDER
# =========================================

class SalesOrder(models.Model):

    PAYMENT_METHODS = [

        ('CASH', 'Cash'),

        ('MOBILE', 'Mobile Money'),

        ('BANK', 'Bank Transfer')

    ]

    STATUS_CHOICES = [

        ('PENDING', 'Pending'),

        ('COMPLETED', 'Completed'),

        ('CANCELLED', 'Cancelled'),

    ]

    customer = models.ForeignKey(

        Customer,

        on_delete=models.CASCADE

    )

    payment_method = models.CharField(

        max_length=20,

        choices=PAYMENT_METHODS,

        default='CASH'

    )

    order_date = models.DateTimeField(

        auto_now_add=True

    )

    status = models.CharField(

        max_length=20,

        choices=STATUS_CHOICES,

        default='PENDING'

    )

    subtotal = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0

    )

    tax_amount = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0

    )

    transport_fee = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0

    )

    total_amount = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0

    )

    served_by = models.ForeignKey(

         settings.AUTH_USER_MODEL, 

        on_delete=models.SET_NULL,

        null=True

    )

    def __str__(self):

        return f"SO-{self.id}"


# =========================================
# SALES ORDER ITEMS
# =========================================

class SalesOrderItem(models.Model):

    sales_order = models.ForeignKey(

        SalesOrder,

        on_delete=models.CASCADE,

        related_name='items'

    )

    product = models.ForeignKey(

        Product,

        on_delete=models.CASCADE

    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(

        max_digits=10,

        decimal_places=2

    )

    subtotal = models.DecimalField(

        max_digits=12,

        decimal_places=2

    )

    def __str__(self):

        return self.product.name


# =========================================
# RECEIPT MODEL
# =========================================

class Receipt(models.Model):

    sales_order = models.OneToOneField(

        SalesOrder,

        on_delete=models.CASCADE

    )

    receipt_number = models.CharField(

        max_length=50,

        unique=True

    )

    issued_at = models.DateTimeField(

        auto_now_add=True

    )

    recorded_by = models.ForeignKey(

         settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE

    )

    def __str__(self):

        return self.receipt_number