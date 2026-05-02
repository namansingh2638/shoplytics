from flask import render_template, session
from flask_login import login_required
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import func
from app import db
from app.models import (Product, Transaction, TransactionItem,
                        Expense, Purchase, Supplier, Category, Organization)
from app.analytics import bp
from app.utils import admin_required

IST = ZoneInfo("Asia/Kolkata")


def get_org_id():
    return session.get('org_id')


# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def get_sales_data(org_id, days=30):
    """Returns daily sales totals for last N days as a dict {date: amount}"""
    since = datetime.now(IST).date() - timedelta(days=days)
    transactions = Transaction.query.filter(
        Transaction.org_id == org_id,
        Transaction.date >= since
    ).all()

    daily = {}
    for t in transactions:
        d = t.date.date() if hasattr(t.date, 'date') else t.date
        daily[d] = daily.get(d, 0) + t.total_amount

    # Fill in missing days with 0
    result = {}
    for i in range(days):
        d = datetime.now(IST).date() - timedelta(days=days - 1 - i)
        result[d] = round(daily.get(d, 0), 2)

    return result


def get_hourly_sales(org_id, open_hour, close_hour, days=30):
    """Returns total sales per hour within working hours"""
    since = datetime.now(IST).date() - timedelta(days=days)
    transactions = Transaction.query.filter(
        Transaction.org_id == org_id,
        Transaction.date >= since
    ).all()

    hourly = {h: 0 for h in range(open_hour, close_hour)}

    for t in transactions:
        hour = t.date.hour
        if open_hour <= hour < close_hour:
            hourly[hour] = round(hourly.get(hour, 0) + t.total_amount, 2)

    return hourly


def get_dead_hours(hourly_sales):
    """
    Dead hours = hours where sales are below average
    OR in bottom 25% of all hourly sales
    """
    values = list(hourly_sales.values())
    if not any(values):
        return [], None

    avg = sum(values) / len(values)
    sorted_vals = sorted(values)
    q1_index = len(sorted_vals) // 4
    q1_threshold = sorted_vals[q1_index]

    dead = []
    for hour, sales in hourly_sales.items():
        if sales < avg or sales <= q1_threshold:
            dead.append(hour)

    lowest_hour = min(hourly_sales, key=hourly_sales.get)
    return dead, lowest_hour


def get_profit_per_product(org_id):
    """Returns profit per product based on avg cost vs selling price * qty sold"""
    items = db.session.query(
        Product.id,
        Product.name,
        Product.cost_price,
        func.sum(TransactionItem.quantity).label('qty_sold'),
        func.sum(TransactionItem.quantity * TransactionItem.price).label('revenue')
    ).join(TransactionItem, TransactionItem.product_id == Product.id)\
     .filter(Product.org_id == org_id)\
     .group_by(Product.id).all()

    result = []
    for item in items:
        cogs = item.cost_price * item.qty_sold
        profit = round(item.revenue - cogs, 2)
        result.append({
            'name': item.name,
            'qty_sold': item.qty_sold,
            'revenue': round(item.revenue, 2),
            'profit': profit
        })

    return sorted(result, key=lambda x: x['profit'], reverse=True)


def get_profit_per_category(org_id):
    """Returns profit grouped by category"""
    items = db.session.query(
        Category.name,
        func.sum(TransactionItem.quantity * TransactionItem.price).label('revenue'),
        func.sum(TransactionItem.quantity * Product.cost_price).label('cogs')
    ).join(Product, Product.id == TransactionItem.product_id)\
     .join(Category, Category.id == Product.category_id)\
     .join(Transaction, Transaction.id == TransactionItem.transaction_id)\
     .filter(Transaction.org_id == org_id)\
     .group_by(Category.id).all()

    result = []
    for item in items:
        profit = round((item.revenue or 0) - (item.cogs or 0), 2)
        result.append({
            'category': item.name,
            'revenue': round(item.revenue or 0, 2),
            'profit': profit
        })

    return sorted(result, key=lambda x: x['profit'], reverse=True)


def get_dead_stock(org_id, days=30):
    """Products not sold in last X days"""
    since = datetime.now(IST).date() - timedelta(days=days)

    sold_ids = db.session.query(TransactionItem.product_id)\
        .join(Transaction)\
        .filter(
            Transaction.org_id == org_id,
            Transaction.date >= since
        ).distinct().all()

    sold_ids = [s[0] for s in sold_ids]

    dead = Product.query.filter(
        Product.org_id == org_id,
        Product.stock_quantity > 0,
        ~Product.id.in_(sold_ids)
    ).all()

    return dead


def get_supplier_analytics(org_id):
    """Total purchases per supplier"""
    result = db.session.query(
        Supplier.name,
        func.count(Purchase.id).label('total_orders'),
        func.sum(Purchase.quantity * Purchase.cost_price).label('total_spent')
    ).join(Purchase, Purchase.supplier_id == Supplier.id)\
     .filter(Supplier.org_id == org_id)\
     .group_by(Supplier.id)\
     .order_by(func.sum(Purchase.quantity * Purchase.cost_price).desc()).all()

    return result


def get_avg_daily_sales(org_id, days=30):
    """Simple average daily sales for prediction"""
    sales_data = get_sales_data(org_id, days)
    values = [v for v in sales_data.values() if v > 0]
    if not values:
        return 0
    return round(sum(values) / len(values), 2)


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@bp.route('/')
@login_required
@admin_required
def index():
    org_id = get_org_id()
    org = Organization.query.get(org_id)
    today = datetime.now(IST).date()
    first_of_month = today.replace(day=1)

    # --- Sales ---
    sales_data = get_sales_data(org_id, days=30)
    daily_labels = [d.strftime('%d %b') for d in sales_data.keys()]
    daily_values = list(sales_data.values())

    today_sales = sales_data.get(today, 0)
    monthly_sales = sum(
        t.total_amount for t in Transaction.query.filter(
            Transaction.org_id == org_id,
            Transaction.date >= first_of_month
        ).all()
    )
    transaction_count = Transaction.query.filter(
        Transaction.org_id == org_id,
        Transaction.date >= first_of_month
    ).count()

    # --- Hourly / Dead Hours ---
    hourly_sales = get_hourly_sales(org_id, org.open_hour, org.close_hour)
    dead_hours, lowest_hour = get_dead_hours(hourly_sales)
    hourly_labels = [f"{h}:00" for h in hourly_sales.keys()]
    hourly_values = list(hourly_sales.values())

    # --- Profit per product ---
    product_profits = get_profit_per_product(org_id)

    # --- Profit per category ---
    category_profits = get_profit_per_category(org_id)
    cat_labels = [c['category'] for c in category_profits]
    cat_values = [c['revenue'] for c in category_profits]

    # --- Inventory Intelligence ---
    low_stock = Product.query.filter(
        Product.org_id == org_id,
        Product.stock_quantity > 0,
        Product.stock_quantity < 5
    ).all()
    out_of_stock = Product.query.filter_by(org_id=org_id, stock_quantity=0).all()
    dead_stock = get_dead_stock(org_id, days=30)

    # --- Supplier Analytics ---
    supplier_analytics = get_supplier_analytics(org_id)

    # --- Prediction ---
    avg_daily_sales = get_avg_daily_sales(org_id)
    predicted_weekly = round(avg_daily_sales * 7, 2)
    predicted_monthly = round(avg_daily_sales * 30, 2)

    # --- Top Products ---
    top_by_qty = sorted(product_profits, key=lambda x: x['qty_sold'], reverse=True)[:5]
    top_by_revenue = sorted(product_profits, key=lambda x: x['revenue'], reverse=True)[:5]

    return render_template('analytics/index.html',
        # sales
        daily_labels=daily_labels,
        daily_values=daily_values,
        today_sales=today_sales,
        monthly_sales=monthly_sales,
        transaction_count=transaction_count,
        # hourly
        hourly_labels=hourly_labels,
        hourly_values=hourly_values,
        dead_hours=[f"{h}:00 - {h+1}:00" for h in dead_hours],
        lowest_hour=f"{lowest_hour}:00 - {lowest_hour+1}:00" if lowest_hour is not None else "N/A",
        # profit
        product_profits=product_profits[:10],
        category_profits=category_profits,
        cat_labels=cat_labels,
        cat_values=cat_values,
        # inventory
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        dead_stock=dead_stock,
        # suppliers
        supplier_analytics=supplier_analytics,
        # prediction
        avg_daily_sales=avg_daily_sales,
        predicted_weekly=predicted_weekly,
        predicted_monthly=predicted_monthly,
        # top
        top_by_qty=top_by_qty,
        top_by_revenue=top_by_revenue,
        org=org
    )