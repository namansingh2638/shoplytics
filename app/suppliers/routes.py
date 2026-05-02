from app.utils import admin_required
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app import db
from app.models import Supplier, Purchase, Product
from app.suppliers import bp

def get_org_id():
    return session.get('org_id')


# --- Supplier Routes ---

@bp.route('/')
@login_required
@admin_required
def index():
    org_id = get_org_id()
    suppliers = Supplier.query.filter_by(org_id=org_id).all()
    return render_template('suppliers/index.html', suppliers=suppliers)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_supplier():
    org_id = get_org_id()

    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']

        supplier = Supplier(name=name, contact=contact, org_id=org_id)
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added!')
        return redirect(url_for('suppliers.index'))

    return render_template('suppliers/add_supplier.html')


@bp.route('/delete/<int:supplier_id>')
@login_required
@admin_required
def delete_supplier(supplier_id):
    org_id = get_org_id()
    supplier = Supplier.query.filter_by(id=supplier_id, org_id=org_id).first_or_404()
    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted.')
    return redirect(url_for('suppliers.index'))


# --- Purchase Routes ---

@bp.route('/purchases')
@login_required
@admin_required
def purchases():
    org_id = get_org_id()
    purchases = Purchase.query.filter_by(org_id=org_id).order_by(Purchase.date.desc()).all()
    return render_template('suppliers/purchases.html', purchases=purchases)


@bp.route('/purchases/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_purchase():
    org_id = get_org_id()
    suppliers = Supplier.query.filter_by(org_id=org_id).all()
    products = Product.query.filter_by(org_id=org_id).all()

    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        cost_price = float(request.form['cost_price'])

        # Record the purchase
        purchase = Purchase(
            supplier_id=supplier_id,
            product_id=product_id,
            quantity=quantity,
            cost_price=cost_price,
            org_id=org_id
        )
        db.session.add(purchase)

        # Update the product stock
        product = Product.query.get(int(product_id))

        new_avg_cost = (
            (product.stock_quantity * product.cost_price) + (quantity * cost_price)
        ) / (product.stock_quantity + quantity)

        product.cost_price = round(new_avg_cost, 2)
        product.stock_quantity += quantity

        db.session.commit()
        flash(f'Purchase recorded! {quantity} units added to stock.')
        return redirect(url_for('suppliers.purchases'))

    return render_template('suppliers/add_purchase.html',
                           suppliers=suppliers, products=products)