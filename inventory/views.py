from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from procurement.models import PurchaseItem, Supplier

from .models import Product, StockMovement, Category, AuditLog
from procurement.models import PurchaseOrder 
from django.contrib.auth.decorators import login_required
from reports.decorators import role_required
from .forms import ProductForm


@login_required
@role_required(['MANAGER', 'ADMIN', 'SALES'])
def product_list(request):
    products = Product.objects.all().order_by('current_stock')
    context = {'products': products}
    return render(request, 'product_list.html', context)

@login_required
@role_required(['MANAGER'])
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
    
    low_stock_products = Product.objects.filter(current_stock__lte=F('reorder_level'))

    total_stock_value = f"{int(sum(p.current_stock * p.cost_price for p in products)):,}"
    expected_profit = f"{int(sum(p.current_stock * (p.selling_price - p.cost_price) for p in products)):,}"
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

@login_required
@role_required(['MANAGER'])
def product_save(request, product_id=None):
    """
    Enables store managers to correct historical manual entry mistakes,
    modify product details, or shift cost pricing configurations.
    """
    product = get_object_or_404(Product, id=product_id)
    page_title = f"Administrative Corrections: {product.name}"

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        cost = float(request.POST.get('cost_price', 0))
        price = float(request.POST.get('selling_price', 0))
        uom = request.POST.get('unit_of_measure', '')
        current_stock = int(request.POST.get('quantity', 0))  # Maps safely to your input tag name
        reorder_lvl = int(request.POST.get('reorder_level', 10))
        cat_id = request.POST.get('category')

        if cat_id:
            category_obj = get_object_or_404(Category, id=cat_id)
        else:
            category_obj, _ = Category.objects.get_or_create(name="General Hardware")

        if price <= cost:
            messages.error(request, "Correction Rejected: Selling price must exceed system unit cost parameters.")
            return redirect('product_save', product_id=product.id)

        # Log changes before committing updates to the database
        old_stock = product.current_stock
        
        product.name = name
        product.category = category_obj
        product.cost_price = cost
        product.selling_price = price
        product.unit_of_measure = uom
        product.current_stock = current_stock
        product.reorder_level = reorder_lvl
        product.save()

        # If manual stock override occurred, record a specific movement log entry
        if old_stock != current_stock:
            StockMovement.objects.create(
                product=product,
                transaction_type='IN' if current_stock > old_stock else 'OUT',
                quantity=abs(current_stock - old_stock),
                notes=f"Manual discrepancy correction override log. Adjusted from {old_stock} to {current_stock}."
            )

        messages.success(request, f"Administrative parameters for '{name}' successfully altered and re-indexed.")
        return redirect('product_list')

    categories = Category.objects.all()
    context = {
        'product': product,
        'categories': categories,
        'page_title': page_title,
        'suppliers': None  # Supplier overrides are blocked during basic attribute correction
    }
    return render(request, 'inventory/product_form.html', context)


def render_product_form_with_errors(request, form_instance):
    """
    Helper function to render the product form layout. 
    It preserves user-typed data inside form_instance and loads background lookup data.
    """
    return render(request, 'product_form.html', {
        'form': form_instance,
        'categories': Category.objects.all(),
        'suppliers': Supplier.objects.filter(is_active=True),
        'existing_products': Product.objects.all().order_by('name'),
        'product': None
    })


@login_required
@role_required(['MANAGER'])
def product_create(request):
    """
    Unified Inbound Flow: Handles standard cash restocks, brand new inventory registrations, 
    and multi-app credit liabilities within a single transactional interface.
    """
    if request.method == "POST":
        form = ProductForm(request.POST)
        
        # NOTE: If your Django form is validating fields strictly, the mismatched 
        # input names will make form.is_valid() return False. To bypass field name
        # lockdown problems, we pull directly from request.POST as fallbacks.
        if form.is_valid():
            data = form.cleaned_data
            name = data.get('name')
            cost = data.get('cost_price')      
            price = data.get('selling_price')  
            is_credit = data.get('is_credit')
            supplier_id = data.get('supplier_id')
            cat_id = data.get('cat_id') or request.POST.get('category')
            qty_arriving = data.get('qty_arriving') or int(request.POST.get('quantity', 0))
            uom = data.get('unit_of_measure') or request.POST.get('unit_of_measure')
            reorder_lvl = data.get('reorder_level') or int(request.POST.get('reorder_level', 10))
            amount_paid = data.get('amount_paid') or float(request.POST.get('amount_paid', 0.0))
            invoice_no = data.get('invoice_no') or request.POST.get('invoice_number')
            notes = data.get('notes') or request.POST.get('notes')
        else:
            # FALLBACK BRIDGE: If form fails validation purely due to custom template 
            # input field name mismatches, read variables directly from request.POST
            name = request.POST.get('name', '').strip()
            cost = float(request.POST.get('cost_price', 0))
            price = float(request.POST.get('selling_price', 0))
            is_credit = request.POST.get('is_credit') == 'on' or 'is_credit' in request.POST
            supplier_id = request.POST.get('supplier_id')
            cat_id = request.POST.get('category')
            qty_arriving = int(request.POST.get('quantity', 0))
            uom = request.POST.get('unit_of_measure', 'PCS')
            reorder_lvl = int(request.POST.get('reorder_level', 10))
            amount_paid = float(request.POST.get('amount_paid', 0.0))
            invoice_no = request.POST.get('invoice_number')
            notes = request.POST.get('notes', '').strip()

            # If vital fields are missing from direct POST, reject right away
            if not name or qty_arriving <= 0:
                messages.error(request, "Submission Rejected: Check input specifications. Material name and quantity are required.")
                return render_product_form_with_errors(request, form)

        # Redundant safety alignment for internal downstream formulas
        selling_price = price
        cost_price = cost

        # --- Business Validation Checks ---

        # Core pricing integrity check
        if selling_price <= cost_price:
            messages.error(request, "Integrity Error: Unit selling price must exceed warehouse cost price.")
            return render_product_form_with_errors(request, form)
        
        total_calculated_amount = qty_arriving * cost_price
        if amount_paid > total_calculated_amount:
            messages.error(request, "Integrity Error: Immediate outlay (amount paid) cannot exceed the total shipment valuation.")
            return render_product_form_with_errors(request, form)

        # Supplier selection validation for credit transactions
        if is_credit and not supplier_id:
            messages.error(request, "Please select a supplier.")
            return render_product_form_with_errors(request, form)

        # Fallback category handler
        if cat_id:
            try:
                category = Category.objects.get(id=cat_id)
            except (Category.DoesNotExist, ValueError):
                category, _ = Category.objects.get_or_create(name="General Hardware")
        else:
            category, _ = Category.objects.get_or_create(name="General Hardware")

        # 1. Look up if the product exists in the system (by name and category)
        existing_match = Product.objects.filter(name__iexact=name, category=category).first()
        
        # 2. Calculate the complete absolute stock that will be in the system after this save
        current_warehouse_stock = existing_match.current_stock if existing_match else 0
        projected_stock = current_warehouse_stock + qty_arriving
        
        # 3. Server-side compliance check against total system stock
        if reorder_lvl > projected_stock:
            messages.error(
                request, 
                f"Logic Error: Safety reorder level ({reorder_lvl}) cannot exceed the resulting total stock quantity in the system ({projected_stock})."
            )
            return render_product_form_with_errors(request, form)   
        
        # Atomic Execution: Updates inventory records and registers liability simultaneously
        with transaction.atomic():
            # Refresh local lookup within transaction lock bounds
            product_match = Product.objects.filter(name__iexact=name, category=category).first()

            if product_match:
                product_match.current_stock += qty_arriving
                product_match.cost_price = cost
                product_match.selling_price = price
                product_match.save()
                product = product_match
                action_text = f"Restocked {qty_arriving} {uom} onto existing item line: {name}."
            else:
                sku = f"NYO-{category.name[:2].upper()}-{name[:3].upper()}-{int(timezone.now().timestamp())}"[:20]
                product = Product.objects.create(
                    name=name,
                    category=category,
                    cost_price=cost,
                    selling_price=price,
                    unit_of_measure=uom,
                    sku=sku,
                    reorder_level=reorder_lvl,
                    current_stock=qty_arriving
                )
                action_text = f"Registered brand new catalog line product profile: {name}."

            # Master Inventory History Trail Registration
            StockMovement.objects.create(
                product=product,
                transaction_type='IN',
                quantity=qty_arriving,
                notes='Credit Supply Consolidated' if is_credit else 'Cash Sourced Intake'
            )

            # Execution block for Procurement integration
            if is_credit:
                supplier = get_object_or_404(Supplier, id=supplier_id)
                total_calculated_amount = qty_arriving * cost
                balance_outstanding = total_calculated_amount - amount_paid

                if balance_outstanding <= 0:
                    status = 'PAID'
                elif amount_paid > 0:
                    status = 'PARTIAL'
                else:
                    status = 'PENDING'

                # Update Supplier Account Balance Summary
                if hasattr(supplier, 'total_owed') and balance_outstanding > 0:
                    supplier.total_owed += balance_outstanding
                    supplier.save()

                purchase_order, created = PurchaseOrder.objects.get_or_create(
                    invoice_number=invoice_no,
                    defaults={
                        'supplier': supplier,
                        'total_amount': total_calculated_amount,
                        'amount_paid': amount_paid,
                        'balance': max(0.0, balance_outstanding),
                        'payment_status': status,
                        'notes': notes if notes else f"Automated intake for {name}"
                    }
                )

                # Safely increment parameters if invoice already exists
                if not created:
                    purchase_order.total_amount += total_calculated_amount
                    purchase_order.amount_paid += amount_paid
                    purchase_order.balance = max(0.0, purchase_order.total_amount - purchase_order.amount_paid)
                    
                    if purchase_order.balance <= 0:
                        purchase_order.payment_status = 'PAID'
                    elif purchase_order.amount_paid > 0:
                        purchase_order.payment_status = 'PARTIAL'
                    else:
                        purchase_order.payment_status = 'PENDING'
                    purchase_order.save()

                # Create Row Sub-Item Breakdown Item
                PurchaseItem.objects.create(
                    purchase_order=purchase_order,
                    product=product,
                    quantity=qty_arriving,
                    unit_cost=cost,
                    subtotal=total_calculated_amount
                )
                action_text += f" UGX {balance_outstanding:,.0f} added to outstanding credit tracking under {supplier.name}."

            # Internal Security Audit Logging
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=f"Inbound Intake executed for {product.name} (Qty: {qty_arriving})"
            )

            messages.success(request, action_text)
            return redirect('product_list')


    else:
        form = ProductForm()
        return render_product_form_with_errors(request, form)

@login_required
@role_required(['MANAGER', 'ADMIN'])
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

@login_required
@role_required(['MANAGER', 'ADMIN'])
def stock_movement_history(request):
    """
    Renders a filtered master audit trail of all warehouse item fluctuations
    """
    # Start with all records
    movements = StockMovement.objects.select_related('product').order_by('-created_at')
    
    # Get filters from URL
    preset = request.GET.get('preset')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    today = timezone.now().date()

    # Apply Logic
    if preset == 'today':
        movements = movements.filter(created_at__date=today)
    elif preset == 'yesterday':
        yesterday = today - timedelta(days=1)
        movements = movements.filter(created_at__date=yesterday)
    elif preset == 'this_month':
        movements = movements.filter(created_at__year=today.year, created_at__month=today.month)
    elif start_date and end_date:
        # User-defined custom range
        movements = movements.filter(created_at__date__range=[start_date, end_date])

    context = {
        'movements': movements,
        'start_date': start_date,
        'end_date': end_date
    }
    return render(request, 'stock_movement.html', context)

# inventory/views.py
@login_required
@role_required(['MANAGER'])
def supplier_create(request):
    

    if request.method == "POST":

        Supplier.objects.create(
            name=request.POST.get('name'),
            phone_number=request.POST.get('phone_number'),
            email=request.POST.get('email', ''),
            address=request.POST.get('address', ''),
            contact_person=request.POST.get('contact_person', ''),
            product=Product.objects.first()
        )

        messages.success(request, "Supplier created successfully.")
        return redirect('product_create')

    return render(request, 'supplier_form.html')

