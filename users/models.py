from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Accounts/admin'
        SALES_ATTENDANT = 'SALES', 'Sales Attendant'
        STORE_MANAGER = 'MANAGER', 'Store Manager'
        CASHIER = 'CASHIER', 'Cashier'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.SALES_ATTENDANT
    )
    contact = models.CharField(max_length=15)
    employee_id = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"