from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import UserRegistrationForm, UserLoginForm
from .models import User
from reports.decorators import role_required


def redirect_user_by_role(user):
    """
    Explicit traffic controller based on user roles.
    Returns the redirect response to their specific dashboard landing gate.
    """
    if user.role == 'ADMIN':
        return redirect('admin_dashboard')
    elif user.role == 'MANAGER':
        return redirect('inventory_dashboard')
    elif user.role == 'SALES':
        return redirect('record_sale')
    elif user.role == 'CASHIER':
        return redirect('order_queue')
    else:
        # Fallback security route if role attributes are corrupted
        return redirect('login')


def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if not user.is_active:
                    messages.error(request, "Access Denied: Your account has been suspended.")
                    return redirect('login')

                # Log the authenticated session into the backend state
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                
                return redirect_user_by_role(user)
        else:
            messages.error(request, "Invalid username or password configuration.")
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, "Session terminated successfully.")
    return redirect('login')


# Staff Profiling and Administrative Actions

@login_required
@role_required(['ADMIN'])
def register_user(request):
    """
    Unified User Control Gateway: Manages real-time 
    staff account listing alongside provisioning forms.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f"Terminal credentials generated successfully for {new_user.username}!")
            return redirect('register_user') # Keeps Admin on page to view updated table
        else:
            messages.error(request, "Account registration failed. Verify database constraints.")
    else:
        form = UserRegistrationForm()

    # Query active system users to populate the integrated dashboard table
    system_users = User.objects.all().order_by('role', 'username')
    
    return render(request, 'users/user_control.html', {
        'form': form,
        'users': system_users
    })


@login_required
@role_required(['ADMIN'])
def toggle_user_status(request, user_id):
    """
    Soft deactivation feature to handle account locks safely.
    Protected explicitly against arbitrary privilege escalations.
    """
    employee = get_object_or_404(User, id=user_id)
    
    if employee == request.user:
        messages.error(request, "Security Violation Protection: You cannot lock out your own administrative account.")
        return redirect('register_user')

    # Atomic inversion of status state
    employee.is_active = not employee.is_active
    employee.save()

    status = "activated" if employee.is_active else "suspended"
    
    if employee.is_active:
        messages.success(request, f"Access clearance for {employee.username} successfully restored.")
    else:
        messages.warning(request, f"Terminal operational rights for {employee.username} have been suspended.")
        
    return redirect('register_user')