from extensions import db
from datetime import datetime

class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    delivery_partner_id = db.Column(db.Integer, db.ForeignKey('delivery_partner.id'), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Pending")
    total_amount = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, default=40.0)
    discount = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(30), default="COD")  # COD, Card, UPI
    delivery_address = db.Column(db.Text, nullable=True)
    estimated_delivery = db.Column(db.String(50), default="35 mins")
    special_instructions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('orders', lazy=True, cascade='all, delete-orphan'))
    restaurant = db.relationship('Restaurant', backref=db.backref('orders', lazy=True, cascade='all, delete-orphan'))
    delivery_partner = db.relationship('DeliveryPartner', backref=db.backref('assigned_orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = "order_item"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_at_time = db.Column(db.Float, nullable=False)

    menu_item = db.relationship('MenuItem')
