from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from sales.models import Customer
from .models import SavingsScheme, SchemeDeposit

# 1. CUSTOMER ENROLLMENT TO SAVINGS SCHEME
def enroll_customer(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        nin = request.POST.get('nin', '').strip().upper()
        phone = request.POST.get('phone', '').strip()
        target = request.POST.get('target_amount', 0)
        initial_deposit = request.POST.get('initial_deposit', 0)

        if not (customer_id and nin and phone):
            messages.error(request, "All core profiling fields are required.")
            return redirect('enroll_customer')

        # Ugandan Phone Code Validation
        if not (phone.startswith('07') and len(phone) == 10 and phone.isdigit()):
            messages.error(request, "Enter a valid Ugandan phone number (07xxxxxxxx).")
            return redirect('enroll_customer')

        if len(nin) != 14:
            messages.error(request, "NIN must contain exactly 14 characters.")
            return redirect('enroll_customer')

        if SavingsScheme.objects.filter(nin=nin).exists():
            messages.error(request, "A savings account with this NIN already exists.")
            return redirect('enroll_customer')

        try:
            customer_obj = Customer.objects.get(id=customer_id)
            
            # Save account using your structural fields
            scheme = SavingsScheme.objects.create(
                customer=customer_obj,
                nin=nin,
                phone_number=phone,
                deposit=int(initial_deposit),
                total_amount_target=int(target),
                current_balance=int(initial_deposit),
                recorded_by=request.user
            )

            # Record initial deposit transaction if present
            if int(initial_deposit) > 0:
                SchemeDeposit.objects.create(
                    scheme=scheme,
                    amount=int(initial_deposit),
                    receipt_number=f"REC-INIT-{scheme.id}"
                )

            messages.success(request, f"Savings ledger for {customer_obj.name} created successfully.")
            return redirect('schemes_list')

        except Exception as e:
            messages.error(request, f"Error enrolling account ledger: {e}")
            return redirect('enroll_customer')

    # Query all standard base store profiles to populate enrollment form
    all_base_customers = Customer.objects.all()
    return render(request, 'schemes/enroll_member.html', {'customers': all_base_customers})


# 2. RECORD CUSTOMER DEPOSIT AGAINST SCHEME
def record_deposit(request, customer_id):
    # Lookup the unique savings profile
    scheme = get_object_or_404(SavingsScheme, id=customer_id)

    if request.method == 'POST':
        try:
            amount = int(request.POST.get('amount') or 0)
        except ValueError:
            amount = 0

        if amount <= 0:
            messages.error(request, "Deposit amount must be greater than zero.")
            return redirect('record_deposit', customer_id=scheme.id)

        # Create explicit ledger deposit entry
        deposit = SchemeDeposit.objects.create(
            scheme=scheme,
            amount=amount,
            receipt_number=f"DEP-{scheme.id}-{timezone.now().strftime('%s')}"
        )

        # Increment balance calculation property
        scheme.current_balance += amount
        scheme.save()

        messages.success(request, f"UGX {amount:,} safely banked. Receipt No: {deposit.receipt_number}")
        return redirect('customer_detail', customer_id=scheme.id)

    return render(request, 'schemes/make_deposit.html', {'scheme': scheme})


# 3. CUSTOMER ACCOUNT SCHEME LEDGER DETAILS
def customer_detail(request, customer_id):
    scheme = get_object_or_404(SavingsScheme, id=customer_id)
    
    # Corrected Model call: Querying SchemeDeposit linked to this specific balance
    deposits = SchemeDeposit.objects.filter(scheme=scheme).order_by('-deposited_at')
    
    context = {
        'scheme': scheme,
        'deposits': deposits,
        'total_balance': scheme.current_balance
    }
    return render(request, 'schemes/customer_detail.html', context)


# 4. COMPLEMENTARY LIST VIEW TO RESOLVE SYSTEM ROUTING
def schemes_list(request):
    active_schemes = SavingsScheme.objects.all().select_related('customer')
    return render(request, 'schemes/schemes_list.html', {'schemes': active_schemes})