from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# 1. MANAGEMENT (Authentication)

@login_required
def user_login(request):
    if request.method =='POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect()

        else:
            form=UserCreationForm()    

    return render(request, 'users/login.html', {'form':form})


@login_required
def user_logout(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('user_login')


# 2. STAFF PROFILING (Role Actions)
# Helper check to restrict access to Admins or Store Managers
def can_manage_staff(user):
    return user.role in [User.Role.ADMIN, User.Role.STORE_MANAGER] or user.is_superuser


@login_required
@user_passes_test(can_manage_staff, login_url='business_dashboard', redirect_field_name=None)
def user_list(request):
    """Displays all employees working in the system"""
    staff_members = User.objects.all().order_by('role')
    return render(request, 'users/user_list.html', {'system_users': staff_members})


@login_required
@user_passes_test(can_manage_staff, login_url='business_dashboard', redirect_field_name=None)
def register_user(request):
    """Allows Admin/Managers to create authenticated profiles for new employees"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        contact = request.POST.get('contact', '').strip()
        emp_id = request.POST.get('employee_id', '').strip()
        selected_role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register_user')

        try:
            # Create core instance of custom user
            new_staff = User.objects.create_user(
                username=username,
                password=password,
                contact=contact,
                employee_id=emp_id,
                role=selected_role
            )
            
            # Explicitly set administrative flags if given high clearance roles
            if selected_role in [User.Role.ADMIN, User.Role.STORE_MANAGER]:
                new_staff.is_staff = True
                
            new_staff.save()

            messages.success(request, f"Staff record for {username} registered successfully.")
            return redirect('user_list')
        except Exception as e:
            messages.error(request, f"Failed to register employee: {e}")

    return render(request, 'users/register.html', {'roles': User.Role.choices})


@login_required
@user_passes_test(can_manage_staff, login_url='business_dashboard', redirect_field_name=None)
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