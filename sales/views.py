from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from inventory.models import Product, StockMovement
from .models import SalesOrder, SalesOrderItem, Customer, Receipt
import json
from schemes.models import SavingsScheme


from django.shortcuts import redirect, get_object_or_404



def make_sale(request, scheme_id=None):
    """ The Tile Grid Registry Terminal Workspace """
    customers = Customer.objects.all().order_by('name')
    products = Product.objects.filter(current_stock__gt=0).order_by('name')
    
    # Catch optional pre-selected scheme tracking allocations from link parameters
    active_scheme = None
    if scheme_id:
        active_scheme = get_object_or_404(SavingsScheme, id=scheme_id)
    
    context = {
        'customers': customers,
        'products': products,
        'active_scheme': active_scheme,  # Injected into context array for frontend JS binding
    }
    return render(request, 'sales/make_sale.html', context)


import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
# Ensure you import your models properly here (Customer, Product, SavingsScheme, SalesOrder, SalesOrderItem, StockMovement, Receipt)

def review_checkout(request):
    """ Intermediate Confirmation Step to compute transport rules and commit """
    if request.method != 'POST':
        return redirect('order_queue')
        
    customer_id = request.POST.get('customer')
    cart_data_raw = request.POST.get('cart_json')
    scheme_id = request.POST.get('scheme_id')
    
    if not customer_id or not cart_data_raw:
        messages.error(request, "Invalid checkout parameters submitted.")
        return redirect('record_sale')
        
    # --- FIXED: Handle dynamic token assignments vs real database profiles ---
    customer = None
    token_identifier = None

    if scheme_id:
        active_scheme = get_object_or_404(SavingsScheme, id=scheme_id)
        customer = active_scheme.customer
    elif 'Token' in str(customer_id):
        token_identifier = customer_id  # Stores "Token 50" text identifier safely
    else:
        try:
            customer = Customer.objects.get(id=customer_id)
        except (Customer.DoesNotExist, ValueError):
            customer = None
            token_identifier = f"Unknown Slot ({customer_id})"

    cart = json.loads(cart_data_raw)
    review_items = []
    subtotal = Decimal('0.00')
    
    for item in cart:
        product = get_object_or_404(Product, id=item['id'])
        qty = int(item['qty'])
        
        if qty > product.current_stock:
            messages.error(request, f"Stock clash! {product.name} only has {product.current_stock} left.")
            return redirect('record_sale')
            
        line_subtotal = Decimal(str(product.selling_price)) * qty
        subtotal += line_subtotal
        
        review_items.append({
            'product': product,
            'quantity': qty,
            'subtotal': line_subtotal
        })
        
    # Process final operational order confirmation
    if 'confirm_order' in request.POST:
        distance = float(request.POST.get('distance') or 0)
        payment_method = request.POST.get('payment_method', 'CASH')
        
        if distance == 0:
            transport_fee = Decimal('0.00')
        elif distance <= 10 and subtotal >= Decimal('500000.00'):
            transport_fee = Decimal('0.00')
        else:
            transport_fee = Decimal('30000.00')
            
        total_bill = subtotal + transport_fee
        
        # --- FINANCIAL GUARD: SCHEME DRAWDOWN AUDITING ---
        scheme_to_deduct = None
        if payment_method == 'SCHEME_BALANCE' or scheme_id:
            # Scheme check requires a real structural profile link
            if not customer:
                messages.error(request, "Operational clash: Anonymous walk-in token transactions cannot pull funds from a savings pool.")
                return redirect('record_sale')

            if scheme_id:
                scheme_to_deduct = get_object_or_404(SavingsScheme, id=scheme_id)
            else:
                scheme_to_deduct = SavingsScheme.objects.filter(customer=customer).first()
                
            if not scheme_to_deduct:
                messages.error(request, f"Operational clash: No active savings scheme ledger profile registered for {customer.name}.")
                return redirect('record_sale')
                
            if total_bill > scheme_to_deduct.current_balance:
                messages.error(
                    request, 
                    f"Insufficient Scheme Balance! {customer.name} has saved UGX {scheme_to_deduct.current_balance:,}, "
                    f"but this collection order totals UGX {total_bill:,}."
                )
                return redirect('record_sale')
        # -------------------------------------------------

        try:
            with transaction.atomic():
                # Deduct funds from scheme if using scheme payment method
                if scheme_to_deduct:
                    scheme_to_deduct.current_balance -= total_bill
                    scheme_to_deduct.save()
                    
                # Build dynamic tracking descriptor notes for walk-in receipts
                order_notes = f"Walk-in Transaction via {token_identifier}" if token_identifier else ""
                if scheme_to_deduct:
                    order_notes = f"Scheme Clearance Drawdown Summary for account {customer.name}"

                sales_order = SalesOrder.objects.create(
                    customer=customer, # Stored as Null for generic walk-in tokens
                    payment_method=payment_method,
                    status='PENDING',
                    subtotal=subtotal,
                    transport_fee=transport_fee,
                    total_amount=total_bill,
                    #notes=order_notes, # Injects tracking identifiers cleanly into the order metadata record
                    served_by=request.user if request.user.is_authenticated else None
                )
                
                for item in review_items:
                    prod = item['product']
                    prod.current_stock -= item['quantity']
                    prod.save()
                    
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        product=prod,
                        quantity=item['quantity'],
                        unit_price=prod.selling_price,
                        subtotal=item['subtotal']
                    )
                    
                    StockMovement.objects.create(
                        product=prod,
                        transaction_type='OUT',
                        quantity=item['quantity'],
                        notes=f"Scheme Clearance Drawdown Order SO-{sales_order.id}" if scheme_to_deduct else f"POS Token Order SO-{sales_order.id} ({token_identifier or 'Walk-in'})"
                    )
                    
                Receipt.objects.create(
                    sales_order=sales_order,
                    receipt_number=f"NYD-{sales_order.id}-{int(timezone.now().timestamp())}",
                    recorded_by=request.user if request.user.is_authenticated else None
                )
                
            messages.success(request, f"Sales Order SO-{sales_order.id} allocated successfully! Assigned identifier: {token_identifier or customer.name}.")
            return redirect('order_queue')
            
        except Exception as e:
            messages.error(request, f"Transaction error encountered: {e}")
            return redirect('record_sale')
            
    # Include existing active scheme reference metadata inside the template pass dictionary
    active_scheme = get_object_or_404(SavingsScheme, id=scheme_id) if scheme_id else None
            
    context = {
        'customer': customer,
        'token_identifier': token_identifier, # Added to track context visually on review_checkout.html
        'review_items': review_items,
        'subtotal': subtotal,
        'cart_json': cart_data_raw,
        'active_scheme': active_scheme
    }
    return render(request, 'sales/review_checkout.html', context)


def sale_history(request):
    # 1. FIXED: Removed .select_related('product') to stop the hidden join crash
    sales = SalesOrder.objects.all().order_by('-order_date')
    
    # 2. FIXED: Changed 'final_amount' to 'total_amount' to match your database choices
    totals = sales.aggregate(
        rev=Sum('total_amount'),
        trans=Sum('transport_fee')
    )

    context = {
        'sales': sales,
        'total_revenue': totals['rev'] or 0,
        'total_transport': totals['trans'] or 0
    }
    return render(request, 'sales/history.html', context)

def order_queue_dashboard(request):
    """ Displays all open orders waiting for cashier payment clearance """
    # Fetch orders where status is PENDING or waiting to be cleared
    pending_orders = SalesOrder.objects.filter(status='PENDING').select_related('customer', 'served_by').order_by('id')
    
    context = {
        'pending_orders': pending_orders,
    }
    return render(request, 'sales/order_queue.html', context)


def process_queue_clearance(request, order_id):
    """
    Processes and clears a pending queue ticket order, transitioning 
    its status to COMPLETED so it updates real-time administrative reports.
    """
    # 1. Fetch the specific order or return a 404 page if not found
    order = get_object_or_404(SalesOrder, id=order_id)
    
    # 2. Safety Check: Only process if it isn't already completed
    if order.status == 'COMPLETED':
        messages.warning(request, f"Order #{order.id} has already been cleared and processed.")
        return redirect('sales:queue_list')  # Adjust to your actual queue list redirect name
        
    try:
        # 3. Transition the status and log who cleared the ticket
        order.status = 'COMPLETED'
        order.served_by = request.user  # Records the active cashier for performance tracking
        order.updated_at = timezone.now() # Updates timestamp log
        order.save()
        
        # 4. Push a success notification to the UI toast messages
        messages.success(request, f"Success! Order #{order.id} has been cleared and posted to revenue metrics.")
        
    except Exception as e:
        messages.error(request, f"An error occurred while clearing the queue: {str(e)}")
        
    # 5. Redirect back to the pending queue panel deck layout
    return redirect('order_queue')  # Change this to match the URL name of your active checkout queue page


def checkout_collection_detail(request, order_id):
    """
    Renders the itemized verification sheet for a pending orders.
    Provides receipt printing layouts and houses the queue clearance execution trigger.
    """
    # Fetch the order ensuring it is still PENDING or processing
    order = get_object_or_404(SalesOrder, id=order_id)
    
    # Retrieve all items linked to this hardware order sheet
    order_items = SalesOrderItem.objects.filter(sales_order=order)
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'sales/checkout_collection_detail.html', context)


def checkout_collection_detail(request, order_id):
    # 1. Fetch the exact order using the ID from the URL
    order = get_object_or_404(SalesOrder, id=order_id)
    
    # 2. If the user clicks "Clear & Post Transaction", it sends a POST request here
    if request.method == 'POST':
        order.status = 'COMPLETED'
        order.save()
        
        messages.success(request, f"Order T-{order.id} has been successfully cleared and posted!")
        # Redirect back to whichever dashboard you use as the main queue screen
        return redirect('reports:dashboard') 
        
    # 3. Gather all item rows belonging to this order sheet so the template can loop them
    order_items = SalesOrderItem.objects.filter(sales_order=order).select_related('product')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'sales/checkout_collection_detail.html', context)


def invoice_detail_receipt(request, order_id):
    """
    Renders the clean, customer-facing retail invoice layout designed 
    specifically for printing clear physical receipts.
    """
    order = get_object_or_404(SalesOrder, id=order_id)
    # Prefetch product details to cleanly populate the inventory matrix rows
    order_items = SalesOrderItem.objects.filter(sales_order=order).select_related('product')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    # Make sure this matches the filename where you saved that customer invoice template!
    return render(request, 'sales/receipt_detail.html', context)