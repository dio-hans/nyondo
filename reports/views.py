from django.shortcuts import render
from django.db.models import (
    Sum,
    F,
    Count,
    DecimalField,
    ExpressionWrapper
)
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from decimal import Decimal
from django.contrib.auth import get_user_model

from sales.models import SalesOrder, SalesOrderItem
from procurement.models import PurchaseOrder
from inventory.models import Product, StockMovement 
from schemes.models import SchemeDeposit 

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

@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def business_dashboard(request):
    """Polished Executive Control Panel providing unified financial telemetry and metrics."""
    completed_sales = SalesOrder.objects.filter(status='COMPLETED')
    total_revenue = completed_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_transport = completed_sales.aggregate(total=Sum('transport_fee'))['total'] or Decimal('0.00')
    
    products = Product.objects.all()
    stock_valuation = sum(p.current_stock * p.selling_price for p in products)
    
    low_stock_count = Product.objects.filter(current_stock__lte=10).count()
    total_staff = User.objects.count()
    
    recent_orders = SalesOrder.objects.all().select_related('customer').order_by('-order_date')[:5]

    context = {
        'total_revenue': total_revenue,
        'stock_valuation': stock_valuation,
        'low_stock_count': low_stock_count,
        'total_staff': total_staff,
        'recent_orders': recent_orders,
        'total_transport': total_transport,
    }
    return render(request, 'reports/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def financial_statement_view(request):
    completed_sales = SalesOrder.objects.filter(status='COMPLETED')
    
    completed_sales, _, today, start_date, end_date = apply_date_filters(request, completed_sales)

    total_sales = completed_sales.aggregate(total=Sum('total_amount'))['total'] or 0

    sale_items = SalesOrderItem.objects.filter(sales_order__in=completed_sales)
    cogs_expression = ExpressionWrapper(
        F('product__cost_price') * F('quantity'),
        output_field=DecimalField()
    )
    cogs = sale_items.aggregate(total=Sum(cogs_expression))['total'] or 0

    gross_profit = total_sales - cogs
    transport_income = completed_sales.aggregate(total=Sum('transport_fee'))['total'] or 0
    net_profit = gross_profit + transport_income

    context = {
        'total_sales': total_sales,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'transport_income': transport_income,
        'net_profit': net_profit,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/financial_statement.html', context)


@login_required
@user_passes_test(is_admin_only, login_url='product_list', redirect_field_name=None)
def unpaid_supplier_view(request):
    unpaid_supplier_orders = PurchaseOrder.objects.filter(balance__gt=0).select_related('supplier').order_by('-balance')
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