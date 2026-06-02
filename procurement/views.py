from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test

from .forms import UnifiedPurchaseForm
from .models import PurchaseOrder, PurchaseItem, Supplier
from inventory.models import Product, StockMovement


# ROLE PROTECTION HELPER FUNCTIONS

def is_admin_or_manager(user):
    """Allows Accounts/Admin and Store Managers to manage supply operations."""
    return user.is_authenticated and (user.role in ['ADMIN', 'MANAGER'] or user.is_superuser)

# CORE PROCUREMENTS FUNCTIONALITIES

@login_required
def record_purchase(request):
    suppliers = Supplier.objects.filter(is_active=True)
    products = Product.objects.all()

    if request.method == 'POST':
        try:
            supplier_id = request.POST.get('supplier')
            invoice_no = request.POST.get('invoice_number').strip()
            product_id = request.POST.get('product')
            qty = int(request.POST.get('quantity', 0))
            cost = float(request.POST.get('unit_cost', 0))
            paid = float(request.POST.get('amount_paid', 0))

            # VALIDATION
            if qty <= 0:
                messages.error(request, "Quantity must be greater than zero.")
                return redirect('record_purchase')

            if cost <= 0:
                messages.error(request, "Unit cost must be greater than zero.")
                return redirect('record_purchase')

            # DUPLICATE INVOICE CHECK
            if PurchaseOrder.objects.filter(invoice_number=invoice_no).exists():
                messages.error(request, "Invoice already exists.")
                return redirect('record_purchase')

            # AUTO-ADJUST QUANTITY
            if paid > (qty * cost):
                original_qty = qty
                qty = int(paid // cost)
                messages.info(request, f"Quantity adjusted from {original_qty} to {qty} based on payment.")

            # CALCULATIONS
            total_cost = qty * cost
            balance = total_cost - paid

            # PAYMENT STATUS
            if balance <= 0:
                status = 'PAID'
            elif paid > 0:
                status = 'PARTIAL'
            else:
                status = 'PENDING'

            with transaction.atomic():
                # CREATE ORDER
                order = PurchaseOrder.objects.create(
                    supplier_id=supplier_id,
                    invoice_number=invoice_no,
                    total_amount=total_cost,
                    amount_paid=paid,
                    balance=balance,
                    payment_status=status
                )

                # CREATE PURCHASE ITEM
                PurchaseItem.objects.create(
                    purchase_order=order,
                    product_id=product_id,
                    quantity=qty,
                    unit_cost=cost,
                    subtotal=total_cost
                )

                # UPDATE INVENTORY
                product = Product.objects.get(id=product_id)
                product.current_stock += qty

                # UPDATE PRODUCT COST
                product.cost_price = cost
                product.save()

                # STOCK MOVEMENT / AUDIT TRAIL
                StockMovement.objects.create(
                    product=product,
                    transaction_type='IN',
                    quantity=qty,
                    notes=f"Purchased from {order.supplier.name} (Invoice: {invoice_no})"
                )

            messages.success(request, f"Purchase recorded successfully. Supplier balance: UGX {balance:,}")
            return redirect('purchase_list')

        except Exception as e:
            messages.error(request, f"Error recording purchase: {e}")

    context = {
        'suppliers': suppliers,
        'products': products
    }
    return render(request, 'procurement/add_purchase.html', context)


@login_required
def receive_credit_stock(request):
    suppliers = Supplier.objects.filter(is_active=True)
    products = Product.objects.all()
    
    context = {
        'suppliers': suppliers,
        'products': products
    }
    return render(request, 'procurement/receive_credit_stock.html', context)


@login_required
def procurement_dashboard(request):
    total_orders = PurchaseOrder.objects.count()
    total_spent = PurchaseOrder.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = PurchaseOrder.objects.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_debt = PurchaseOrder.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or 0
    
    pending_count = PurchaseOrder.objects.filter(payment_status='PENDING').count()
    partial_count = PurchaseOrder.objects.filter(payment_status='PARTIAL').count()
    paid_count = PurchaseOrder.objects.filter(payment_status='PAID').count()
    
    recent_orders = PurchaseOrder.objects.select_related('supplier').order_by('-created_at')[:5]
    recent_items = PurchaseItem.objects.select_related('product', 'purchase_order').order_by('-purchase_order__created_at')[:5]

    context = {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'total_paid': total_paid,
        'total_debt': total_debt,
        'pending_count': pending_count,
        'partial_count': partial_count,
        'paid_count': paid_count,
        'recent_orders': recent_orders,
        'recent_items': recent_items,
    }
    return render(request, 'procurement/dashboard.html', context)


@login_required
def record_procurement_entry(request):
    if request.method == 'POST':
        form = UnifiedPurchaseForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.cleaned_data['product']
                    quantity = form.cleaned_data['quantity']
                    unit_cost = form.cleaned_data['unit_cost']
                    payment_type = form.cleaned_data['payment_type']
                    
                    total_calculated_amount = quantity * unit_cost
                    amount_paid = form.cleaned_data.get('amount_paid') or 0
                    
                    if payment_type == 'CASH':
                        amount_paid = total_calculated_amount
                    
                    balance_outstanding = total_calculated_amount - amount_paid
                    
                    if balance_outstanding == 0:
                        status = 'PAID'
                    elif amount_paid > 0:
                        status = 'PARTIAL'
                    else:
                        status = 'PENDING'
                    
                    purchase_order = PurchaseOrder.objects.create(
                        supplier=form.cleaned_data['supplier'],
                        invoice_number=form.cleaned_data['invoice_number'],
                        total_amount=total_calculated_amount,
                        amount_paid=amount_paid,
                        balance=balance_outstanding,
                        payment_status=status,
                        notes=form.cleaned_data['notes']
                    )
                    
                    PurchaseItem.objects.create(
                        purchase_order=purchase_order,
                        product=product,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        subtotal=total_calculated_amount
                    )
                    
                    product.current_stock += quantity
                    product.save()
                    
                    StockMovement.objects.create(
                        product=product,
                        transaction_type='IN',
                        quantity=quantity,
                        reference=f"PUR-{purchase_order.invoice_number}",
                        notes=f"Procured via inbound shipment. Payment scheme configuration: {payment_type}"
                    )
                    
                messages.success(request, f"Shipment ingested successfully! {quantity} units added directly to hardware inventory registry.")
                return redirect('procurement_dashboard')
                
            except Exception as e:
                messages.error(request, f"System compilation failure during database save action nodes: {str(e)}")
    else:
        form = UnifiedPurchaseForm()
        
    return render(request, 'procurement/record_purchase.html', {'form': form})

@login_required()
def supplier_debt_list(request):
    debtors = []
    total_global_debt = 0

    # 1. Pull all active suppliers
    suppliers = Supplier.objects.filter(is_active=True)

    for supplier in suppliers:
        # 2. Get the total cost of all orders from this supplier
        total_owed = PurchaseOrder.objects.filter(supplier=supplier).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # 3. Sum up what you have paid them directly from the purchase orders
        total_paid = PurchaseOrder.objects.filter(supplier=supplier).aggregate(
            total=Sum('amount_paid')
        )['total'] or 0

        # 4. Use your model's stored outstanding balance field
        remaining_balance = PurchaseOrder.objects.filter(supplier=supplier).aggregate(
            total=Sum('balance')
        )['total'] or 0

        # 5. Build our ledger array dynamically if there's an outstanding balance
        if remaining_balance > 0:
            supplier.total_owed = total_owed
            supplier.total_paid = total_paid
            supplier.remaining_balance = remaining_balance
            
            debtors.append(supplier)
            total_global_debt += remaining_balance

    context = {
        'debtors': debtors,
        'total_global_debt': total_global_debt,
        'next_due_date': None,
    }
    
    return render(request, 'procurement/supplier_debt_list.html', context)

@login_required
def clear_supplier_credit(request, debt_id):
    if request.method == "POST":
        purchase_order = get_object_or_404(PurchaseOrder, id=debt_id)
        payment_amount = Decimal(request.POST.get('amount_paid', '0.00'))

        if payment_amount <= 0:
            messages.error(request, "Please enter a valid payment amount.")
        elif payment_amount > purchase_order.balance:
            messages.error(request, f"Cannot pay more than the outstanding balance of UGX {purchase_order.balance}")
        else:
            # 1. Deduct the liability balance
            purchase_order.balance -= payment_amount
            purchase_order.save()
            
            # 2. Success message back to dashboard
            messages.success(request, f"Successfully paid UGX {payment_amount} to supplier!")
            
    return redirect('unpaid_supplier')