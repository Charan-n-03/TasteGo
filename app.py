from flask import Flask, render_template, jsonify, session
from config import Config
from extensions import db
from datetime import datetime, timedelta
import os

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
app.config.from_object(Config)
db.init_app(app)
app.secret_key = app.config["SECRET_KEY"]

try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"DB create_all warning: {e}")

from routes import auth_bp, main_bp, admin_bp, customer_bp, restaurant_bp, delivery_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(restaurant_bp)
app.register_blueprint(delivery_bp)

# --- Custom Jinja2 Filters ---
@app.template_filter('timeago')
def timeago_filter(dt):
    """Convert datetime to human-readable time ago string."""
    if not dt:
        return "Unknown"
    now = datetime.utcnow()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins} min{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"

@app.template_filter('currency')
def currency_filter(value):
    """Format value as Indian currency."""
    try:
        return f"\u20b9{float(value):,.2f}"
    except (ValueError, TypeError):
        return "\u20b90.00"

@app.context_processor
def inject_cart_count():
    """Inject cart item count into all templates."""
    cart = session.get('cart', {})
    count = sum(cart.get('items', {}).values()) if cart else 0
    return dict(cart_count=count)

# --- Custom Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# --- Auto Delivery Status Progression ---
# This runs on every request (via before_request) to work on both
# local dev AND serverless platforms like Vercel (where bg threads don't work).
def auto_progress_orders_sync():
    """Progresses order statuses automatically, called on each request."""
    try:
        from models import Order, DeliveryPartner
        now = datetime.utcnow()

        # Pending -> Preparing (after 30 seconds)
        pending = Order.query.filter_by(status="Pending").all()
        for order in pending:
            if order.created_at and (now - order.created_at).total_seconds() > 30:
                order.status = "Preparing"
                order.updated_at = now

        # Preparing -> Ready for Pickup (after 60 seconds)
        preparing = Order.query.filter_by(status="Preparing").all()
        for order in preparing:
            ref_time = order.updated_at or order.created_at
            if ref_time and (now - ref_time).total_seconds() > 60:
                order.status = "Ready for Pickup"
                order.updated_at = now

        # Ready for Pickup -> auto-assign partner + Out for Delivery (after 30 seconds)
        ready = Order.query.filter_by(status="Ready for Pickup").all()
        for order in ready:
            ref_time = order.updated_at or order.created_at
            if ref_time and (now - ref_time).total_seconds() > 30:
                if not order.delivery_partner_id:
                    partner = DeliveryPartner.query.filter_by(is_available=True).first()
                    if partner:
                        order.delivery_partner_id = partner.id
                        partner.is_available = False
                order.status = "Out for Delivery"
                order.updated_at = now

        # Out for Delivery -> Delivered (after 90 seconds)
        out_for = Order.query.filter_by(status="Out for Delivery").all()
        for order in out_for:
            ref_time = order.updated_at or order.created_at
            if ref_time and (now - ref_time).total_seconds() > 90:
                order.status = "Delivered"
                order.updated_at = now
                if order.delivery_partner:
                    order.delivery_partner.is_available = True
                    order.delivery_partner.total_deliveries += 1

        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

@app.before_request
def run_auto_delivery():
    """Run auto-delivery progression on every request."""
    auto_progress_orders_sync()

if __name__ == '__main__':
    app.run(port=5001, debug=True)