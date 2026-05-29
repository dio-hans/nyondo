from django import forms
from .models import PurchaseOrder, Supplier
from inventory.models import Product

class UnifiedPurchaseForm(forms.Form):
    # Core Inventory Details
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'w-full p-2.5 border rounded-lg'})
    )
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'w-full p-2.5 border rounded-lg'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'w-full p-2.5 border rounded-lg', 'id': 'id_quantity'})
    )
    unit_cost = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'w-full p-2.5 border rounded-lg', 'id': 'id_unit_cost'})
    )
    invoice_number = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'w-full p-2.5 border rounded-lg', 'placeholder': 'INV-XXXX'})
    )
    
    # Financial Transaction Details
    PAYMENT_TYPE_CHOICES = [
        ('CASH', 'Standard Immediate Cash'),
        ('CREDIT', 'Supplier Credit Scheme (Wholesale Debt)')
    ]
    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'w-full p-2.5 border rounded-lg', 'id': 'id_payment_type'})
    )
    
    # Credit Conditions Fields (Default Hidden via UI toggles)
    amount_paid = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False, initial=0,
        widget=forms.NumberInput(attrs={'class': 'w-full p-2.5 border rounded-lg', 'id': 'id_amount_paid'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'w-full p-2.5 border rounded-lg', 'rows': 2})
    )