from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q

from sales.models import Customer
from inventory.models import Product
from .models import SavingsScheme, SchemeDeposit


# ROLE PROTECTION HELPER FUNCTIONS

def is_sales_or_higher(user):
    """Allows Sales Attendants, Store Managers, and Admins to run ledger actions."""
    return user.is_authenticated and (user.role in ['SALES', 'MANAGER', 'ADMIN'] or user.is_superuser)


# CORE SAVINGS SCHEME LOGIC

@login_required
@user_passes_test(is_sales_or_higher, login_url='product_list', redirect_field_name=None)
def enroll_customer(request):
    if request.method == 'POST':
        customer_name_input = request.POST.get('customer_name', '').strip()
        nin = request.POST.get('nin', '').strip().upper()
        phone = request.POST.get('phone', '').strip()
        target = request.POST.get('target_amount', 0)
        initial_deposit = request.POST.get('initial_deposit', 0) or 0
        employer = request.POST.get('employer', '').strip()
        home_address = request.POST.get('home_address', '').strip()
        nok_name = request.POST.get('nok_name', '').strip()
        nok_phone = request.POST.get('nok_phone', '').strip()
        nok_relationship = request.POST.get('nok_relationship', '').strip()
        deposit_frequency = request.POST.get('deposit_frequency', 'MONTHLY')
        price_lock_secured = request.POST.get('price_lock_secured') == 'on'

        # Core Field Validation Checkpoint
        if not (customer_name_input and nin and phone and nok_name and nok_phone):
            messages.error(request, "Customer name, NIN, phone, and Next of Kin metrics are strictly required.")
            return redirect('enroll_customer')

        # Phone Length Protection Rule (Ugandan Telecom Formats)
        if not (phone.startswith('07') and len(phone) == 10 and phone.isdigit()):
            messages.error(request, "Enter a valid Ugandan phone number (07xxxxxxxx).")
            return redirect('enroll_customer')

        if len(nin) != 14:
            messages.error(request, "NIN validation failed: Must contain exactly 14 characters.")
            return redirect('enroll_customer')

        if SavingsScheme.objects.filter(nin=nin).exists():
            messages.error(request, "A savings ledger account with this NIN already exists.")
            return redirect('enroll_customer')

        try:
            # DYNAMIC CUSTOMER ENGINE: Get or create base profile
            customer_obj, created = Customer.objects.get_or_create(
                name=customer_name_input,
                defaults={'phone': phone} 
            )
            
            staff_user = request.user if request.user.is_authenticated else None

            # Establish the Savings Scheme linked safely to this customer object
            scheme = SavingsScheme.objects.create(
                customer=customer_obj,
                nin=nin,
                phone_number=phone,
                deposit=int(initial_deposit),
                total_amount_target=int(target),
                current_balance=int(initial_deposit),
                address=home_address,
                employer_tag=employer,
                next_of_kin_name=nok_name,
                next_of_kin_phone=nok_phone,
                next_of_kin_relationship=nok_relationship,
                frequency_commitment=deposit_frequency,
                is_price_locked=price_lock_secured,
                recorded_by=staff_user  
            )

            # Record initial deposit ledger transaction line if capital dropped immediately
            if int(initial_deposit) > 0:
                SchemeDeposit.objects.create(
                    scheme=scheme,
                    amount=int(initial_deposit),
                    receipt_number=f"REC-INIT-{scheme.id}-{int(timezone.now().timestamp())}"
                )

            messages.success(request, f"Savings account ledger for {customer_obj.name} deployed successfully.")
            return redirect('schemes_list')

        except Exception as e:
            messages.error(request, f"Error processing ledger registration: {e}")
            return redirect('enroll_customer')

    all_base_customers = Customer.objects.all()
    return render(request, 'schemes/enroll_member.html', {'customers': all_base_customers})


@login_required
@user_passes_test(is_sales_or_higher, login_url='product_list', redirect_field_name=None)
def record_deposit(request, customer_id=None):
    scheme = None
    if customer_id:
        scheme = get_object_or_404(SavingsScheme, id=customer_id)

    if request.method == 'POST':
        customer_name_input = request.POST.get('customer_name', '').strip()
        material_id = request.POST.get('material_allocation') 
        allocated_product = get_object_or_404(Product, id=material_id) if material_id else None
        
        try:
            amount = int(request.POST.get('amount') or 0)
        except ValueError:
            amount = 0

        if amount <= 0:
            messages.error(request, "Deposit amount must be greater than zero.")
            if scheme:
                return redirect('record_deposit', customer_id=scheme.id)
            return redirect('record_deposit_blank')

        if not scheme and customer_name_input:
            scheme = SavingsScheme.objects.filter(customer__name__iexact=customer_name_input).first()
            if not scheme:
                messages.error(request, f"No active savings scheme ledger found matching '{customer_name_input}'. Please enroll them first.")
                return redirect(request.path_info)

        deposit = SchemeDeposit.objects.create(
            scheme=scheme,
            amount=amount,
            material_allocation=allocated_product,
            receipt_number=f"DEP-{scheme.id}-{int(timezone.now().timestamp())}"
        )

        scheme.current_balance += amount
        scheme.save()

        messages.success(request, f"UGX {amount:,} safely banked. Generating temporary invoice...")
        return redirect('view_receipt', deposit_id=deposit.id)

    all_active_schemes = SavingsScheme.objects.all().select_related('customer')
    hardware_materials = Product.objects.filter(
        Q(name__icontains='Cement') | 
        Q(name__icontains='Iron Sheet') | 
        Q(name__icontains='Iron Bar')
    )
    
    context = {
        'scheme': scheme,
        'active_schemes': all_active_schemes,
        'hardware_materials': hardware_materials
    }
    return render(request, 'schemes/make_deposit.html', context)


@login_required
def view_receipt(request, deposit_id):
    deposit = get_object_or_404(SchemeDeposit, id=deposit_id)
    scheme = deposit.scheme
    previous_balance = scheme.current_balance - deposit.amount
    
    context = {
        'deposit': deposit,
        'scheme': scheme,
        'customer': scheme.customer,
        'previous_balance': previous_balance
    }
    return render(request, 'schemes/member_receipt.html', context)


@login_required
def customer_detail(request, customer_id):
    scheme = get_object_or_404(SavingsScheme, id=customer_id)
    deposits = SchemeDeposit.objects.filter(scheme=scheme).order_by('-deposited_at')
    
    context = {
        'scheme': scheme,
        'deposits': deposits,
        'total_balance': scheme.current_balance
    }
    return render(request, 'schemes/customer_detail.html', context)


@login_required
def schemes_list(request):
    active_schemes = SavingsScheme.objects.all().select_related('customer')
    return render(request, 'schemes/schemes_list.html', {'schemes': active_schemes})