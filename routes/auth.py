from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import User, UserRole, DeliveryPartner
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        c_password = request.form.get('c_password', '').strip()
        role = request.form.get('role', '').strip()

        if not username:
            flash("Username is required", "error")
            return redirect(url_for("auth.register"))
        if not email:
            flash("Email is required", "error")
            return redirect(url_for("auth.register"))
        if not password or not c_password:
            flash("Password cannot be empty", "error")
            return redirect(url_for("auth.register"))
        if password != c_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("auth.register"))
        if not role:
            flash("Please select a role", "error")
            return redirect(url_for("auth.register"))
        if '@' not in email:
            flash("Enter a valid email", "error")
            return redirect(url_for("auth.register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters", "error")
            return redirect(url_for("auth.register"))

        user_check = User.query.filter_by(username=username).first()
        email_check = User.query.filter_by(email=email).first()
        if user_check:
            flash("Username already exists", "error")
            return redirect(url_for("auth.register"))
        if email_check:
            flash("Email already taken", "error")
            return redirect(url_for("auth.register"))

        password_hash = generate_password_hash(password)
        try:
            role_enum = UserRole(role.lower())
            user = User(
                username=username,
                email=email,
                phone=phone if phone else None,
                role=role_enum,
                password_hash=password_hash
            )
            db.session.add(user)
            db.session.commit()

            # Auto-create delivery partner profile
            if role_enum == UserRole.PARTNER:
                dp = DeliveryPartner(user_id=user.id, phone=phone if phone else None)
                db.session.add(dp)
                db.session.commit()

            flash("Registration successful! Please login.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred: " + str(e), "error")
            return redirect(url_for("auth.register"))
    return render_template("register.html")

@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Enter email and password", "error")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("User not found. Please register.", "error")
            return redirect(url_for("auth.login"))

        if not check_password_hash(user.password_hash, password):
            flash("Invalid email or password", "error")
            return redirect(url_for("auth.login"))

        session["user_id"] = user.id
        session["role"] = user.role.name.upper() if hasattr(user.role, 'name') else str(user.role).upper()
        session["username"] = user.username
        session["avatar"] = user.avatar_url or ""
        session.permanent = True
        flash(f"Welcome back, {user.username}!", "success")

        # Role based redirect
        if session["role"] == "ADMIN":
            return redirect(url_for("admin.dashboard"))
        elif session["role"] == "CUSTOMER":
            return redirect(url_for("customer.dashboard"))
        elif session["role"] == "STAFF":
            return redirect(url_for("restaurant.dashboard"))
        elif session["role"] == "PARTNER":
            return redirect(url_for("delivery.dashboard"))
        else:
            return redirect(url_for("main.home"))

    return render_template("login.html")

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("auth.login"))
