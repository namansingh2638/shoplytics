from app.utils import admin_required
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category
from app.inventory import bp


def get_org_id():
    return session.get('org_id')


@bp.route('/')
@login_required
def index():
    org_id = get_org_id()
    products = Product.query.filter_by(org_id=org_id).all()
    return render_template('inventory/index.html', products=products)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    org_id = get_org_id()
    categories = Category.query.filter_by(org_id=org_id).all()

    if request.method == 'POST':
        name = request.form['name']
        barcode = request.form['barcode']
        cost_price = float(request.form['cost_price'])
        selling_price = float(request.form['selling_price'])
        stock_quantity = int(request.form['stock_quantity'])
        category_id = request.form.get('category_id') or None

        existing = Product.query.filter_by(name=name, org_id=org_id).first()
        if existing:
            flash(f'Product "{name}" already exists. Use the Purchase module to restock or Edit to update details.')
            return redirect(url_for('inventory.add_product'))

        product = Product(
            name=name,
            barcode=barcode or None,
            cost_price=cost_price,
            selling_price=selling_price,
            stock_quantity=stock_quantity,
            category_id=category_id,
            org_id=org_id
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!')
        return redirect(url_for('inventory.index'))

    return render_template('inventory/add_product.html', categories=categories)


@bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    org_id = get_org_id()
    product = Product.query.filter_by(id=product_id, org_id=org_id).first_or_404()
    categories = Category.query.filter_by(org_id=org_id).all()

    if request.method == 'POST':
        product.name = request.form['name']
        product.barcode = request.form['barcode'] or None
        product.cost_price = float(request.form['cost_price'])
        product.selling_price = float(request.form['selling_price'])
        product.stock_quantity = int(request.form['stock_quantity'])
        product.category_id = request.form.get('category_id') or None

        db.session.commit()
        flash('Product updated!')
        return redirect(url_for('inventory.index'))

    return render_template('inventory/edit_product.html', product=product, categories=categories)


@bp.route('/delete/<int:product_id>')
@login_required
@admin_required
def delete_product(product_id):
    org_id = get_org_id()
    product = Product.query.filter_by(id=product_id, org_id=org_id).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.')
    return redirect(url_for('inventory.index'))


# --- Category routes ---

@bp.route('/categories')
@login_required
def categories():
    org_id = get_org_id()
    cats = Category.query.filter_by(org_id=org_id).all()
    return render_template('inventory/categories.html', categories=cats)


@bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    org_id = get_org_id()

    if request.method == 'POST':
        name = request.form['name']
        cat = Category(name=name, org_id=org_id)
        db.session.add(cat)
        db.session.commit()
        flash('Category added!')
        return redirect(url_for('inventory.categories'))

    return render_template('inventory/add_category.html')