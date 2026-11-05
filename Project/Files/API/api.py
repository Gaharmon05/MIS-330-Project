"""
api.py -- StyleHub JSON API for the JavaScript version.

The JavaScript page (Files/WEBAPP/JavaScript_Version) never talks to MySQL
directly. It calls these URLs with fetch(), and this file runs the SQL.

Path of one request:
  1. index.js calls  fetch("/api/orders", { method: "POST" })
  2. The matching Python route below reads the JSON body
  3. It calls db.py with a SQL statement from queries.py + the values
  4. MySQL runs it and returns rows / commits the change
  5. The route answers with JSON, and index.js redraws that part of the page

The same server also hands the browser index.html, index.js and index.css.
"""
import os
import secrets
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, jsonify, request, send_from_directory, session
from flask.json.provider import DefaultJSONProvider
from werkzeug.security import check_password_hash, generate_password_hash

import db
import queries as q

FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "WEBAPP", "JavaScript_Version"))

ALTERATION_STATUSES = ["Received", "In Progress", "Ready for Pickup", "Completed"]
EMPLOYEE_ROLES = ["Manager", "Tailor", "Sales Associate"]


class StyleHubJSON(DefaultJSONProvider):
    """Send money as numbers and dates as ISO text (e.g. 2026-09-08T10:06:00)."""
    @staticmethod
    def default(value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat() + "T00:00:00"
        return DefaultJSONProvider.default(value)


app = Flask(__name__, static_folder=FRONTEND, static_url_path="")
app.json = StyleHubJSON(app)
app.json.sort_keys = False      # keep report columns in the order the SQL selects them
# Signs the login cookie. If no key is set, make a random one each run, so nobody can
# forge a login using a key copied from GitHub (you just get signed out on restart).
app.secret_key = os.environ.get("STYLEHUB_SECRET_KEY") or secrets.token_hex(32)


# =====================================================================
# Helpers
# =====================================================================
def current_user():
    return session.get("user")


def is_customer():
    return bool(current_user()) and current_user()["type"] == "customer"


def is_employee():
    return bool(current_user()) and current_user()["type"] == "employee"


def is_manager():
    return is_employee() and current_user()["role"] == "Manager"


def denied(who):
    """Returns an error response if the signed-in user isn't allowed, else None."""
    allowed = {"customer": is_customer(), "employee": is_employee(), "manager": is_manager()}[who]
    if allowed:
        return None
    return jsonify(error="Please sign in with an account that can do that."), 403


def body():
    return request.get_json(silent=True) or {}


def text(name):
    return str(body().get(name) or "").strip()


def number(name):
    """An optional whole number from the JSON body (None if blank)."""
    value = body().get(name)
    return int(value) if value not in (None, "") else None


def money_value(name):
    return Decimal(str(body().get(name)))


def ok(message, **extra):
    return jsonify(message=message, **extra)


def sign_in(user_type, user_id, first_name, role):
    session["user"] = {"type": user_type, "id": user_id, "name": first_name, "role": role}


def password_matches(stored_hash, password):
    try:
        return check_password_hash(stored_hash, password)
    except ValueError:            # sample-data rows hold placeholder text, not real hashes
        return False


NO_FILTERS = {key: None for key in ("text", "like", "category", "size", "color", "min_price", "max_price", "sort")}


# =====================================================================
# Errors -> JSON {"error": "..."}
# =====================================================================
DB_ERROR_MESSAGES = {
    1062: "That value already exists (for example, an email that is already registered).",
    1451: "That record can't be deleted because other records still use it "
          "(for example, a product with sales or supplier history).",
    1452: "That refers to a record that doesn't exist.",
    3819: "Blocked by a business rule: an alteration order needs a tailor "
          "before it can move past 'Received'.",
}


@app.errorhandler(db.DatabaseError)
def handle_database_error(err):
    if err.errno in DB_ERROR_MESSAGES:
        return jsonify(error=DB_ERROR_MESSAGES[err.errno]), 400
    return jsonify(error=f"Database error: {err.msg}"), 500


@app.errorhandler(ValueError)
@app.errorhandler(ArithmeticError)
@app.errorhandler(TypeError)
def handle_bad_input(err):
    return jsonify(error="Please check the values you entered."), 400


# =====================================================================
# The page itself
# =====================================================================
@app.route("/")
def home():
    return send_from_directory(FRONTEND, "index.html")


# =====================================================================
# ACCOUNT
# =====================================================================
@app.get("/api/session")
def get_session():
    cart_count = 0
    if is_customer():
        cart_count = db.fetch_one(q.CART_COUNT, (current_user()["id"],))["Items"]
    return jsonify(user=current_user(), cartCount=cart_count)


@app.get("/api/demo-accounts")
def demo_accounts():
    return jsonify(customers=db.fetch_all(q.ALL_CUSTOMERS), employees=db.fetch_all(q.ALL_EMPLOYEES))


@app.post("/api/register")
def register():
    first, last, email = text("firstName"), text("lastName"), text("email").lower()
    password, phone = text("password"), text("phone")
    if not (first and last and email and password):
        return jsonify(error="First name, last name, email and password are required."), 400
    db.execute(q.INSERT_CUSTOMER, (first, last, email, phone or None, generate_password_hash(password)))
    return ok("Account created -- sign in to start shopping.")


@app.post("/api/login")
def login():
    email, password = text("email").lower(), text("password")

    customer = db.fetch_one(q.CUSTOMER_BY_EMAIL, (email,))
    if customer and password_matches(customer["PasswordHash"], password):
        sign_in("customer", customer["CustID"], customer["FirstName"], "Customer")
        return ok(f"Welcome back, {customer['FirstName']}!")

    employee = db.fetch_one(q.EMPLOYEE_BY_EMAIL, (email,))
    if employee and password_matches(employee["PasswordHash"], password):
        sign_in("employee", employee["EmpID"], employee["FirstName"], employee["Role"])
        return ok(f"Signed in as {employee['Role']} {employee['FirstName']}.")

    return jsonify(error="Email or password is incorrect."), 401


@app.post("/api/demo-login")
def demo_login():
    """Presentation helper: sample accounts have placeholder password hashes."""
    kind, _, raw_id = text("account").partition(":")
    if kind == "customer":
        row = db.fetch_one(q.CUSTOMER_BY_ID, (int(raw_id),))
        if row:
            sign_in("customer", row["CustID"], row["FirstName"], "Customer")
            return ok(f"Signed in as {row['FirstName']}.")
    elif kind == "employee":
        row = db.fetch_one(q.EMPLOYEE_BY_ID, (int(raw_id),))
        if row:
            sign_in("employee", row["EmpID"], row["FirstName"], row["Role"])
            return ok(f"Signed in as {row['Role']} {row['FirstName']}.")
    return jsonify(error="Unknown account."), 400


@app.post("/api/logout")
def logout():
    session.clear()
    return ok("You are signed out.")


@app.get("/api/profile")
def get_profile():
    if (error := denied("customer")):
        return error
    return jsonify(db.fetch_one(q.CUSTOMER_BY_ID, (current_user()["id"],)))


@app.put("/api/profile")
def update_profile():
    if (error := denied("customer")):
        return error
    first, last = text("firstName"), text("lastName")
    if not (first and last):
        return jsonify(error="First and last name are required."), 400
    db.execute(q.UPDATE_CUSTOMER_PROFILE, (first, last, text("phone") or None, current_user()["id"]))
    session["user"] = {**current_user(), "name": first}
    return ok("Profile updated.")


# =====================================================================
# SHOP (everyone)
# =====================================================================
@app.get("/api/filters")
def filter_options():
    return jsonify(
        categories=[r["CategoryName"] for r in db.fetch_all(q.FILTER_CATEGORIES)],
        sizes=[r["Size"] for r in db.fetch_all(q.FILTER_SIZES)],
        colors=[r["Color"] for r in db.fetch_all(q.FILTER_COLORS)],
    )


@app.get("/api/products")
def search_products():
    """Query string example: /api/products?text=oxford&category=Shirts&sort=price_asc"""
    def arg(name):
        return (request.args.get(name) or "").strip() or None

    filters = {
        "text": arg("text"), "category": arg("category"), "size": arg("size"), "color": arg("color"),
        "min_price": Decimal(arg("min_price")) if arg("min_price") else None,
        "max_price": Decimal(arg("max_price")) if arg("max_price") else None,
        "sort": arg("sort"),
    }
    filters["like"] = f"%{filters['text']}%" if filters["text"] else None
    return jsonify(db.fetch_all(q.SEARCH_PRODUCTS, filters))


@app.get("/api/services")
def services():
    return jsonify(db.fetch_all(q.ALTERATION_SERVICES))


# =====================================================================
# CART & ORDERS (customers)
# =====================================================================
@app.get("/api/cart")
def get_cart():
    if (error := denied("customer")):
        return error
    return jsonify(db.fetch_all(q.CART_FOR_CUSTOMER, (current_user()["id"],)))


@app.post("/api/cart")
def add_to_cart():
    if (error := denied("customer")):
        return error
    quantity = max(1, number("quantity") or 1)
    db.execute(q.ADD_TO_CART, (current_user()["id"], number("productId"), quantity, quantity))
    return ok(f"Added to your cart ({quantity}).")


@app.put("/api/cart/<int:product_id>")
def update_cart(product_id):
    if (error := denied("customer")):
        return error
    quantity = number("quantity") or 0
    if quantity <= 0:
        db.execute(q.REMOVE_FROM_CART, (current_user()["id"], product_id))
    else:
        db.execute(q.UPDATE_CART_QUANTITY, (quantity, current_user()["id"], product_id))
    return ok("Cart updated.")


@app.delete("/api/cart/<int:product_id>")
def remove_from_cart(product_id):
    if (error := denied("customer")):
        return error
    db.execute(q.REMOVE_FROM_CART, (current_user()["id"], product_id))
    return ok("Removed from cart.")


@app.post("/api/orders")
def place_order():
    """The complete business transaction -- see db.place_order()."""
    if (error := denied("customer")):
        return error
    order_id, problem = db.place_order(current_user()["id"],
                                       text("paymentMethod"), text("cardLastFour"))
    if problem:
        return jsonify(error=problem), 400
    return ok(f"Order #{order_id} confirmed! Thank you for shopping at StyleHub.", orderId=order_id)


@app.get("/api/orders")
def order_history():
    if (error := denied("customer")):
        return error
    cust_id = current_user()["id"]
    items_by_order = defaultdict(list)
    for item in db.fetch_all(q.ORDER_ITEMS_FOR_CUSTOMER, (cust_id,)):
        items_by_order[item["OrderID"]].append(item)
    orders = db.fetch_all(q.ORDERS_FOR_CUSTOMER, (cust_id,))
    for order in orders:
        order["Items"] = items_by_order[order["OrderID"]]
    return jsonify(orders)


# =====================================================================
# ALTERATIONS (customers)
# =====================================================================
@app.get("/api/my-alterations")
def my_alterations():
    if (error := denied("customer")):
        return error
    return jsonify(db.fetch_all(q.ALTERATION_ORDERS_FOR_CUSTOMER, (current_user()["id"],)))


@app.post("/api/alterations")
def request_alteration():
    if (error := denied("customer")):
        return error
    garment, alteration_id = text("garment"), number("alterationId")
    if not garment or not alteration_id:
        return jsonify(error="Describe the garment and choose a service."), 400
    db.execute(q.INSERT_ALTERATION_ORDER, (current_user()["id"], garment, alteration_id))
    return ok("Alteration order received -- track its progress below.")


@app.delete("/api/alterations/<int:order_id>")
def cancel_alteration(order_id):
    if (error := denied("customer")):
        return error
    if db.execute(q.CANCEL_ALTERATION_ORDER, (order_id, current_user()["id"])):
        return ok("Alteration order cancelled.")
    return jsonify(error="Only orders still marked 'Received' can be cancelled."), 400


# =====================================================================
# WORK BOARD (employees)
# =====================================================================
@app.get("/api/board")
def work_board():
    if (error := denied("employee")):
        return error
    return jsonify(jobs=db.fetch_all(q.ALL_ALTERATION_ORDERS, {"status": None}),
                   tailors=db.fetch_all(q.TAILORS), statuses=ALTERATION_STATUSES)


@app.put("/api/board/<int:order_id>")
def update_alteration(order_id):
    if (error := denied("employee")):
        return error
    status = text("status")
    if status not in ALTERATION_STATUSES:
        return jsonify(error="Unknown status."), 400
    db.execute(q.UPDATE_ALTERATION_ORDER, {
        "id": order_id, "emp_id": number("empId"), "status": status, "fee": money_value("fee"),
    })
    return ok("Alteration order updated.")


# =====================================================================
# PRODUCTS & CATEGORIES (manager)
# =====================================================================
@app.get("/api/categories")
def categories():
    if (error := denied("manager")):
        return error
    return jsonify(db.fetch_all(q.ALL_CATEGORIES))


@app.post("/api/categories")
def add_category():
    if (error := denied("manager")):
        return error
    db.execute(q.INSERT_CATEGORY, (text("categoryName"), text("size"), text("color")))
    return ok("Category added.")


def product_values():
    return (number("categoryId"), text("productName"), text("brand"),
            money_value("price"), number("quantity"), number("reorderPoint"))


@app.post("/api/products")
def add_product():
    if (error := denied("manager")):
        return error
    db.execute(q.INSERT_PRODUCT, product_values())
    return ok("Product added.")


@app.put("/api/products/<int:product_id>")
def update_product(product_id):
    if (error := denied("manager")):
        return error
    db.execute(q.UPDATE_PRODUCT, product_values() + (product_id,))
    return ok("Product updated.")


@app.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    if (error := denied("manager")):
        return error
    db.execute(q.DELETE_PRODUCT, (product_id,))
    return ok("Product deleted.")


# =====================================================================
# INVENTORY & SUPPLIERS (manager)
# =====================================================================
@app.get("/api/inventory")
def inventory():
    if (error := denied("manager")):
        return error
    return jsonify(lowStock=db.fetch_all(q.LOW_STOCK), suppliers=db.fetch_all(q.ALL_SUPPLIERS),
                   purchases=db.fetch_all(q.SUPPLIER_PURCHASES),
                   products=db.fetch_all(q.SEARCH_PRODUCTS, NO_FILTERS))


@app.post("/api/suppliers")
def add_supplier():
    if (error := denied("manager")):
        return error
    db.execute(q.INSERT_SUPPLIER, (text("supplierName"), text("contactFirst"), text("contactLast"), text("contactEmail")))
    return ok("Supplier added.")


@app.put("/api/suppliers/<int:supplier_id>")
def update_supplier(supplier_id):
    if (error := denied("manager")):
        return error
    db.execute(q.UPDATE_SUPPLIER, (text("supplierName"), text("contactFirst"), text("contactLast"),
                                   text("contactEmail"), supplier_id))
    return ok("Supplier updated.")


@app.post("/api/purchases")
def add_purchase():
    if (error := denied("manager")):
        return error
    db.execute(q.INSERT_SUPPLIER_PURCHASE, (number("supplierId"), number("productId"),
                                            money_value("unitCost"), number("quantity")))
    return ok("Purchase order recorded. Mark it received when the shipment arrives.")


@app.post("/api/purchases/<int:purchase_id>/receive")
def receive_purchase(purchase_id):
    if (error := denied("manager")):
        return error
    if db.receive_supplier_purchase(purchase_id):
        return ok("Shipment received -- inventory updated.")
    return jsonify(error="That shipment was already received."), 400


# =====================================================================
# EMPLOYEES (manager)
# =====================================================================
@app.get("/api/employees")
def employees():
    if (error := denied("manager")):
        return error
    return jsonify(employees=db.fetch_all(q.ALL_EMPLOYEES), roles=EMPLOYEE_ROLES)


@app.post("/api/employees")
def add_employee():
    if (error := denied("manager")):
        return error
    role, password = text("role"), text("password")
    if role not in EMPLOYEE_ROLES or not password:
        return jsonify(error="Choose a role and set a starting password."), 400
    db.execute(q.INSERT_EMPLOYEE, (text("firstName"), text("lastName"), text("email").lower(),
                                   generate_password_hash(password), role))
    return ok("Employee account created.")


# =====================================================================
# REPORTS (manager)
# =====================================================================
@app.get("/api/stats")
def stats():
    if (error := denied("manager")):
        return error
    return jsonify(db.fetch_one(q.DASHBOARD_STATS))


@app.get("/api/reports")
def report_list():
    if (error := denied("manager")):
        return error
    return jsonify([{"key": key, "title": r[0]} for key, r in q.REPORTS.items()])


@app.get("/api/reports/<key>")
def run_report(key):
    if (error := denied("manager")):
        return error
    if key not in q.REPORTS:
        return jsonify(error="Unknown report."), 404
    title, sql, takeaway = q.REPORTS[key]
    return jsonify(title=title, takeaway=takeaway, rows=db.fetch_all(sql))


if __name__ == "__main__":
    # host="0.0.0.0": other computers on your network can open the site too
    # (teammates use http://<your-IP>:<port>). MySQL itself stays private on this PC.
    # Debug mode stays OFF unless STYLEHUB_DEBUG=1, because its error page can run
    # Python in the browser and read environment variables (your DB password).
    app.run(host="0.0.0.0", port=5001, debug=os.environ.get("STYLEHUB_DEBUG") == "1")
