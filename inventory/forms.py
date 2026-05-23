from django import forms
from .models import Product


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            'category',
            'name',
            'description',
            'unit_of_measure',
            'cost_price',
            'selling_price',
            'current_stock',
            'reorder_level'
        ]

        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3
            })
        }