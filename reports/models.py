from django.conf import settings
from django.db import models

# Create your models here.
class Expense(models.Model):
    EXPENSE_CATEGORIES = [
        ('RENT', 'Rent & Utilities'),
        ('SALARY', 'Staff Salaries & Wages'),
        ('LOGISTICS', 'Fuel & Vehicle Maintenance'),
        ('MAINTENANCE', 'Store Maintenance & Repairs'),
        ('MARKETING', 'Marketing & Branding'),
        ('TAX', 'Taxes & Licensing'),
        ('MISC', 'Miscellaneous / Sundry'),
    ]
    
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date_incurred = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
    settings.AUTH_USER_MODEL, 
    on_delete=models.SET_NULL, 
    null=True
)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.amount} ({self.date_incurred})"