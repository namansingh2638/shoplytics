from flask import render_template, session
from flask_login import login_required
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
from sqlalchemy import func
from app import db
from app.models import Transaction, TransactionItem, Expense, Product
from app.main import bp
from app.utils import admin_required
from app.models import Organization
from flask import render_template, session, request
from flask import redirect, url_for, flash, render_template

def get_org_id():
    return session.get('org_id')


def calc_daily_profit(org_id, date):
    # Total revenue collected today
    daily_transactions = Transaction.query.filter(
        Transaction.org_id == org_id,
        func.date(Transaction.date) == date
    ).all()
    revenue = sum(t.total_amount for t in daily_transactions)

    # Total cost of goods sold today
    items = db.session.query(TransactionItem).join(Transaction).filter(
        Transaction.org_id == org_id,
        func.date(Transaction.date) == date
    ).all()
    cogs = sum(Product.query.get(item.product_id).cost_price * item.quantity
               for item in items
               if Product.query.get(item.product_id))

    return round(revenue - cogs, 2)

def calc_monthly_cogs(org_id, from_date):
    """
    Monthly COGS = sum of (cost_price * quantity) for all items sold this month
    """
    items = db.session.query(TransactionItem).join(Transaction).filter(
        Transaction.org_id == org_id,
        Transaction.date >= from_date
    ).all()

    cogs = 0
    for item in items:
        product = Product.query.get(item.product_id)
        if product:
            cogs += product.cost_price * item.quantity

    return round(cogs, 2)


@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    org_id = get_org_id()
    today = datetime.now(IST).date()
    first_of_month = today.replace(day=1)

    # --- Daily Sales ---
    daily_transactions = Transaction.query.filter(
        Transaction.org_id == org_id,
        func.date(Transaction.date) == today
    ).all()
    daily_sales = sum(t.total_amount for t in daily_transactions)

    # --- Daily Profit (margin on goods sold only) ---
    daily_profit = calc_daily_profit(org_id, today)

    # --- Monthly Sales ---
    monthly_transactions = Transaction.query.filter(
        Transaction.org_id == org_id,
        Transaction.date >= first_of_month
    ).all()
    monthly_sales = sum(t.total_amount for t in monthly_transactions)

    # --- Monthly Expenses (rent, electricity etc.) ---
    monthly_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.org_id == org_id,
        Expense.date >= first_of_month
    ).scalar() or 0

    # --- Monthly COGS ---
    monthly_cogs = calc_monthly_cogs(org_id, first_of_month)

    # --- Monthly Profit (full picture) ---
    monthly_profit = round(monthly_sales - monthly_cogs - monthly_expenses, 2)

    # --- Low Stock Alert ---
    low_stock = Product.query.filter(
        Product.org_id == org_id,
        Product.stock_quantity < 5
    ).all()

    # --- Top 5 Products ---
    top_products = db.session.query(
        Product.name,
        func.sum(TransactionItem.quantity).label('total_sold')
    ).join(TransactionItem, TransactionItem.product_id == Product.id)\
     .filter(Product.org_id == org_id)\
     .group_by(Product.id)\
     .order_by(func.sum(TransactionItem.quantity).desc())\
     .limit(5).all()

    return render_template('main/dashboard.html',
        daily_sales=daily_sales,
        daily_profit=daily_profit,
        monthly_sales=monthly_sales,
        monthly_expenses=monthly_expenses,
        monthly_cogs=monthly_cogs,
        monthly_profit=monthly_profit,
        low_stock=low_stock,
        top_products=top_products
    )


@bp.route('/reports')
@login_required
@admin_required
def reports():
    org_id = get_org_id()
    today = datetime.now(IST).date()
    first_of_month = today.replace(day=1)
    seven_days_ago = today - timedelta(days=7)

    # --- Last 7 days ---
    recent_transactions = Transaction.query.filter(
        Transaction.org_id == org_id,
        Transaction.date >= seven_days_ago
    ).order_by(Transaction.date.desc()).all()

    # --- This month's transactions ---
    monthly_transactions = Transaction.query.filter(
        Transaction.org_id == org_id,
        Transaction.date >= first_of_month
    ).order_by(Transaction.date.desc()).all()

    # --- Monthly breakdown numbers ---
    monthly_sales = sum(t.total_amount for t in monthly_transactions)
    monthly_cogs = calc_monthly_cogs(org_id, first_of_month)

    monthly_expenses_list = Expense.query.filter(
        Expense.org_id == org_id,
        Expense.date >= first_of_month
    ).order_by(Expense.date.desc()).all()
    monthly_expenses_total = sum(e.amount for e in monthly_expenses_list)

    # Expenses broken down by category
    expense_by_category = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.org_id == org_id,
        Expense.date >= first_of_month
    ).group_by(Expense.category).all()

    monthly_profit = round(monthly_sales - monthly_cogs - monthly_expenses_total, 2)

    return render_template('main/reports.html',
        recent_transactions=recent_transactions,
        monthly_transactions=monthly_transactions,
        monthly_sales=monthly_sales,
        monthly_cogs=monthly_cogs,
        monthly_expenses_list=monthly_expenses_list,
        monthly_expenses_total=monthly_expenses_total,
        expense_by_category=expense_by_category,
        monthly_profit=monthly_profit,
        today=today
    )

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    org_id = get_org_id()
    org = Organization.query.get(org_id)

    if request.method == 'POST':
        org.open_hour = int(request.form['open_hour'])
        org.close_hour = int(request.form['close_hour'])
        db.session.commit()
        flash('Settings updated!')
        return redirect(url_for('main.settings'))

    return render_template('main/settings.html', org=org)