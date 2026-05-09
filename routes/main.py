from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import text, or_
from extensions import db
from models import Restaurant, MenuItem, Review

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    # Featured restaurants (approved, open, top-rated)
    featured = Restaurant.query.filter_by(is_approved=True, is_open=True)\
        .order_by(Restaurant.rating.desc()).limit(8).all()
    # Popular food items (bestsellers)
    popular_items = MenuItem.query.filter_by(is_bestseller=True, is_available=True)\
        .limit(8).all()
    # Stats
    total_restaurants = Restaurant.query.filter_by(is_approved=True).count()
    total_items = MenuItem.query.count()

    return render_template('index.html',
                           featured_restaurants=featured,
                           popular_items=popular_items,
                           total_restaurants=total_restaurants,
                           total_items=total_items)

@main_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'restaurants': [], 'items': []})

    # Search restaurants
    restaurants = Restaurant.query.filter(
        Restaurant.is_approved == True,
        or_(
            Restaurant.name.ilike(f'%{q}%'),
            Restaurant.cuisine_type.ilike(f'%{q}%'),
            Restaurant.description.ilike(f'%{q}%')
        )
    ).limit(5).all()

    # Search menu items
    items = MenuItem.query.filter(
        MenuItem.is_available == True,
        or_(
            MenuItem.name.ilike(f'%{q}%'),
            MenuItem.description.ilike(f'%{q}%'),
            MenuItem.category.ilike(f'%{q}%')
        )
    ).limit(5).all()

    return jsonify({
        'restaurants': [{
            'id': r.id, 'name': r.name, 'image_url': r.image_url,
            'cuisine_type': r.cuisine_type, 'rating': r.rating
        } for r in restaurants],
        'items': [{
            'id': i.id, 'name': i.name, 'image_url': i.image_url,
            'price': i.price, 'restaurant_id': i.restaurant_id,
            'restaurant_name': i.restaurant.name if i.restaurant else ''
        } for i in items]
    })

@main_bp.route('/restaurant/<int:id>/view')
def restaurant_view(id):
    restaurant = Restaurant.query.get_or_404(id)
    menu_items = MenuItem.query.filter_by(restaurant_id=id, is_available=True).all()
    reviews = Review.query.filter_by(restaurant_id=id).order_by(Review.created_at.desc()).limit(10).all()

    # Group items by category
    categories = {}
    for item in menu_items:
        cat = item.category or "Other"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)

    return render_template('restaurant_view.html',
                           restaurant=restaurant,
                           categories=categories,
                           reviews=reviews)

@main_bp.route('/db-test')
def db_test():
    try:
        result = db.session.execute(text("SELECT 'success'"))
        return jsonify({
            "status": "success",
            "records": [row[0] for row in result]
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
