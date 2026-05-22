from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction # For atomic transactions
from django.db.models import Sum # For faster reporting

from inventory.models import Product, StockMovement
#Changed 'Sale' to 'SalesOrder' to match your models.py
from .models import SalesOrder 

def make_sale(request):
    products = Product.objects.filter(current_stock__gt=0) # Only show products in stock

    if request.method == 'POST':
        try:
            product_id = request.POST.get('product')
            # Handle empty inputs to prevent crashes
            quantity_sold = int(request.POST.get('quantity') or 0)
            distance = float(request.POST.get('distance') or 0)

            if quantity_sold <= 0:
                messages.error(request, "Quantity must be greater than zero.")
                return redirect('make_sale')

            product = get_object_or_404(Product, id=product_id)

            # 1. STOCK VALIDATION
            if product.current_stock < quantity_sold:
                messages.error(request, f"Insufficient stock. {product.product_name} only has {product.current_stock} units.")
                return redirect('make_sale')

            # 2. CALCULATION
            total_price = product.selling_price * quantity_sold
            
            # Transport Logic (The Nyondo Rule)
            if distance <= 10 and total_price >= 500000:
                transport_fee = 0
            else:
                transport_fee = 30000
            
            final_amount = total_price + transport_fee

            # 3. ATOMIC EXECUTION (Sharp Practice)
            with transaction.atomic():
                # Update Inventory
                product.current_stock -= quantity_sold
                product.save()

                # QUERY METADATA FIXED: Using SalesOrder instead of Sale
                SalesOrder.objects.create(
                    product=product,
                    quantity=quantity_sold,
                    total_price=total_price,
                    transport_fee=transport_fee,
                    final_amount=final_amount,
                    sale_date=timezone.now()
                )

                # Create Stock Movement (Audit Trail)
                StockMovement.objects.create(
                    product=product,
                    transaction_type='OUT',
                    quantity=quantity_sold,
                    notes=f'Sold {quantity_sold} units'
                )

            messages.success(request, f"Sale recorded! Total: UGX {final_amount:,}")
            return redirect('sale_history')

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect('make_sale')

    return render(request, 'sales/make_sale.html', {'products': products})


def sale_history(request):
    # QUERY METADATA FIXED: Using SalesOrder instead of Sale
    sales = SalesOrder.objects.all().select_related('product').order_by('-sale_date')
    
    # Sharp Logic: Let the Database calculate totals (Aggregates)
    totals = sales.aggregate(
        rev=Sum('final_amount'),
        trans=Sum('transport_fee')
    )

    context = {
        'sales': sales,
        'total_revenue': totals['rev'] or 0,
        'total_transport': totals['trans'] or 0
    }
    return render(request, 'sales/history.html', context)