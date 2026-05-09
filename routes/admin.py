from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models import User, Restaurant, Order, DeliveryPartner, Review, Coupon, UserRole
from extensions import db
from sqlalchemy import func
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def require_admin():
    if "user_id" not in session or session.get("role") != "ADMIN":
        flash("Unauthorized access", "error")
        return redirect(url_for("auth.login"))

@admin_bp.route('/dashboard')
def dashboard():
    users_count = User.query.count()
    restaurants_count = Restaurant.query.count()
    orders_count = Order.query.count()
    partners_count = DeliveryPartner.query.count()
    reviews_count = Review.query.count()
    active_coupons = Coupon.query.filter_by(is_active=True).count()

    total_revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(status="Delivered").scalar() or 0
    pending_approvals = Restaurant.query.filter_by(is_approved=False).count()

    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    # Orders by status
    status_counts = {}
    for status in ["Pending", "Preparing", "Ready for Pickup", "Out for Delivery", "Delivered"]:
        status_counts[status] = Order.query.filter_by(status=status).count()

    # Customer count
    customer_count = User.query.filter_by(role=UserRole.CUSTOMER).count()

    return render_template('admin/dashboard.html',
                           users_count=users_count,
                           restaurants_count=restaurants_count,
                           orders_count=orders_count,
                           partners_count=partners_count,
                           reviews_count=reviews_count,
                           active_coupons=active_coupons,
                           total_revenue=total_revenue,
                           pending_approvals=pending_approvals,
                           recent_orders=recent_orders,
                           status_counts=status_counts,
                           customer_count=customer_count)

@admin_bp.route('/users')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot delete yourself", "error")
        return redirect(url_for('admin.users'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted", "success")
    return redirect(url_for('admin.users'))

@admin_bp.route('/restaurants')
def restaurants():
    all_restaurants = Restaurant.query.order_by(Restaurant.created_at.desc()).all()
    return render_template('admin/restaurants.html', restaurants=all_restaurants)

@admin_bp.route('/restaurant/add', methods=['GET', 'POST'])
def add_restaurant():
    if request.method == 'POST':
        restaurant = Restaurant(
            name=request.form.get('name'),
            description=request.form.get('description'),
            owner_id=request.form.get('owner_id'),
            image_url=request.form.get('image_url', ''),
            cuisine_type=request.form.get('cuisine_type', ''),
            is_approved=True
        )
        db.session.add(restaurant)
        db.session.commit()
        flash("Restaurant added and auto-approved.", "success")
        return redirect(url_for('admin.restaurants'))
    staff_users = User.query.filter_by(role=UserRole.STAFF).all()
    return render_template('admin/restaurant_form.html', staff_users=staff_users)

@admin_bp.route('/restaurant/approve/<int:r_id>', methods=['POST'])
def approve_restaurant(r_id):
    r = Restaurant.query.get_or_404(r_id)
    r.is_approved = not r.is_approved
    db.session.commit()
    status = "approved" if r.is_approved else "revoked"
    flash(f"Restaurant {status}.", "success")
    return redirect(url_for('admin.restaurants'))

@admin_bp.route('/restaurant/delete/<int:r_id>', methods=['POST'])
def delete_restaurant(r_id):
    r = Restaurant.query.get_or_404(r_id)
    db.session.delete(r)
    db.session.commit()
    flash("Restaurant deleted", "success")
    return redirect(url_for('admin.restaurants'))

@admin_bp.route('/delivery_partners')
def delivery_partners():
    partners = DeliveryPartner.query.all()
    return render_template('admin/delivery_partners.html', partners=partners)

@admin_bp.route('/delivery_partner/edit/<int:p_id>', methods=['GET', 'POST'])
def edit_delivery_partner(p_id):
    partner = DeliveryPartner.query.get_or_404(p_id)
    if request.method == 'POST':
        partner.is_available = (request.form.get('is_available') == '1')
        db.session.commit()
        flash("Partner status updated", "success")
        return redirect(url_for('admin.delivery_partners'))
    return render_template('admin/delivery_partner_edit.html', partner=partner)

# --- Coupon Management ---
@admin_bp.route('/coupons')
def coupons():
    all_coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('admin/coupons.html', coupons=all_coupons)

@admin_bp.route('/coupon/add', methods=['GET', 'POST'])
def add_coupon():
    if request.method == 'POST':
        coupon = Coupon(
            code=request.form.get('code', '').upper().strip(),
            description=request.form.get('description', ''),
            discount_percent=float(request.form.get('discount_percent', 10)),
            max_discount=float(request.form.get('max_discount', 100)),
            min_order=float(request.form.get('min_order', 200)),
            is_active=request.form.get('is_active') == '1'
        )
        db.session.add(coupon)
        db.session.commit()
        flash("Coupon created!", "success")
        return redirect(url_for('admin.coupons'))
    return render_template('admin/coupon_form.html', coupon=None)

@admin_bp.route('/coupon/edit/<int:c_id>', methods=['GET', 'POST'])
def edit_coupon(c_id):
    coupon = Coupon.query.get_or_404(c_id)
    if request.method == 'POST':
        coupon.code = request.form.get('code', '').upper().strip()
        coupon.description = request.form.get('description', '')
        coupon.discount_percent = float(request.form.get('discount_percent', 10))
        coupon.max_discount = float(request.form.get('max_discount', 100))
        coupon.min_order = float(request.form.get('min_order', 200))
        coupon.is_active = request.form.get('is_active') == '1'
        db.session.commit()
        flash("Coupon updated!", "success")
        return redirect(url_for('admin.coupons'))
    return render_template('admin/coupon_form.html', coupon=coupon)

@admin_bp.route('/coupon/delete/<int:c_id>', methods=['POST'])
def delete_coupon(c_id):
    coupon = Coupon.query.get_or_404(c_id)
    db.session.delete(coupon)
    db.session.commit()
    flash("Coupon deleted", "success")
    return redirect(url_for('admin.coupons'))

# --- Reviews ---
@admin_bp.route('/reviews')
def reviews():
    all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=all_reviews)

@admin_bp.route('/review/delete/<int:r_id>', methods=['POST'])
def delete_review(r_id):
    review = Review.query.get_or_404(r_id)
    db.session.delete(review)
    db.session.commit()
    flash("Review deleted", "success")
    return redirect(url_for('admin.reviews'))

# --- Orders Overview ---
@admin_bp.route('/orders')
def orders_overview():
    status_filter = request.args.get('status', '')
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_orders = query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=all_orders, current_status=status_filter)

@admin_bp.route('/reset-db', methods=['POST'])
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        from werkzeug.security import generate_password_hash
        admin = User(username="admin", email="admin@tastego.com",
                     role=UserRole.ADMIN,
                     password_hash=generate_password_hash("admin"))
        db.session.add(admin)
        db.session.commit()
        flash("Database reset. Run seed_db.py for demo data.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    user = User.query.get(session["user_id"])
    if request.method == 'POST':
        user.username = request.form.get('username', user.username)
        user.email = request.form.get('email', user.email)
        user.phone = request.form.get('phone', '')
        new_password = request.form.get('password', '').strip()
        if new_password:
            if len(new_password) < 6:
                flash("Password must be at least 6 characters", "error")
                return redirect(url_for('admin.profile'))
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        session["username"] = user.username
        flash("Profile updated successfully!", "success")
        return redirect(url_for('admin.profile'))
    return render_template('admin/profile.html', user=user)
