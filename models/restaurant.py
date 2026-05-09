from extensions import db
from datetime import datetime

class Restaurant(db.Model):
    __tablename__ = "restaurant"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    cuisine_type = db.Column(db.String(100), nullable=True)  # "North Indian, Chinese"
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True, default="Bangalore")
    phone = db.Column(db.String(20), nullable=True)
    rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    delivery_time = db.Column(db.String(50), default="30-40 mins")
    price_for_two = db.Column(db.Float, default=400.0)
    is_approved = db.Column(db.Boolean, default=False)
    is_open = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    owner = db.relationship('User', backref=db.backref('restaurants', lazy=True, cascade='all, delete-orphan'))
