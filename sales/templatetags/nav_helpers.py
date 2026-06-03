from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag
def get_dashboard_url(user):
    if user.role == 'MANAGER':
        return reverse('inventory_dashboard') # Uses the name from urls.py
    else:
        return reverse('record_sale')