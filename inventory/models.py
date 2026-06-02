from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings



class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    class Meta:

        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    name = models.CharField(
        max_length=150
    )

    sku = models.CharField(
        max_length=50,
        unique=True
    )

    description = models.TextField(
        blank=True
    )


    class Unit(models.TextChoices):

        PIECE = 'PCS', 'Pieces'

        BAG = 'BAG', 'Bag (cement)'

        KILO = 'KGS', 'Kilogram'

        PACK = 'PKT', '5KG Packet (Nails)'


    unit_of_measure = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.PIECE
)
        
    

    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    current_stock = models.PositiveIntegerField(
        default=0
    )

    reorder_level = models.PositiveIntegerField(
        default=10
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    average_daily_sales = models.PositiveIntegerField(
    default=1
)
    
    def days_until_stockout(self):
        """
        Dynamically calculates remaining stock runway by dividing current count
        by the average historical daily consumption sales pace.
        """
        # If daily sales pace is 0, return None to avoid a ZeroDivisionError crash
        if self.average_daily_sales and self.average_daily_sales > 0:
            return int(self.current_stock / self.average_daily_sales)
        return None

    def clean(self):
        if self.selling_price is not None and self.cost_price is not None:
            if self.selling_price <= self.cost_price:
                raise ValidationError("Selling price must be strictly greater than the cost price.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



class Location(models.Model):

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.name


class StockMovement(models.Model):

    TRANSACTION_TYPES = [

        ('IN', 'Stock In'),

        ('OUT', 'Stock Out'),

        ('ADJUSTMENT', 'Adjustment'),

        ('DAMAGED', 'Damaged'),

        ('RETURNED', 'Returned')

    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    quantity = models.PositiveIntegerField()

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.product.name} -{self.transaction_type}"
    
class AuditLog(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    action = models.CharField(
        max_length=255
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.action