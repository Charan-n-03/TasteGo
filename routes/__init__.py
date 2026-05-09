from routes.auth import auth_bp
from routes.main import main_bp
from routes.admin import admin_bp
from routes.customer import customer_bp
from routes.restaurant import restaurant_bp
from routes.delivery import delivery_bp

__all__ = ["auth_bp", "main_bp", "admin_bp", "customer_bp", "restaurant_bp", "delivery_bp"]
