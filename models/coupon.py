from extensions import db
from datetime import datetime

class Coupon(db.Model):
    __tablename__ = "coupon"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    description = db.Column(db.String(200), nullable=True)
    discount_percent = db.Column(db.Float, nullable=False, default=10)
    max_discount = db.Column(db.Float, nullable=False, default=100)
    min_order = db.Column(db.Float, nullable=False, default=200)
    is_active = db.Column(db.Boolean, default=True)
    valid_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
