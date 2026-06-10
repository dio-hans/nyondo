from django import forms
from .models import Product, Category
from procurement.models import Supplier

class ProductForm(forms.ModelForm):
    # These fields collect form input data without saving directly to the Product table
    cat_id = forms.ModelChoiceField(
        queryset=Category.objects.all(), 
        required=False, 
        label="Category Dropdown")
    
    quantity_arriving = forms.IntegerField(
        min_value=1, 
        required=True, 
        label="Quantity Arriving")
    
    is_credit = forms.BooleanField(
        required=False, 
        initial=False, 
        label="Is this a Credit Purchase?")
    
    supplier_id = forms.ModelChoiceField(
        queryset=Supplier.objects.all(), 
        required=False, 
        label="Supplier")
    
    invoice_no = forms.CharField(
        required=False, 
        max_length=50, 
        label="Invoice Number")
    
    amount_paid = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False, 
        initial=0.0, 
        label="Amount Paid Upfront")
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}), 
        required=False, 
        label="Transaction Notes")


    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'unit_of_measure',
            'cost_price',
            'selling_price',
            'reorder_level',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3})
        }