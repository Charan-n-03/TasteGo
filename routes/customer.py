from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from models import Restaurant, Order, MenuItem, OrderItem, User, Review, Coupon, DeliveryPartner
from extensions import db
from werkzeug.security import generate_password_hash
from datetime import datetime

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.before_request
def require_customer():
    if "user_id" not in session or session.get("role") != "CUSTOMER":
        flash("Unauthorized access", "error")
        return redirect(url_for("auth.login"))

@customer_bp.route('/dashboard')
def dashboard():
    cuisine = request.args.get('cuisine', '')
    sort = request.args.get('sort', 'rating')
    q = request.args.get('q', '').strip()

    query = Restaurant.query.filter_by(is_approved=True)

    if cuisine:
        query = query.filter(Restaurant.cuisine_type.ilike(f'%{cuisine}%'))
    if q:
        query = query.filter(
            db.or_(
                Restaurant.name.ilike(f'%{q}%'),
                Restaurant.cuisine_type.ilike(f'%{q}%')
            )
        )

    if sort == 'rating':
        query = query.order_by(Restaurant.rating.desc())
    elif sort == 'delivery_time':
        query = query.order_by(Restaurant.delivery_time.asc())
    elif sort == 'price_low':
        query = query.order_by(Restaurant.price_for_two.asc())
    elif sort == 'price_high':
        query = query.order_by(Restaurant.price_for_two.desc())

    restaurants = query.all()

    # Active orders (not delivered)
    active_orders = Order.query.filter(
        Order.user_id == session["user_id"],
        Order.status != "Delivered"
    ).order_by(Order.created_at.desc()).all()

    # Recent orders
    recent_orders = Order.query.filter_by(user_id=session["user_id"])\
        .order_by(Order.created_at.desc()).limit(5).all()

    # Get unique cuisines for filter
    all_cuisines = db.session.query(Restaurant.cuisine_type)\
        .filter(Restaurant.is_approved == True, Restaurant.cuisine_type.isnot(None))\
        .distinct().all()
    cuisines = list(set(c for (c,) in all_cuisines if c for c in c.split(', ')))

    return render_template('customer/dashboard.html',
                           restaurants=restaurants,
                           active_orders=active_orders,
                           recent_orders=recent_orders,
                           cuisines=sorted(cuisines),
                           current_cuisine=cuisine,
                           current_sort=sort,
                           search_query=q)

@customer_bp.route('/restaurant/<int:id>/menu')
def restaurant_menu(id):
    restaurant = Restaurant.query.get_or_404(id)
    items = MenuItem.query.filter_by(restaurant_id=id, is_available=True).all()

    # Group by category
    categories = {}
    for item in items:
        cat = item.category or "Other"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)

    reviews = Review.query.filter_by(restaurant_id=id)\
        .order_by(Review.created_at.desc()).limit(5).all()

    return render_template('customer/restaurant_menu.html',
                           restaurant=restaurant,
                           categories=categories,
                           reviews=reviews)

@customer_bp.route('/cart', methods=['GET'])
def cart():
    cart_data = session.get('cart', {})
    cart_items = []
    total = 0.0
    restaurant = None

    if cart_data:
        restaurant_id = cart_data.get('restaurant_id')
        restaurant = Restaurant.query.get(restaurant_id)
        for item_id, quantity in cart_data.get('items', {}).items():
            menu_item = MenuItem.query.get(int(item_id))
            if menu_item:
                subtotal = menu_item.price * quantity
                total += subtotal
                cart_items.append({
                    'menu_item': menu_item,
                    'quantity': quantity,
                    'subtotal': subtotal
                })

    # Available coupons
    coupons = Coupon.query.filter_by(is_active=True).all()

    # Applied coupon
    applied_coupon = session.get('applied_coupon', None)
    discount = 0
    if applied_coupon and total > 0:
        coupon = Coupon.query.filter_by(code=applied_coupon, is_active=True).first()
        if coupon and total >= coupon.min_order:
            discount = min(total * coupon.discount_percent / 100, coupon.max_discount)

    delivery_fee = 40.0 if total > 0 else 0
    if total >= 500:
        delivery_fee = 0  # Free delivery over ₹500

    grand_total = total + delivery_fee - discount

    # Get user address
    user = User.query.get(session["user_id"])

    return render_template('customer/cart.html',
                           cart_items=cart_items,
                           total=total,
                           restaurant=restaurant,
                           coupons=coupons,
                           applied_coupon=applied_coupon,
                           discount=discount,
                           delivery_fee=delivery_fee,
                           grand_total=grand_total,
                           user=user)

@customer_bp.route('/cart/add/<int:restaurant_id>/<int:item_id>', methods=['POST'])
def add_to_cart(restaurant_id, item_id):
    cart_data = session.get('cart', {})

    if cart_data and cart_data.get('restaurant_id') != restaurant_id:
        cart_data = {'restaurant_id': restaurant_id, 'items': {}}
        flash("Cart cleared — items from a different restaurant.", "warning")
    elif not cart_data:
        cart_data = {'restaurant_id': restaurant_id, 'items': {}}

    items = cart_data['items']
    item_id_str = str(item_id)
    items[item_id_str] = items.get(item_id_str, 0) + 1

    session['cart'] = cart_data
    flash("Item added to cart!", "success")
    return redirect(request.referrer or url_for('customer.restaurant_menu', id=restaurant_id))

@customer_bp.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart_quantity(item_id):
    """Update item quantity in cart via AJAX or form."""
    action = request.form.get('action', 'increment')
    cart_data = session.get('cart', {})

    if cart_data and 'items' in cart_data:
        item_id_str = str(item_id)
        if item_id_str in cart_data['items']:
            if action == 'increment':
                cart_data['items'][item_id_str] += 1
            elif action == 'decrement':
                cart_data['items'][item_id_str] -= 1
                if cart_data['items'][item_id_str] <= 0:
                    del cart_data['items'][item_id_str]
            session['cart'] = cart_data

        if not cart_data.get('items'):
            session.pop('cart', None)
            session.pop('applied_coupon', None)

    return redirect(url_for('customer.cart'))

@customer_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_data = session.get('cart', {})
    if cart_data and 'items' in cart_data:
        item_id_str = str(item_id)
        if item_id_str in cart_data['items']:
            del cart_data['items'][item_id_str]
            session['cart'] = cart_data

        if not cart_data['items']:
            session.pop('cart', None)
            session.pop('applied_coupon', None)

        flash("Item removed from cart", "success")
    return redirect(url_for('customer.cart'))

@customer_bp.route('/cart/clear', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    session.pop('applied_coupon', None)
    flash("Cart cleared", "success")
    return redirect(url_for('customer.cart'))

@customer_bp.route('/cart/apply-coupon', methods=['POST'])
def apply_coupon():
    code = request.form.get('coupon_code', '').strip().upper()
    if not code:
        flash("Enter a coupon code", "error")
        return redirect(url_for('customer.cart'))

    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    if not coupon:
        flash("Invalid or expired coupon code", "error")
        session.pop('applied_coupon', None)
        return redirect(url_for('customer.cart'))

    # Check minimum order
    cart_data = session.get('cart', {})
    total = 0
    for item_id, qty in cart_data.get('items', {}).items():
        item = MenuItem.query.get(int(item_id))
        if item:
            total += item.price * qty

    if total < coupon.min_order:
        flash(f"Minimum order ₹{coupon.min_order:.0f} required for this coupon", "error")
        return redirect(url_for('customer.cart'))

    session['applied_coupon'] = code
    discount = min(total * coupon.discount_percent / 100, coupon.max_discount)
    flash(f"Coupon applied! You save ₹{discount:.0f}", "success")
    return redirect(url_for('customer.cart'))

@customer_bp.route('/cart/remove-coupon', methods=['POST'])
def remove_coupon():
    session.pop('applied_coupon', None)
    flash("Coupon removed", "success")
    return redirect(url_for('customer.cart'))

@customer_bp.route('/checkout', methods=['POST'])
def checkout():
    cart_data = session.get('cart')
    if not cart_data or not cart_data.get('items'):
        flash("Cart is empty", "error")
        return redirect(url_for('customer.cart'))

    restaurant_id = cart_data['restaurant_id']
    items = cart_data['items']
    payment_method = request.form.get('payment_method', 'COD')
    special_instructions = request.form.get('special_instructions', '').strip()

    user = User.query.get(session["user_id"])
    delivery_address = user.address or "Not specified"

    total_amount = 0.0
    order_items_to_add = []

    for item_id, quantity in items.items():
        menu_item = MenuItem.query.get(int(item_id))
        if menu_item:
            price = menu_item.price
            total_amount += price * quantity
            order_items_to_add.append((menu_item.id, quantity, price))

    # Calculate fees
    delivery_fee = 40.0 if total_amount < 500 else 0
    discount = 0
    applied_coupon = session.get('applied_coupon')
    if applied_coupon:
        coupon = Coupon.query.filter_by(code=applied_coupon, is_active=True).first()
        if coupon and total_amount >= coupon.min_order:
            discount = min(total_amount * coupon.discount_percent / 100, coupon.max_discount)

    new_order = Order(
        user_id=session["user_id"],
        restaurant_id=restaurant_id,
        status="Pending",
        total_amount=total_amount,
        delivery_fee=delivery_fee,
        discount=discount,
        payment_method=payment_method,
        delivery_address=delivery_address,
        special_instructions=special_instructions,
        estimated_delivery="35 mins"
    )
    db.session.add(new_order)
    db.session.flush()

    for item_id, quantity, price in order_items_to_add:
        order_item = OrderItem(
            order_id=new_order.id,
            menu_item_id=item_id,
            quantity=quantity,
            price_at_time=price
        )
        db.session.add(order_item)

    db.session.commit()
    session.pop('cart', None)
    session.pop('applied_coupon', None)
    flash(f"Order #{new_order.id} placed successfully! 🎉", "success")
    return redirect(url_for('customer.order_detail', order_id=new_order.id))

@customer_bp.route('/orders')
def orders():
    user_orders = Order.query.filter_by(user_id=session["user_id"])\
        .order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=user_orders)

@customer_bp.route('/order/<int:order_id>')
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=session["user_id"]).first_or_404()
    return render_template('customer/order_detail.html', order=order)

@customer_bp.route('/order/<int:order_id>/track')
def track_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=session["user_id"]).first_or_404()
    partner = None
    if order.delivery_partner:
        partner = order.delivery_partner
    return render_template('customer/track_order.html', order=order, partner=partner)

@customer_bp.route('/api/order-status/<int:order_id>')
def order_status_api(order_id):
    """AJAX endpoint for live order status polling."""
    order = Order.query.filter_by(id=order_id, user_id=session["user_id"]).first()
    if not order:
        return jsonify({'error': 'Not found'}), 404

    partner_data = None
    if order.delivery_partner:
        p = order.delivery_partner
        partner_data = {
            'name': p.user.username,
            'phone': p.phone or 'N/A',
            'vehicle': p.vehicle_type,
            'rating': p.rating,
            'latitude': p.latitude,
            'longitude': p.longitude
        }

    return jsonify({
        'status': order.status,
        'estimated_delivery': order.estimated_delivery,
        'partner': partner_data
    })

@customer_bp.route('/order/<int:order_id>/review', methods=['POST'])
def submit_review(order_id):
    order = Order.query.filter_by(id=order_id, user_id=session["user_id"]).first_or_404()

    if order.status != "Delivered":
        flash("You can only review delivered orders", "error")
        return redirect(url_for('customer.order_detail', order_id=order_id))

    # Check if already reviewed
    existing = Review.query.filter_by(order_id=order_id).first()
    if existing:
        flash("You've already reviewed this order", "warning")
        return redirect(url_for('customer.order_detail', order_id=order_id))

    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment', '').strip()

    review = Review(
        user_id=session["user_id"],
        restaurant_id=order.restaurant_id,
        order_id=order_id,
        rating=max(1, min(5, rating)),
        comment=comment
    )
    db.session.add(review)

    # Update restaurant rating
    restaurant = order.restaurant
    total = restaurant.total_ratings or 0
    current_avg = restaurant.rating or 0
    new_total = total + 1
    new_avg = ((current_avg * total) + rating) / new_total
    restaurant.rating = round(new_avg, 1)
    restaurant.total_ratings = new_total

    db.session.commit()
    flash("Thank you for your review! ⭐", "success")
    return redirect(url_for('customer.order_detail', order_id=order_id))

@customer_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    user = User.query.get(session["user_id"])
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        password = request.form.get('password')
        if password:
            user.password_hash = generate_password_hash(password)
        db.session.commit()
        session["username"] = user.username
        flash("Profile updated successfully", "success")
        return redirect(url_for('customer.profile'))

    order_count = Order.query.filter_by(user_id=user.id).count()
    total_spent = db.session.query(db.func.sum(Order.total_amount))\
        .filter_by(user_id=user.id, status="Delivered").scalar() or 0

    return render_template('customer/profile.html',
                           user=user,
                           order_count=order_count,
                           total_spent=total_spent)
