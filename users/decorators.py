from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def admin_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or u.groups.filter(name='admin').exists()),
        login_url='login'
    )(view_func)

def store_manager_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and (u.groups.filter(name='store_manager').exists() or u.is_superuser or u.groups.filter(name='admin').exists()),
        login_url='login'
    )(view_func)

def sales_attendant_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and u.groups.filter(name='sales_attendant').exists(),
        login_url='login'
    )(view_func)