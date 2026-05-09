from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from models import Order, DeliveryPartner, User
from extensions import db
from sqlalchemy import func
import random

delivery_bp = Blueprint('delivery', __name__, url_prefix='/delivery')

@delivery_bp.before_request
def require_delivery():
    if "user_id" not in session or session.get("role") != "PARTNER":
        flash("Unauthorized access", "error")
        return redirect(url_for("auth.login"))

@delivery_bp.route('/dashboard')
def dashboard():
    partner = DeliveryPartner.query.filter_by(user_id=session["user_id"]).first()
    if not partner:
        partner = DeliveryPartner(user_id=session["user_id"])
        db.session.add(partner)
        db.session.commit()

    available_orders = Order.query.filter(
        Order.status.in_(["Pending", "Preparing", "Ready for Pickup"]),
        Order.delivery_partner_id.is_(None)
    ).all()

    assigned_orders = Order.query.filter_by(delivery_partner_id=partner.id)\
        .filter(Order.status != 'Delivered').all()

    # Stats
    total_deliveries = partner.total_deliveries
    today_earnings = db.session.query(func.sum(Order.delivery_fee))\
        .filter_by(delivery_partner_id=partner.id, status="Delivered").scalar() or 0
    total_earnings = db.session.query(func.sum(Order.delivery_fee))\
        .filter_by(delivery_partner_id=partner.id, status="Delivered").scalar() or 0

    # Recent completed
    completed = Order.query.filter_by(delivery_partner_id=partner.id, status="Delivered")\
        .order_by(Order.created_at.desc()).limit(5).all()

    return render_template('delivery/dashboard.html',
                           available_orders=available_orders,
                           assigned_orders=assigned_orders,
                           partner=partner,
                           total_deliveries=total_deliveries,
                           today_earnings=today_earnings,
                           total_earnings=total_earnings,
                           completed_orders=completed)

@delivery_bp.route('/accept/<int:order_id>', methods=['POST'])
def accept_order(order_id):
    order = Order.query.get_or_404(order_id)
    partner = DeliveryPartner.query.filter_by(user_id=session["user_id"]).first()
    if not partner:
        partner = DeliveryPartner(user_id=session["user_id"])
        db.session.add(partner)
        db.session.flush()

    if order.delivery_partner_id is None:
        order.delivery_partner_id = partner.id
        order.status = "Out for Delivery"
        partner.is_available = False
        db.session.commit()
        flash("Delivery accepted! 🛵", "success")
    else:
        flash("Order already taken.", "error")
    return redirect(url_for('delivery.dashboard'))

@delivery_bp.route('/complete/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    order = Order.query.get_or_404(order_id)
    partner = DeliveryPartner.query.filter_by(user_id=session["user_id"]).first()

    if partner and order.delivery_partner_id == partner.id:
        order.status = "Delivered"
        partner.is_available = True
        partner.total_deliveries += 1
        db.session.commit()
        flash("Delivery completed! 🎉", "success")
    else:
        flash("Unauthorized.", "error")
    return redirect(url_for('delivery.dashboard'))

@delivery_bp.route('/toggle-availability', methods=['POST'])
def toggle_availability():
    partner = DeliveryPartner.query.filter_by(user_id=session["user_id"]).first()
    if partner:
        partner.is_available = not partner.is_available
        db.session.commit()
        status = "Online" if partner.is_available else "Offline"
        flash(f"You are now {status}", "success")
    return redirect(url_for('delivery.dashboard'))

@delivery_bp.route('/update-location', methods=['POST'])
def update_location():
    """Update delivery partner's GPS coordinates."""
    partner = DeliveryPartner.query.filter_by(user_id=session["user_id"]).first()
    if partner:
        lat = request.form.get('latitude') or request.json.get('latitude')
        lng = request.form.get('longitude') or request.json.get('longitude')
        if lat and lng:
            partner.latitude = float(lat)
            partner.longitude = float(lng)
            db.session.commit()
            return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@delivery_bp.route('/api/location/<int:order_id>')
def get_partner_location(order_id):
    """API endpoint for customer to poll delivery partner location."""
    order = Order.query.get_or_404(order_id)
    if order.delivery_partner:
        p = order.delivery_partner
        # Simulate movement
        p.latitude = (p.latitude or 12.9716) + random.uniform(-0.002, 0.002)
        p.longitude = (p.longitude or 77.5946) + random.uniform(-0.002, 0.002)
        db.session.commit()
        return jsonify({
            'latitude': p.latitude,
            'longitude': p.longitude,
            'name': p.user.username,
            'vehicle': p.vehicle_type
        })
    return jsonify({'error': 'No partner assigned'}), 404
