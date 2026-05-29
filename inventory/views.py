from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import F
from django.db import transaction
import datetime
from .models import Product, StockMovement, Category
# Import models from your procurement app to track supplier credits
from procurement.models import Supplier, PurchaseOrder 
from .models import AuditLog



def product_list(request):
    products = Product.objects.all().order_by('name')
    context = {'products': products}
    return render(request, 'product_list.html', context)


def inventory_dashboard(request):
    products = Product.objects.all()
    for product in products:
        if product.average_daily_sales > 0:
            product.days_until_stockout = round(
            product.current_stock / product.average_daily_sales
        )
        else:
            product.days_until_stockout = "Unlimited"
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
    return render(request, 'dashboard.html', context)


def product_save(request, product_id=None):
    # 1. SETUP: If an ID is passed, we are EDITING. If not, we are CREATING.
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        page_title = f"Modify Item: {product.name}"
    else:
        product = None
        page_title = "Register New Inventory Product"

    # 2. POST FLOW: Saving the form data
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        cost = float(request.POST.get('cost_price', 0))
        price = float(request.POST.get('selling_price', 0))
        uom = request.POST.get('unit_of_measure', '')
        current_stock = int(request.POST.get('current_stock', 0))
        reorder_lvl = int(request.POST.get('reorder_level', 10))
        cat_id = request.POST.get('category')

        # Safety fallback for the Category rule
        if cat_id:
            try:
                category_obj = Category.objects.get(id=cat_id)
            except Category.DoesNotExist:
                category_obj, _ = Category.objects.get_or_create(name="General Hardware")
        else:
            category_obj, _ = Category.objects.get_or_create(name="General Hardware")

        if product:
            # 👉 EDIT ROUTINE: Update fields on the existing database row
            product.name = name
            product.category = category_obj
            product.cost_price = cost
            product.selling_price = price
            product.unit_of_measure = uom
            product.current_stock = current_stock
            product.reorder_level = reorder_lvl
            product.save()
            messages.success(request, f"Changes committed to '{name}' successfully.")
        else:
            # 👉 CREATE ROUTINE: Ingest a brand new row into the table
            sku = f"NYO-{category_obj.name[:2].upper()}-{name[:3].upper()}-{int(timezone.now().timestamp())}"[:20]
            Product.objects.create(
                name=name,
                category=category_obj,
                cost_price=cost,
                selling_price=price,
                unit_of_measure=uom,
                sku=sku,
                current_stock=current_stock,
                reorder_level=reorder_lvl
            )
            messages.success(request, f"New product '{name}' registered smoothly.")

        return redirect('product_list')

    # 3. GET FLOW: Rendering the page layout with existing data (if editing)
    categories = Category.objects.all()
    context = {
        'product': product,      # Will be None when creating, full object when editing
        'categories': categories,
        'page_title': page_title
    }
    return render(request, 'product_form.html', context)


def product_create(request):
    """
    Handles registering completely new items lines (e.g. adding 16mm iron bars for the first time)
    as well as restocking existing items lines under smart financial payment conditions.
    """
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        cat_id = request.POST.get('category')
        cost = float(request.POST.get('cost_price', 0))
        price = float(request.POST.get('selling_price', 0))
        uom = request.POST.get('unit_of_measure', 'Pcs') or 'Pcs'
        reorder_lvl = int(request.POST.get('reorder_level', 10))
        initial_stock = int(request.POST.get('current_stock', 0))
        
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

        # 🚀 THE SAFETY ENGINE FIX:
        # Instead of get_object_or_404 crashing, check if the category exists.
        # If it doesn't exist or none was selected, create/fetch a default one on the fly!
        if cat_id:
            try:
                category = Category.objects.get(id=cat_id)
            except Category.DoesNotExist:
                category, _ = Category.objects.get_or_create(name="General Hardware")
        else:
            category, _ = Category.objects.get_or_create(name="General Hardware")

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
                
                if hasattr(supplier, 'total_owed'):
                    supplier.total_owed += batch_liability
                    supplier.save()

                PurchaseOrder.objects.create(
                    supplier=supplier,
                    product=product,
                    quantity=initial_stock,
                    unit_cost=cost,
                    balance=batch_liability,
                    served_by=request.user if request.user.is_authenticated else None
                )
                action_text += f" UGX {batch_liability:,.0f} logged as credit debt to {supplier.name}."

            # Safe Audit logging check
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=f"Registered product {product.name}"
            )    

            messages.success(request, action_text)
            return redirect('product_list')

    # GET Request processing
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    
    context = {
        'categories': categories,
        'suppliers': suppliers
    }
    return render(request, 'product_form.html', context)


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
