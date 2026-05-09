# TasteGo Project Documentation

This document serves as a comprehensive technical explanation of the TasteGo application, covering its database schema, backend architecture, frontend UI, and core business logic.

## 1. System Architecture overview

TasteGo is a monolithic web application built using **Python and the Flask Framework**. The architecture strictly follows the **MVC (Model-View-Controller)** pattern:
- **Models**: Defines database schemas via `Flask-SQLAlchemy`.
- **Views**: UI rendered dynamically using `Jinja2` templates and styled via custom CSS.
- **Controllers (Routes)**: Application logic is separated into multiple `Flask Blueprints`.

## 2. Database Schema (The Models)

The system uses a relational database (MySQL via `mysql-connector-python`) managed entirely by SQLAlchemy ORM. The models are defined in the `models/` directory:

*   **`User`**: The central authentication table. It utilizes a `UserRole` enum (`ADMIN`, `STAFF`, `PARTNER`, `CUSTOMER`) to implement Role-Based Access Control (RBAC). It stores credentials (hashed passwords) and user metadata (like the newly added `address`).
*   **`Restaurant`**: Represents a food vendor. Linked to a `User` (STAFF) via `owner_id`. It includes an `is_approved` boolean so Admins can moderate the platform.
*   **`MenuItem`**: Represents food items linked to a specific `Restaurant`.
*   **`Order` & `OrderItem`**: `Order` stores the overall transaction (customer, restaurant, total amount, status, assigned delivery partner). `OrderItem` acts as a junction table, storing the exact items, quantities, and *price at the time of purchase* (to ensure historical accuracy if prices change).
*   **`DeliveryPartner`**: An extension of the `User` model, holding specific data like `is_available` status and `current_location`.

## 3. Backend Logic & Routing (The Controllers)

The backend is modularized using Flask Blueprints. Each blueprint manages a specific domain and enforces security using `@before_request` hooks (checking `session["role"]`).

### **Auth Blueprint (`routes/auth.py`)**
Handles user registration, login, and session management (`session["user_id"]`, `session["role"]`). Passwords are securely hashed using `werkzeug.security`.

### **Admin Blueprint (`routes/admin.py`)**
The master control panel. Admins can view system-wide statistics, manage users, and importantly, **approve or revoke restaurants**. They also have an emergency "Reset Database" endpoint.

### **Restaurant Blueprint (`routes/restaurant.py`)**
Used by `STAFF` users. This is where vendors manage their profiles and menus. They can perform full CRUD (Create, Read, Update, Delete) operations on their `MenuItem`s. They can also manually update the status of active orders (e.g., from "Pending" to "Preparing").

### **Customer Blueprint (`routes/customer.py`)**
The core consumer experience. Features include:
- Browsing `is_approved` restaurants.
- A session-based shopping cart. The cart restricts users from adding items from multiple restaurants simultaneously.
- Checkout process: Converts the session cart into an `Order` and associated `OrderItem`s in the database.
- Profile management (updating their `address` for delivery).

### **Delivery Blueprint (`routes/delivery.py`)**
Used by `PARTNER` users. Features include:
- Viewing `available_orders` (Orders where status is "Ready for Pickup").
- Accepting an order, which assigns the `delivery_partner_id` to the order and marks the partner as unavailable (`is_available = False`).
- Marking an order as "Delivered", which frees up the partner to take new jobs.

## 4. UI / Frontend Logic (The Views)

The frontend is built with HTML5, Jinja2 templating, and Vanilla CSS (`static/css/main.css`).

> [!TIP]
> **Premium UI Philosophy:** The application avoids generic frameworks like Bootstrap. Instead, it utilizes a custom CSS design system featuring the "Sunset Orange" brand color, glassmorphism card effects, CSS Grid/Flexbox layouts, and the modern `Outfit` font to provide a high-end user experience.

- **Jinja2 Templating**: Allows for dynamic rendering. `{% extends "base.html" %}` is used to wrap all pages in a consistent navigation bar and layout structure.
- **Micro-animations**: Hover effects and form focus transitions are implemented purely in CSS to make the app feel responsive and "alive".
- **Dynamic Formatting**: Prices are consistently formatted to 2 decimal places using Jinja filters (`{{ "%.2f"|format(price) }}`) and utilize the local `₹` currency symbol.

## 5. Typical Workflow Example

1. **Setup**: The Admin runs `seed_db.py` to populate initial Indian-themed data and test accounts.
2. **Browsing**: A Customer logs in, updates their profile with an `address`, browses approved restaurants, and adds "Butter Chicken" to their cart.
3. **Checkout**: The Customer checks out. An `Order` is created with status "Pending".
4. **Preparation**: The Restaurant Owner logs in, sees the order, and updates the status to "Preparing", and eventually "Ready for Pickup".
5. **Delivery**: The Delivery Partner logs in, sees the available order alongside the **Customer's Address**. They accept the job, deliver the food, and mark it as "Delivered".
