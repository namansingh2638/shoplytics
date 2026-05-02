from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from zoneinfo import ZoneInfo

# This tells flask-login how to load a user from the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    memberships = db.relationship('UserOrganization', backref='user', lazy=True)


class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    open_hour = db.Column(db.Integer, default=9)    # ← add this
    close_hour = db.Column(db.Integer, default=21)  # ← add this (9 PM)

    members = db.relationship('UserOrganization', backref='organization', lazy=True)
    products = db.relationship('Product', backref='organization', lazy=True)


class UserOrganization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'staff'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

    products = db.relationship('Product', backref='category', lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(50), unique=True, nullable=True)
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(200), nullable=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

    purchases = db.relationship('Purchase', backref='supplier', lazy=True)


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', backref='purchases')
    quantity = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

    items = db.relationship('TransactionItem', backref='transaction', lazy=True)


class TransactionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', backref='transaction_items')
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # selling price at time of sale


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(80), nullable=True)
    note = db.Column(db.String(200), nullable=True)
    date = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))