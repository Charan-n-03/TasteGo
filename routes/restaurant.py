from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models import Restaurant, MenuItem, Order
from extensions import db
from sqlalchemy import func

restaurant_bp = Blueprint('restaurant', __name__, url_prefix='/restaurant')

@restaurant_bp.before_request
def require_restaurant():
    if "user_id" not in session or session.get("role") != "STAFF":
        flash("Unauthorized access", "error")
        return redirect(url_for("auth.login"))

@restaurant_bp.route('/dashboard')
def dashboard():
    restaurants = Restaurant.query.filter_by(owner_id=session["user_id"]).all()
    orders = []
    total_revenue = 0
    total_orders = 0
    pending_orders = 0
    today_orders = 0

    if restaurants:
        rest_ids = [r.id for r in restaurants]
        orders = Order.query.filter(Order.restaurant_id.in_(rest_ids))\
            .order_by(Order.created_at.desc()).limit(10).all()
        total_revenue = db.session.query(func.sum(Order.total_amount))\
            .filter(Order.restaurant_id.in_(rest_ids), Order.status == "Delivered").scalar() or 0
        total_orders = Order.query.filter(Order.restaurant_id.in_(rest_ids)).count()
        pending_orders = Order.query.filter(
            Order.restaurant_id.in_(rest_ids),
            Order.status.in_(["Pending", "Preparing"])
        ).count()
        from datetime import datetime
        today = datetime.utcnow().date()
        today_orders = Order.query.filter(
            Order.restaurant_id.in_(rest_ids),
            func.date(Order.created_at) == today
        ).count()

    return render_template('restaurant/dashboard.html',
                           restaurants=restaurants,
                           orders=orders,
                           total_revenue=total_revenue,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           today_orders=today_orders)

@restaurant_bp.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        restaurant = Restaurant(
            name=request.form.get('name'),
            description=request.form.get('description'),
            image_url=request.form.get('image_url', ''),
            cuisine_type=request.form.get('cuisine_type', ''),
            address=request.form.get('address', ''),
            phone=request.form.get('phone', ''),
            delivery_time=request.form.get('delivery_time', '30-40 mins'),
            price_for_two=float(request.form.get('price_for_two', 400)),
            owner_id=session["user_id"]
        )
        db.session.add(restaurant)
        db.session.commit()
        flash("Restaurant added! Waiting for admin approval.", "success")
        return redirect(url_for('restaurant.dashboard'))
    return render_template('restaurant/details.html', restaurant=None)

@restaurant_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def details(id):
    restaurant = Restaurant.query.filter_by(id=id, owner_id=session["user_id"]).first_or_404()
    if request.method == 'POST':
        restaurant.name = request.form.get('name')
        restaurant.description = request.form.get('description')
        restaurant.image_url = request.form.get('image_url', '')
        restaurant.cuisine_type = request.form.get('cuisine_type', '')
        restaurant.address = request.form.get('address', '')
        restaurant.phone = request.form.get('phone', '')
        restaurant.delivery_time = request.form.get('delivery_time', '30-40 mins')
        restaurant.price_for_two = float(request.form.get('price_for_two', 400))
        db.session.commit()
        flash("Restaurant updated!", "success")
        return redirect(url_for('restaurant.dashboard'))
    return render_template('restaurant/details.html', restaurant=restaurant)

@restaurant_bp.route('/toggle/<int:id>', methods=['POST'])
def toggle_open(id):
    restaurant = Restaurant.query.filter_by(id=id, owner_id=session["user_id"]).first_or_404()
    restaurant.is_open = not restaurant.is_open
    db.session.commit()
    status = "open" if restaurant.is_open else "closed"
    flash(f"Restaurant is now {status}", "success")
    return redirect(url_for('restaurant.dashboard'))

@restaurant_bp.route('/<int:restaurant_id>/menu')
def menu(restaurant_id):
    restaurant = Restaurant.query.filter_by(id=restaurant_id, owner_id=session["user_id"]).first_or_404()
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()

    # Group by category
    categories = {}
    for item in menu_items:
        cat = item.category or "Other"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)

    return render_template('restaurant/menu.html',
                           restaurant=restaurant,
                           menu_items=menu_items,
                           categories=categories)

@restaurant_bp.route('/<int:restaurant_id>/menu/add', methods=['GET', 'POST'])
def menu_item_add(restaurant_id):
    restaurant = Restaurant.query.filter_by(id=restaurant_id, owner_id=session["user_id"]).first_or_404()
    if request.method == 'POST':
        item = MenuItem(
            name=request.form.get('name'),
            description=request.form.get('description'),
            price=float(request.form.get('price')),
            image_url=request.form.get('image_url', ''),
            category=request.form.get('category', 'Main Course'),
            is_veg=request.form.get('is_veg') == '1',
            is_bestseller=request.form.get('is_bestseller') == '1',
            restaurant_id=restaurant_id
        )
        db.session.add(item)
        db.session.commit()
        flash("Menu item added!", "success")
        return redirect(url_for('restaurant.menu', restaurant_id=restaurant_id))
    return render_template('restaurant/menu_item_form.html', restaurant=restaurant, item=None)

@restaurant_bp.route('/menu/edit/<int:item_id>', methods=['GET', 'POST'])
def menu_item_edit(item_id):
    item = MenuItem.query.get_or_404(item_id)
    restaurant = Restaurant.query.filter_by(id=item.restaurant_id, owner_id=session["user_id"]).first_or_404()

    if request.method == 'POST':
        item.name = request.form.get('name')
        item.description = request.form.get('description')
        item.price = float(request.form.get('price'))
        item.image_url = request.form.get('image_url', '')
        item.category = request.form.get('category', 'Main Course')
        item.is_veg = request.form.get('is_veg') == '1'
        item.is_bestseller = request.form.get('is_bestseller') == '1'
        db.session.commit()
        flash("Menu item updated!", "success")
        return redirect(url_for('restaurant.menu', restaurant_id=restaurant.id))
    return render_template('restaurant/menu_item_form.html', restaurant=restaurant, item=item)

@restaurant_bp.route('/menu/toggle/<int:item_id>', methods=['POST'])
def menu_item_toggle(item_id):
    item = MenuItem.query.get_or_404(item_id)
    restaurant = Restaurant.query.filter_by(id=item.restaurant_id, owner_id=session["user_id"]).first_or_404()
    item.is_available = not item.is_available
    db.session.commit()
    flash(f"{'Available' if item.is_available else 'Unavailable'}: {item.name}", "success")
    return redirect(url_for('restaurant.menu', restaurant_id=restaurant.id))

@restaurant_bp.route('/menu/delete/<int:item_id>', methods=['POST'])
def menu_item_delete(item_id):
    item = MenuItem.query.get_or_404(item_id)
    restaurant = Restaurant.query.filter_by(id=item.restaurant_id, owner_id=session["user_id"]).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Menu item deleted", "success")
    return redirect(url_for('restaurant.menu', restaurant_id=restaurant.id))

@restaurant_bp.route('/orders')
def orders():
    restaurants = Restaurant.query.filter_by(owner_id=session["user_id"]).all()
    orders = []
    if restaurants:
        rest_ids = [r.id for r in restaurants]
        orders = Order.query.filter(Order.restaurant_id.in_(rest_ids))\
            .order_by(Order.created_at.desc()).all()
    return render_template('restaurant/orders.html', orders=orders)

@restaurant_bp.route('/order/<int:order_id>/update', methods=['POST'])
def order_update(order_id):
    order = Order.query.get_or_404(order_id)
    restaurant = Restaurant.query.filter_by(id=order.restaurant_id, owner_id=session["user_id"]).first_or_404()

    new_status = request.form.get('status')
    if new_status:
        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} -> {new_status}", "success")
    return redirect(request.referrer or url_for('restaurant.orders'))
