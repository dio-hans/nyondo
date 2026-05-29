from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from inventory.models import Product, StockMovement
from .models import SalesOrder, SalesOrderItem, Customer, Receipt
import json


def make_sale(request):
    """ The Tile Grid Registry Terminal Workspace """
    customers = Customer.objects.all().order_by('name')
    products = Product.objects.filter(current_stock__gt=0).order_by('name')
    
    context = {
        'customers': customers,
        'products': products,
    }
    return render(request, 'sales/make_sale.html', context)


def review_checkout(request):
    """ Intermediate Confirmation Step to compute transport rules and commit """
    if request.method != 'POST':
        return redirect('order_queue')
        
    customer_id = request.POST.get('customer')
    # Read the packed JSON cart dictionary from the frontend
    cart_data_raw = request.POST.get('cart_json')
    
    if not customer_id or not cart_data_raw:
        messages.error(request, "Invalid checkout parameters submitted.")
        return redirect('make_sale')
        
    customer = get_object_or_404(Customer, id=customer_id)
    cart = json.loads(cart_data_raw)  # Format: [{"id": "1", "qty": 2}, ...]
    
    review_items = []
    subtotal = Decimal('0.00')
    
    # Pre-calculate line allocations for review validation
    for item in cart:
        product = get_object_or_404(Product, id=item['id'])
        qty = int(item['qty'])
        
        if qty > product.current_stock:
            messages.error(request, f"Stock clash! {product.name} only has {product.current_stock} left.")
            return redirect('make_sale')
            
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
        
        # Apply the Official Nyondo Transport Rule
        if distance <= 10 and subtotal >= Decimal('500000'):
            transport_fee = Decimal('0.00')
        else:
            transport_fee = Decimal('30000.00')
            
        try:
            with transaction.atomic():
                sales_order = SalesOrder.objects.create(
                    customer=customer,
                    payment_method=payment_method,
                    status='PENDING',
                    subtotal=subtotal,
                    transport_fee=transport_fee,
                    total_amount=subtotal + transport_fee,
                    served_by=request.user if request.user.is_authenticated else None
                )
                
                for item in review_items:
                    # Deduct stock totals
                    prod = item['product']
                    prod.current_stock -= item['quantity']
                    prod.save()
                    
                    # Create child row lines
                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        product=prod,
                        quantity=item['quantity'],
                        unit_price=prod.selling_price,
                        subtotal=item['subtotal']
                    )
                    
                    # Save audit movement trail
                    StockMovement.objects.create(
                        product=prod,
                        transaction_type='OUT',
                        quantity=item['quantity'],
                        notes=f"POS Cart Checkout Order SO-{sales_order.id}"
                    )
                    
                # Generate unique POS code asset token
                Receipt.objects.create(
                    sales_order=sales_order,
                    receipt_number=f"NYD-{sales_order.id}-{int(timezone.now().timestamp())}",
                    recorded_by=request.user if request.user.is_authenticated else None
                )
                
            messages.success(request, f"Sales Order SO-{sales_order.id} processed successfully!")
            return redirect('order_queue')
            
        except Exception as e:
            messages.error(request, f"Transaction error encountered: {e}")
            return redirect('record_sale')
            
    context = {
        'customer': customer,
        'review_items': review_items,
        'subtotal': subtotal,
        'cart_json': cart_data_raw
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