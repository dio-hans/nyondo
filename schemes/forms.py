from django import forms
from .models import SchemeDeposit


class RecordDepositForm(forms.ModelForm):
    class Meta:
        model = SchemeDeposit
        fields = [
            
        ]