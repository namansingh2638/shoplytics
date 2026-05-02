from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app import db
from app.models import Expense
from app.expenses import bp
from app.utils import admin_required


def get_org_id():
    return session.get('org_id')


@bp.route('/')
@login_required
@admin_required
def index():
    org_id = get_org_id()
    expenses = Expense.query.filter_by(org_id=org_id).order_by(Expense.date.desc()).all()

    total = sum(e.amount for e in expenses)

    return render_template('expenses/index.html', expenses=expenses, total=total)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_expense():
    org_id = get_org_id()

    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        note = request.form.get('note', '')

        expense = Expense(
            amount=amount,
            category=category,
            note=note,
            org_id=org_id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense recorded!')
        return redirect(url_for('expenses.index'))

    return render_template('expenses/add_expense.html')


@bp.route('/delete/<int:expense_id>')
@login_required
@admin_required
def delete_expense(expense_id):
    org_id = get_org_id()
    expense = Expense.query.filter_by(id=expense_id, org_id=org_id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.')
    return redirect(url_for('expenses.index'))