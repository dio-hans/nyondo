from django.shortcuts import render, redirect
from django.contrib import messages

from django.db import transaction
from django.db.models import Sum

from .models import (
    Supplier,
    PurchaseOrder,
    PurchaseItem
)

from inventory.models import (
    Product,
    StockMovement
)


# RECORD PURCHASE

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

    return render(

        request,

        'procurement/add_purchase.html',

        context

    )


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

    return render(

        request,

        'procurement/debt_list.html',

        context

    )
