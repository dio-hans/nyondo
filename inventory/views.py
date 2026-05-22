from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import F
from django.db import transaction
import datetime
from django.contrib.auth.decorators import login_required
from .models import Product, StockMovement, Category
# Import models from your procurement app to track supplier credits
from procurement.models import Supplier, PurchaseOrder 

@login_required
def product_list(request):
    products = Product.objects.all().order_by('name')
    context = {'products': products}
    return render(request, 'inventory/product_list.html', context)

@login_required
def inventory_dashboard(request):
    products = Product.objects.all()
    total_products = products.count()
    
    # Compare current stock levels to custom reorder levels dynamically
    low_stock_products = Product.objects.filter(current_stock__lte=F('reorder_level'))

    total_stock_value = sum(p.current_stock * p.cost_price for p in products)
    expected_profit = sum(p.current_stock * (p.selling_price - p.cost_price) for p in products)
    recent_movements = StockMovement.objects.order_by('-created_at')[:5]

    context = {
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_stock_value': total_stock_value,
        'expected_profit': expected_profit, 
        'recent_movements': recent_movements,
        'products': products[:10] 
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def product_create(request):
    """
    Handles registering completely new items lines (e.g. adding 16mm iron bars for the first time)
    as well as restocking existing items lines under smart financial payment conditions.
    """
    if request.method == "POST":
        name = request.POST.get('name')
        cat_id = request.POST.get('category')
        cost = float(request.POST.get('cost_price', 0))
        price = float(request.POST.get('selling_price', 0))
        uom = request.POST.get('unit_of_measure')
        reorder_lvl = int(request.POST.get('reorder_level', 10))
        initial_stock = int(request.POST.get('initial_stock', 0))
        
        # Smart Credit Parameter Flags
        is_credit = request.POST.get('is_credit') == 'on'
        supplier_id = request.POST.get('supplier_id')

        # Rule Validation: selling price must outpace procurement costs
        if price <= cost:
            messages.error(request, "Critical Validation Error: Selling price must be greater than cost price.")
            return redirect('product_create')

        # Rule Validation: Credit mode requires an assigned factory supplier depot
        if is_credit and not supplier_id:
            messages.error(request, "Credit Exception: You must select a Supplier profile when logging credit arrivals.")
            return redirect('product_create')

        category = get_object_or_404(Category, id=cat_id)

        # Execution using atomic transaction guards to preserve database state integrity
        with transaction.atomic():
            # Check if this item name already exists in this category (Restocking Flow)
            product_match = Product.objects.filter(name__iexact=name, category=category).first()

            if product_match:
                # 1. Update matching product data values directly
                product_match.current_stock += initial_stock
                product_match.cost_price = cost
                product_match.selling_price = price
                product_match.save()
                product = product_match
                action_text = f"Restocked {initial_stock} units of existing item line: {name}."
            else:
                # 2. Build out a custom unique SKU index string and save a new Product line
                sku = f"NYO-{category.name[:2].upper()}-{name[:3].upper()}-{datetime.datetime.now().strftime('%S')}"
                product = Product.objects.create(
                    name=name,
                    category=category,
                    cost_price=cost,
                    selling_price=price,
                    unit_of_measure=uom,
                    sku=sku,
                    reorder_level=reorder_lvl,
                    current_stock=initial_stock
                )
                action_text = f"Registered brand new inventory product profile: {name}."

            # 3. Write universal Double-Entry audit movement record
            StockMovement.objects.create(
                product=product,
                transaction_type='IN',
                quantity=initial_stock,
                notes='Credit Supply Consolidated' if is_credit else 'Cash Sourced Intake'
            )

            # 4. If credit toggle was active, process accounts payable values automatically
            if is_credit:
                supplier = get_object_or_404(Supplier, id=supplier_id)
                batch_liability = initial_stock * cost
                
                # Increment running supplier ledger totals if column field tracks it
                if hasattr(supplier, 'total_owed'):
                    supplier.total_owed += batch_liability
                    supplier.save()

                # Save permanent Procurement record entry tracking this unliquidated batch
                PurchaseOrder.objects.create(
                    supplier=supplier,
                    product=product,
                    quantity=initial_stock,
                    unit_cost=cost,
                    balance=batch_liability,
                    served_by=request.user if request.user.is_authenticated else None
                )
                action_text += f" UGX {batch_liability:,.0f} logged as credit debt to {supplier.name}."

            messages.success(request, action_text)
            return redirect('product_list')

    # GET Request processing
    categories = Category.objects.all()
    suppliers = Supplier.objects.all() # Passed to fill the smart conditional dropdown menu
    
    context = {
        'categories': categories,
        'suppliers': suppliers
    }
    return render(request, 'inventory/product_form.html', context)

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    stock_movements = StockMovement.objects.filter(product=product).order_by('-created_at')

    stock_value = product.current_stock * product.cost_price
    expected_revenue = product.current_stock * product.selling_price
    expected_profit = expected_revenue - stock_value
    is_low_stock = product.current_stock <= product.reorder_level

    context = {
        'product': product,
        'stock_movements': stock_movements,
        'stock_value': stock_value,
        'expected_revenue': expected_revenue,
        'expected_profit': expected_profit,
        'is_low_stock': is_low_stock
    }
    return render(request, 'inventory/product_detail.html', context)