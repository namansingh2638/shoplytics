from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app import db
from app.models import Product, Transaction, TransactionItem
from app.billing import bp


def get_org_id():
    return session.get('org_id')


def get_cart():
    # Cart is stored in session as a dict {product_id: quantity}
    return session.get('cart', {})


def save_cart(cart):
    session['cart'] = cart
    session.modified = True  # tells Flask the session was changed


@bp.route('/')
@login_required
def index():
    org_id = get_org_id()
    cart = get_cart()

    # Build cart details from product IDs in session
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.filter_by(id=int(product_id), org_id=org_id).first()
        if product:
            subtotal = product.selling_price * quantity
            total += subtotal
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })

    return render_template('billing/index.html', cart_items=cart_items, total=total)


@bp.route('/search')
@login_required
def search():
    org_id = get_org_id()
    query = request.args.get('q', '')
    products = []

    if query:
        products = Product.query.filter(
            Product.org_id == org_id,
            (Product.name.ilike(f'%{query}%') | Product.barcode.ilike(f'%{query}%'))
        ).all()

    return render_template('billing/search.html', products=products, query=query)


@bp.route('/add/<int:product_id>')
@login_required
def add_to_cart(product_id):
    cart = get_cart()
    key = str(product_id)  # session keys must be strings

    cart[key] = cart.get(key, 0) + 1
    save_cart(cart)

    flash('Product added to cart.')
    return redirect(url_for('billing.index'))


@bp.route('/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    cart = get_cart()
    key = str(product_id)
    quantity = int(request.form['quantity'])

    if quantity <= 0:
        cart.pop(key, None)  # remove from cart if quantity is 0
    else:
        cart[key] = quantity

    save_cart(cart)
    return redirect(url_for('billing.index'))


@bp.route('/remove/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    flash('Item removed.')
    return redirect(url_for('billing.index'))


@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    org_id = get_org_id()
    cart = get_cart()

    if not cart:
        flash('Cart is empty!')
        return redirect(url_for('billing.index'))

    total = 0
    items_to_save = []

    # Validate stock and calculate total
    for product_id, quantity in cart.items():
        product = Product.query.filter_by(id=int(product_id), org_id=org_id).first()

        if not product:
            flash(f'Product not found.')
            return redirect(url_for('billing.index'))

        if product.stock_quantity < quantity:
            flash(f'Insufficient stock for {product.name}.')
            return redirect(url_for('billing.index'))

        subtotal = product.selling_price * quantity
        total += subtotal
        items_to_save.append((product, quantity))

    # Create transaction
    transaction = Transaction(org_id=org_id, total_amount=total)
    db.session.add(transaction)
    db.session.flush()  # get transaction.id before commit

    # Save each item and deduct stock
    for product, quantity in items_to_save:
        item = TransactionItem(
            transaction_id=transaction.id,
            product_id=product.id,
            quantity=quantity,
            price=product.selling_price
        )
        db.session.add(item)
        product.stock_quantity -= quantity  # deduct stock

    db.session.commit()

    # Clear cart after successful checkout
    session.pop('cart', None)

    flash('Transaction completed successfully!')
    return redirect(url_for('billing.invoice', transaction_id=transaction.id))


@bp.route('/invoice/<int:transaction_id>')
@login_required
def invoice(transaction_id):
    org_id = get_org_id()
    transaction = Transaction.query.filter_by(
        id=transaction_id, org_id=org_id
    ).first_or_404()

    return render_template('billing/invoice.html', transaction=transaction)