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
from django.contrib.auth.decorators import login_required

from sales.models import (
    SalesOrder,
    SalesOrderItem,
    
)
from procurement.models import PurchaseOrder
from inventory.models import Product, StockMovement  # Added StockMovement for history
from schemes.models import SchemeDeposit  # Added for scheme collection reporting


# =========================================
# BUSINESS DASHBOARD
# =========================================

@login_required
def business_dashboard(request):

    today = timezone.now().date()

    # =====================================
    # DATE FILTER LOGIC
    # =====================================

    preset = request.GET.get('preset')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sales = SalesOrder.objects.filter(
        status='COMPLETED'
    )
    
    # Active scheme deposits baseline query for date filtering
    scheme_deposits = SchemeDeposit.objects.all()

    # TODAY
    if preset == 'today':
        sales = sales.filter(order_date__date=today)
        scheme_deposits = scheme_deposits.filter(deposited_at__date=today)

    # YESTERDAY
    elif preset == 'yesterday':
        yesterday = today - timedelta(days=1)
        sales = sales.filter(order_date__date=yesterday)
        scheme_deposits = scheme_deposits.filter(deposited_at__date=yesterday)

    # THIS MONTH
    elif preset == 'this_month':
        sales = sales.filter(order_date__month=today.month, order_date__year=today.year)
        scheme_deposits = scheme_deposits.filter(deposited_at__month=today.month, deposited_at__year=today.year)

    # CUSTOM RANGE
    elif start_date and end_date:
        sales = sales.filter(order_date__date__range=[start_date, end_date])
        scheme_deposits = scheme_deposits.filter(deposited_at__date__range=[start_date, end_date])

    # =====================================
    # SALES REPORTS
    # =====================================

    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0

    # REPORT ADDED: Transport Revenue
    total_transport = sales.aggregate(total=Sum('transport_fee'))['total'] or 0

    total_orders = sales.count()

    # =====================================
    # SALES ITEMS
    # =====================================

    sale_items = SalesOrderItem.objects.filter(
        sales_order__in=sales
    )

    total_items_sold = sale_items.aggregate(total=Sum('quantity'))['total'] or 0

    # =====================================
    # PERFORMANCE METRICS (Top & Least Selling)
    # =====================================

    # Top Selling Products
    top_products = sale_items.values(
        'product__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_sales=Sum('subtotal')
    ).order_by('-total_qty')[:5]

    # REPORT ADDED: Least Selling Products (Dead Stock)
    least_selling_products = sale_items.values(
        'product__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_sales=Sum('subtotal')
    ).order_by('total_qty')[:5]

    # REPORT ADDED: Highest Profit Products
    profit_expression = ExpressionWrapper(
        (F('unit_price') - F('product__cost_price')) * F('quantity'),
        output_field=DecimalField()
    )

    highest_profit_products = sale_items.values(
        'product__name'
    ).annotate(
        total_profit=Sum(profit_expression)
    ).order_by('-total_profit')[:5]

    # REPORT ADDED: Profit Trends (Overall Period Estimated Profit)
    estimated_profit = sale_items.aggregate(
        total=Sum(profit_expression)
    )['total'] or 0

    # =====================================
    # REPORT ADDED: CASHIER PERFORMANCE
    # =====================================

    cashier_performance = sales.values(
        'served_by__username'
    ).annotate(
        total_sales_generated=Sum('total_amount'),
        tickets_closed=Count('id')
    ).order_by('-total_sales_generated')

    # =====================================
    # REPORT ADDED: BEST CUSTOMERS
    # =====================================

    best_customers = sales.values('customer__name').annotate(
        total_spent=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('-total_spent')[:5]

    # =====================================
    # REPORT ADDED: SCHEME COLLECTIONS
    # =====================================

    scheme_collections_total = scheme_deposits.aggregate(
        total=Sum('amount')
    )['total'] or 0

    # =====================================
    # REPORT ADDED: UNPAID SUPPLIERS
    # =====================================

    unpaid_supplier_orders = PurchaseOrder.objects.filter(
       balance__gt=0
    ).select_related('supplier').order_by('-balance')

    supplier_debt = unpaid_supplier_orders.aggregate(
        total=Sum('balance')
    )['total'] or 0

    # =====================================
    # INVENTORY VALUE
    # =====================================

    inventory = Product.objects.all()

    stock_value = sum(
        product.current_stock * product.cost_price
        for product in inventory
    )

    low_stock_items = Product.objects.filter(
        current_stock__lte=F('reorder_level')
    )

    # =====================================
    # REPORT ADDED: STOCK MOVEMENT HISTORY
    # =====================================

    recent_stock_movements = StockMovement.objects.all().select_related(
        'product'
    ).order_by('-moved_at')[:10]  # Pulls last 10 audit details

    # =====================================
    # CONTEXT
    # =====================================

    context = {
        'sales': sales,
        'total_revenue': total_revenue,
        'transport_total': total_transport,
        'total_orders': total_orders,
        'total_items_sold': total_items_sold,
        'supplier_debt': supplier_debt,
        'stock_value': stock_value,
        'low_stock_items': low_stock_items,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
        
        # New Expanded Context Metrics Passed to Dashboard Template
        'top_products': top_products,
        'least_selling_products': least_selling_products,
        'highest_profit_products': highest_profit_products,
        'estimated_profit': estimated_profit,
        'cashier_performance': cashier_performance,
        'best_customers': best_customers,
        'scheme_collections_total': scheme_collections_total,
        'unpaid_supplier_orders': unpaid_supplier_orders,
        'recent_stock_movements': recent_stock_movements,
    }

    return render(
        request,
        'reports/dashboard.html',
        context
    )


# =========================================
# FINANCIAL STATEMENT
# =========================================

def financial_statement_view(request):

    completed_sales = SalesOrder.objects.filter(
        status='COMPLETED'
    )

    # =====================================
    # TOTAL SALES
    # =====================================

    total_sales = completed_sales.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # =====================================
    # COST OF GOODS SOLD
    # =====================================

    sale_items = SalesOrderItem.objects.filter(
        sales_order__status='COMPLETED'
    )

    cogs_expression = ExpressionWrapper(
        F('product__cost_price') * F('quantity'),
        output_field=DecimalField()
    )

    cogs = sale_items.aggregate(
        total=Sum(cogs_expression)
    )['total'] or 0

    # =====================================
    # GROSS PROFIT
    # =====================================

    gross_profit = total_sales - cogs

    # =====================================
    # TRANSPORT INCOME
    # =====================================

    transport_income = completed_sales.aggregate(
        total=Sum('transport_fee')
    )['total'] or 0

    # =====================================
    # NET PROFIT ESTIMATE
    # =====================================

    net_profit = gross_profit + transport_income

    context = {
        'total_sales': total_sales,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'transport_income': transport_income,
        'net_profit': net_profit
    }

    return render(
        request,
        'reports/financial_statement.html',
        context
    )