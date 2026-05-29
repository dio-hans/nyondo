from django.shortcuts import render, redirect
from django.contrib import messages

from django.db import transaction
from .forms import UnifiedPurchaseForm
from .models import PurchaseOrder, PurchaseItem
from inventory.models import Product, StockMovement

from django.db.models import Sum

from .models import Supplier

def record_purchase(request):

    suppliers = Supplier.objects.filter(
        is_active=True
    )

    products = Product.objects.all()

    if request.method == 'POST':

        try:

            supplier_id = request.POST.get(
                'supplier'
            )

            invoice_no = request.POST.get(
                'invoice_number'
            ).strip()

            product_id = request.POST.get(
                'product'
            )

            qty = int(
                request.POST.get(
                    'quantity',
                    0
                )
            )

            cost = float(
                request.POST.get(
                    'unit_cost',
                    0
                )
            )

            paid = float(
                request.POST.get(
                    'amount_paid',
                    0
                )
            )

            # VALIDATION

            if qty <= 0:

                messages.error(
                    request,
                    "Quantity must be greater than zero."
                )

                return redirect(
                    'record_purchase'
                )

            if cost <= 0:

                messages.error(
                    request,
                    "Unit cost must be greater than zero."
                )

                return redirect(
                    'record_purchase'
                )

            # DUPLICATE INVOICE CHECK

            if PurchaseOrder.objects.filter(
                invoice_number=invoice_no
            ).exists():

                messages.error(
                    request,
                    "Invoice already exists."
                )

                return redirect(
                    'record_purchase'
                )

            # AUTO-ADJUST QUANTITY
            # If payment exceeds expected amount,
            # system recalculates actual quantity received.

            if paid > (qty * cost):

                original_qty = qty

                qty = int(paid // cost)

                messages.info(
                    request,
                    f"Quantity adjusted from "
                    f"{original_qty} to {qty} "
                    f"based on payment."
                )

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

                product = Product.objects.get(
                    id=product_id
                )

                product.current_stock += qty

                # UPDATE PRODUCT COST

                product.cost_price = cost

                product.save()

                # STOCK MOVEMENT / AUDIT TRAIL

                StockMovement.objects.create(

                    product=product,

                    transaction_type='IN',

                    quantity=qty,

                    notes=(
                        f"Purchased from "
                        f"{order.supplier.name} "
                        f"(Invoice: {invoice_no})"
                    )

                )

            messages.success(

                request,

                f"Purchase recorded successfully. "
                f"Supplier balance: UGX {balance:,}"

            )

            return redirect(
                'purchase_list'
            )

        except Exception as e:

            messages.error(
                request,
                f"Error recording purchase: {e}"
            )

    context = {

        'suppliers': suppliers,

        'products': products

    }

    return render(request, 'procurement/add_purchase.html', context)


# SUPPLIER DEBT LIST

def supplier_debt_list(request):

    unpaid_orders = PurchaseOrder.objects.filter(

        balance__gt=0

    ).order_by('created_at')

    total_debt = unpaid_orders.aggregate(

        Sum('balance')

    )['balance__sum'] or 0

    context = {

        'orders': unpaid_orders,

        'total_debt': total_debt

    }

    return render(request, 'procurement/debt_list.html', context)

# Add this at the bottom of procurement/views.py
def receive_credit_stock(request):
    # Fetch active suppliers and products to populate your form dropdowns
    suppliers = Supplier.objects.filter(is_active=True)
    products = Product.objects.all()
    
    context = {
        'suppliers': suppliers,
        'products': products
    }
    return render(request, 'procurement/receive_credit_stock.html', context)


def procurement_dashboard(request):
    # 1. High-level KPI metrics
    total_orders = PurchaseOrder.objects.count()
    total_spent = PurchaseOrder.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = PurchaseOrder.objects.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_debt = PurchaseOrder.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or 0
    
    # 2. Status counts for badges
    pending_count = PurchaseOrder.objects.filter(payment_status='PENDING').count()
    partial_count = PurchaseOrder.objects.filter(payment_status='PARTIAL').count()
    paid_count = PurchaseOrder.objects.filter(payment_status='PAID').count()
    
    # 3. Recent activity lists
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

def record_procurement_entry(request):
    if request.method == 'POST':
        form = UnifiedPurchaseForm(request.POST)
        if form.is_valid():
            try:
                # Wrap everything in a database transaction block so it never corrupts data on crash
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
                    
                    # 1. Determine Payment Status
                    if balance_outstanding == 0:
                        status = 'PAID'
                    elif amount_paid > 0:
                        status = 'PARTIAL'
                    else:
                        status = 'PENDING'
                    
                    # 2. Write the PurchaseOrder Registry entry
                    purchase_order = PurchaseOrder.objects.create(
                        supplier=form.cleaned_data['supplier'],
                        invoice_number=form.cleaned_data['invoice_number'],
                        total_amount=total_calculated_amount,
                        amount_paid=amount_paid,
                        balance=balance_outstanding,
                        payment_status=status,
                        notes=form.cleaned_data['notes']
                    )
                    
                    # 3. Write individual Line Item entry
                    PurchaseItem.objects.create(
                        purchase_order=purchase_order,
                        product=product,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        subtotal=total_calculated_amount
                    )
                    
                    # 4. CRITICAL CORE SYNC: Update the stock sheets in the Inventory app directly
                    product.current_stock += quantity
                    product.save()
                    
                    # 5. Log internal audit history trail
                    StockMovement.objects.create(
                        product=product,
                        transaction_type='IN',
                        quantity=quantity,
                        reference=f"PUR-{purchase_order.invoice_number}",
                        notes=f"Procured via inbound shipment. Payment scheme configuration: {payment_type}"
                    )
                    
                messages.success(request, f"Shipment ingested successfully! {quantity} units added directly to hardware inventory registry.")
                return redirect('procurement_dashboard') # Update this match string name to your main view
                
            except Exception as e:
                messages.error(request, f"System compilation failure during database save action nodes: {str(e)}")
    else:
        form = UnifiedPurchaseForm()
        
    return render(request, 'procurement/record_purchase.html', {'form': form})