from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from .forms import UserRegistrationForm, UserLoginForm
from .models import User

# 1. MANAGEMENT (Authentication)
def redirect_user_by_role(user):
    """Sends the user straight to their specific operational layout"""
    if user.role == User.Role.ADMIN:
        return redirect('admin_dashboard')
    elif user.role == User.Role.STORE_MANAGER:
        return redirect('inventory_dashboard')
    else:
        return redirect('sales_dashboard')


def user_login(request):
    # Check 1: If they bounce here but are already logged in, send them away
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if not user.is_active:
                    messages.error(request, "Your account has been suspended.")
                    return redirect('login')

                # Log them into the session backend
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}")

                # Check 2: Send them directly to their screen right now!
                return redirect_user_by_role(user)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('user_login')


# 2. STAFF PROFILING (Role Actions)
def can_manage_staff(user):
    return user.role in [User.Role.ADMIN, User.Role.STORE_MANAGER] or user.is_superuser


@user_passes_test(can_manage_staff, login_url='user_login', redirect_field_name=None)
def user_list(request):
    """Displays all employees working in the system"""
    staff_members = User.objects.all().order_by('role')
    return render(request, 'users/user_list.html', {'system_users': staff_members})


def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
                  
            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'users/register.html', {'form': form})

@user_passes_test(can_manage_staff, login_url='user_login', redirect_field_name=None)
def toggle_user_status(request, user_id):
    """Soft deactivation feature to handle account locks safely"""
    employee = get_object_or_404(User, id=user_id)
    
    if employee == request.user:
        messages.error(request, "Security protection: You cannot lock out your own account.")
        return redirect('user_list')

    employee.is_active = not employee.is_active
    employee.save()

    status = "activated" if employee.is_active else "suspended"
    messages.success(request, f"Account access for {employee.username} has been {status}.")
    return redirect('user_list')


