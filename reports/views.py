from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import (
    Sum,
    F,
    Count,
    DecimalField,
    ExpressionWrapper)
from .forms import ExpenseForm
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from decimal import Decimal
from django.contrib.auth import get_user_model

from sales.models import SalesOrder, SalesOrderItem
from procurement.models import PurchaseOrder
from inventory.models import Product, StockMovement 
from schemes.models import SavingsScheme
from .models import Expense


User = get_user_model()


# ROLE PROTECTION HELPER FUNCTIONS

def is_admin_only(user):
    """Restricts deep financial records and system dashboard metrics strictly to Accounts/Admin profiles."""
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_superuser)


# DATE FILTER HELPER UTILITY

def apply_date_filters(request, sales_queryset, scheme_queryset=None):
    """
    Helper utility to ensure date preset filters work uniformly 
    across all individual sub-report view sheets.
    """
    today = timezone.now().date()
    preset = request.GET.get('preset')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if preset == 'today':
        sales_queryset = sales_queryset.filter(order_date__date=today)
        if scheme_queryset is not None:
            scheme_queryset = scheme_queryset.filter(deposited_at__date=today)
            
    elif preset == 'yesterday':
        yesterday = today - timedelta(days=1)
        sales_queryset = sales_queryset.filter(order_date__date=yesterday)
        if scheme_queryset is not None:
            scheme_queryset = scheme_queryset.filter(deposited_at__date=yesterday)
            
    elif preset == 'this_month':
        sales_queryset = sales_queryset.filter(order_date__month=today.month, order_date__year=today.year)
        if scheme_queryset is not None:
            scheme_queryset = scheme_queryset.filter(deposited_at__month=today.month, deposited_at__year=today.year)
            
    elif start_date and end_date:
        sales_queryset = sales_queryset.filter(order_date__date__range=[start_date, end_date])
        if scheme_queryset is not None:
            scheme_queryset = scheme_queryset.filter(deposited_at__date__range=[start_date, end_date])

    return sales_queryset, scheme_queryset, today, start_date, end_date


# CORE VIEWS AND SUB-REPORTS
# 1. MAKE SURE SAVINGS SCHEME IS IMPORTED AT THE TOP of reports/views.py


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def business_dashboard(request):
    """Polished Executive Control Panel providing unified financial telemetry and metrics."""
    completed_sales = SalesOrder.objects.filter(status='COMPLETED')
    
    # Existing calculations
    total_revenue = completed_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_transport = completed_sales.aggregate(total=Sum('transport_fee'))['total'] or Decimal('0.00')
    
    products = Product.objects.all()
    stock_valuation = sum(p.current_stock * p.selling_price for p in products)
    
    # FIX 1: Fetch items for lower safety threshold warning banner
    low_stock_items = Product.objects.filter(current_stock__lte=F('reorder_level'))
    low_stock_count = low_stock_items.count()
    total_staff = User.objects.count()
    
    recent_orders = SalesOrder.objects.all().select_related('customer').order_by('-order_date')[:5]

    # FIX 2: Compute Live Supplier Credit Owed (Debt Card)
    supplier_debt = PurchaseOrder.objects.filter(balance__gt=0).aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

    # FIX 3: Compute Customer Savings Balance (Held Card)
    scheme_collections_total = SavingsScheme.objects.aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')

    # FIX 4: Compute Period Net Profit (Estimated Profit Card)
    sale_items = SalesOrderItem.objects.filter(sales_order__in=completed_sales)
    cogs_expression = ExpressionWrapper(
        F('product__cost_price') * F('quantity'),
        output_field=DecimalField()
    )
    cogs = sale_items.aggregate(total=Sum(cogs_expression))['total'] or Decimal('0.00')
    gross_profit = total_revenue - cogs
    estimated_profit = gross_profit + total_transport

    # Pass all variables directly to match your template keys perfectly
    context = {
        'total_revenue': total_revenue,
        'stock_valuation': stock_valuation,
        'low_stock_count': low_stock_count,
        'low_stock_items': low_stock_items,  # Added to make the warning banner active!
        'total_staff': total_staff,
        'recent_orders': recent_orders,
        'total_transport': total_transport,
        'supplier_debt': supplier_debt,                       # Match Card 1
        'scheme_collections_total': scheme_collections_total, # Match Card 2
        'estimated_profit': estimated_profit,                 # Match Card 3
    }
    return render(request, 'reports/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def unpaid_supplier_view(request):
    # FIXED: Using 'purchaseitem_set' to prefetch child rows and their respective products
    unpaid_supplier_orders = PurchaseOrder.objects.filter(balance__gt=0)\
        .select_related('supplier')\
        .prefetch_related('purchaseitem_set__product')\
        .order_by('-balance')
        
    supplier_debt = unpaid_supplier_orders.aggregate(total=Sum('balance'))['total'] or 0

    context = {
        'unpaid_supplier_orders': unpaid_supplier_orders,
        'supplier_debt': supplier_debt
    }
    return render(request, 'reports/unpaid_supplier.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def cashier_performance_view(request):
    sales = SalesOrder.objects.filter(status='COMPLETED')
    sales, _, today, start_date, end_date = apply_date_filters(request, sales)

    cashier_performance = sales.values('served_by__username').annotate(
        total_sales_generated=Sum('total_amount'),
        tickets_closed=Count('id')
    ).order_by('-total_sales_generated')

    context = {
        'cashier_performance': cashier_performance,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/cashier_performance.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def stock_history_view(request):
    recent_stock_movements = StockMovement.objects.all().select_related('product').order_by('-created_at')
    low_stock_items = Product.objects.filter(current_stock__lte=F('reorder_level'))

    context = {
        'recent_stock_movements': recent_stock_movements,
        'low_stock_items': low_stock_items
    }
    return render(request, 'reports/stock_history.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def highest_profit_view(request):
    sales = SalesOrder.objects.filter(status='COMPLETED')
    sales, _, today, start_date, end_date = apply_date_filters(request, sales)
    
    sale_items = SalesOrderItem.objects.filter(sales_order__in=sales)
    profit_expression = ExpressionWrapper(
        (F('unit_price') - F('product__cost_price')) * F('quantity'),
        output_field=DecimalField()
    )

    highest_profit_products = sale_items.values('product__name').annotate(
        total_profit=Sum(profit_expression),
        total_qty=Sum('quantity')
    ).order_by('-total_profit')

    context = {
        'highest_profit_products': highest_profit_products,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/highest_profit.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def least_selling_view(request):
    sales = SalesOrder.objects.filter(status='COMPLETED')
    sales, _, today, start_date, end_date = apply_date_filters(request, sales)

    sale_items = SalesOrderItem.objects.filter(sales_order__in=sales)
    least_selling_products = sale_items.values('product__name').annotate(
        total_qty=Sum('quantity'),
        total_sales=Sum('subtotal')
    ).order_by('total_qty')

    context = {
        'least_selling_products': least_selling_products,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/least_selling.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def transport_revenue_view(request):
    sales = SalesOrder.objects.filter(status='COMPLETED')
    sales, _, today, start_date, end_date = apply_date_filters(request, sales)

    total_transport = sales.aggregate(total=Sum('transport_fee'))['total'] or 0
    transport_orders = sales.filter(transport_fee__gt=0).order_by('-order_date')

    context = {
        'transport_orders': transport_orders,
        'transport_total': total_transport,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/transport_revenue.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def reports_index_view(request):
    return render(request, 'reports/reports_index.html')

@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def general_sales_report(request):
    sales = SalesOrder.objects.filter(status='COMPLETED')
    sales, _, today, start_date, end_date = apply_date_filters(request, sales)

    # Aggregate performance by product
    sales_data = SalesOrderItem.objects.filter(sales_order__in=sales).values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('subtotal'),
        transaction_count=Count('sales_order')
    ).order_by('-total_revenue')

    total_gross_revenue = sales_data.aggregate(total=Sum('total_revenue'))['total'] or 0

    context = {
        'sales_data': sales_data,
        'total_gross_revenue': total_gross_revenue,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/general_sales.html', context)

@login_required
def log_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, "Expense successfully logged to the ledger.")
            return redirect('financial_statement')
    else:
        form = ExpenseForm()
    
    return render(request, 'reports/log_expenses.html', {'form': form})

# reports/views.py

@login_required
@user_passes_test(is_admin_only, login_url='product_list')
def financial_statement_view(request):
    # 1. Filter Sales
    sales = SalesOrder.objects.filter(status='COMPLETED')
    sales, _, today, start_date, end_date = apply_date_filters(request, sales)
    
    # 2. Calculate Financials
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    transport_income = sales.aggregate(total=Sum('transport_fee'))['total'] or 0
    
    # 3. Calculate COGS
    cogs = SalesOrderItem.objects.filter(sales_order__in=sales).aggregate(
        total=Sum(ExpressionWrapper(F('product__cost_price') * F('quantity'), output_field=DecimalField()))
    )['total'] or 0
    
    # 4. Filter Expenses by the same date range
    expenses = Expense.objects.all()
    if start_date and end_date:
        expenses = expenses.filter(date_incurred__range=[start_date, end_date])
    elif request.GET.get('preset') == 'today':
        expenses = expenses.filter(date_incurred=today)
    elif request.GET.get('preset') == 'this_month':
        expenses = expenses.filter(date_incurred__month=today.month, date_incurred__year=today.year)
        
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # 5. Result Calculations
    gross_profit = total_revenue - cogs
    net_profit = (gross_profit + transport_income) - total_expenses
    
    context = {
        'total_revenue': total_revenue,
        'transport_income': transport_income,
        'cogs': cogs,
        'total_expenses': total_expenses,
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'today': today,
        'start_date': start_date,
        'end_date': end_date
    }
    return render(request, 'reports/financial_statement.html', context)