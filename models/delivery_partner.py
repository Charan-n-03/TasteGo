from extensions import db

class DeliveryPartner(db.Model):
    __tablename__ = "delivery_partner"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    is_available = db.Column(db.Boolean, default=True)
    current_location = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True, default=12.9716)
    longitude = db.Column(db.Float, nullable=True, default=77.5946)
    vehicle_type = db.Column(db.String(30), default="Bike")  # Bike, Bicycle, Scooter
    phone = db.Column(db.String(20), nullable=True)
    total_deliveries = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=5.0)

    # Relationships
    user = db.relationship('User', backref=db.backref('delivery_profile', uselist=False))
