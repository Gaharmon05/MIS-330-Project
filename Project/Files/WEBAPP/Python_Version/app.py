"""
app.py -- StyleHub, Python version (Flask renders the page on the server).

It is ONE page (one route "/" and one layout). The menu switches between
sections with ?tab=shop, ?tab=cart, ... and only the data for that tab is loaded.

Path of one request:
  1. Browser submits a form, e.g. POST /cart/place-order
  2. The matching Python route below reads the form values
  3. It calls db.py with a SQL statement from queries.py + the values
  4. MySQL runs it and returns rows / commits the change
  5. The route redirects to /?tab=... and index() re-renders the page

Every POST route's URL starts with the tab it belongs to (/cart/..., /products/...)
so after an action -- or an error -- we go back to that tab.
"""
import os
import secrets
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db
import queries as q
import ui

app = Flask(__name__, static_folder="Client_Resources", static_url_path="/Client_Resources")
# Signs the login cookie. If no key is set, make a random one each run, so nobody can
# forge a login using a key copied from GitHub (you just get signed out on restart).
app.secret_key = os.environ.get("STYLEHUB_SECRET_KEY") or secrets.token_hex(32)
app.jinja_env.globals.update(icon=ui.icon, swatch=ui.swatch, initials=ui.initials)

ALTERATION_STATUSES = ["Received", "In Progress", "Ready for Pickup", "Completed"]
EMPLOYEE_ROLES = ["Manager", "Tailor", "Sales Associate"]


# =====================================================================
# Who is signed in?
# =====================================================================
def current_user():
    return session.get("user")


def is_customer():
    return bool(current_user()) and current_user()["type"] == "customer"


def is_employee():
    return bool(current_user()) and current_user()["type"] == "employee"


def is_manager():
    return is_employee() and current_user()["role"] == "Manager"


def can_see(audience):
    """Which tabs the current user may open (matches the last column of ui.TABS)."""
    return {"everyone": True, "customer": is_customer(),
            "employee": is_employee(), "manager": is_manager()}[audience]


# =====================================================================
# Small helpers
# =====================================================================
def back_to(tab):
    return redirect(url_for("index", tab=tab))


def back_to_previous_page(default_tab):
    """Go back to the exact page the user came from (keeps search filters)."""
    query = urlparse(request.referrer or "").query
    return redirect(url_for("index") + "?" + query) if query else back_to(default_tab)


def deny(message="Please sign in with an account that can do that."):
    flash(message, "error")
    return back_to("account")


def form_text(name):
    return request.form.get(name, "").strip()


def blank_to_none(value):
    value = (value or "").strip()
    return value or None


def to_decimal(value):
    try:
        return Decimal(value) if value not in (None, "") else None
    except ArithmeticError:
        return None


def password_matches(stored_hash, password):
    try:
        return check_password_hash(stored_hash, password)
    except ValueError:            # sample-data rows hold placeholder text, not real hashes
        return False


def sign_in(user_type, user_id, first_name, role):
    session["user"] = {"type": user_type, "id": user_id, "name": first_name, "role": role}


# =====================================================================
# Errors -> friendly messages
# =====================================================================
DB_ERROR_MESSAGES = {
    1062: "That value already exists (for example, an email that is already registered).",
    1451: "That record can't be deleted because other records still use it "
          "(for example, a product with sales or supplier history).",
    1452: "That refers to a record that doesn't exist.",
    3819: "Blocked by a business rule: an alteration order needs a tailor "
          "before it can move past 'Received'.",
}


def tab_from_path():
    return request.path.strip("/").split("/")[0] or "shop"


@app.errorhandler(db.DatabaseError)
def handle_database_error(err):
    if request.method != "POST":
        return render_template("db_error.html", message=err.msg), 500
    flash(DB_ERROR_MESSAGES.get(err.errno, f"Database error: {err.msg}"), "error")
    return back_to(tab_from_path())


@app.errorhandler(ValueError)          # int("abc")
@app.errorhandler(ArithmeticError)     # Decimal("abc")
def handle_bad_number(err):
    if request.method != "POST":
        return "Bad request", 400
    flash("Please check the numbers you entered.", "error")
    return back_to(tab_from_path())


# Template filters for display
@app.template_filter("money")
def money(value):
    return "" if value is None else f"${value:,.2f}"


@app.template_filter("day")
def day(value):
    return "—" if value is None else value.strftime("%b %d, %Y")


@app.template_filter("cell")
def cell(value):
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return value


@app.template_filter("column_label")
def column_label(name):
    """Report column names -> headings: 'UnitsSold' -> 'Units Sold'."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)


@app.template_filter("slug")
def slug(value):
    return (value or "").lower().replace(" ", "-")


# =====================================================================
# Data loaders -- one per tab. Each returns the values its template uses.
# =====================================================================
def load_shop():
    filters = {
        "text":      blank_to_none(request.args.get("text")),
        "category":  blank_to_none(request.args.get("category")),
        "size":      blank_to_none(request.args.get("size")),
        "color":     blank_to_none(request.args.get("color")),
        "min_price": to_decimal(request.args.get("min_price")),
        "max_price": to_decimal(request.args.get("max_price")),
        "sort":      blank_to_none(request.args.get("sort")),
    }
    filters["like"] = f"%{filters['text']}%" if filters["text"] else None
    return {
        "filters": filters,
        "products": db.fetch_all(q.SEARCH_PRODUCTS, filters),
        "filter_categories": db.fetch_all(q.FILTER_CATEGORIES),
        "filter_sizes": db.fetch_all(q.FILTER_SIZES),
        "filter_colors": db.fetch_all(q.FILTER_COLORS),
    }


def load_cart():
    cart = db.fetch_all(q.CART_FOR_CUSTOMER, (current_user()["id"],))
    return {"cart": cart, "cart_total": sum(row["LineTotal"] for row in cart),
            "payment_methods": db.PAYMENT_METHODS}


def load_orders():
    cust_id = current_user()["id"]
    items_by_order = defaultdict(list)
    for item in db.fetch_all(q.ORDER_ITEMS_FOR_CUSTOMER, (cust_id,)):
        items_by_order[item["OrderID"]].append(item)
    return {"orders": db.fetch_all(q.ORDERS_FOR_CUSTOMER, (cust_id,)), "order_items": items_by_order}


def load_alterations():
    data = {"services": db.fetch_all(q.ALTERATION_SERVICES)}
    if is_customer():
        data["my_alterations"] = db.fetch_all(q.ALTERATION_ORDERS_FOR_CUSTOMER, (current_user()["id"],))
    return data


def load_board():
    jobs = db.fetch_all(q.ALL_ALTERATION_ORDERS, {"status": None})
    columns = {status: [job for job in jobs if job["Status"] == status] for status in ALTERATION_STATUSES}
    return {"columns": columns, "tailors": db.fetch_all(q.TAILORS)}


def load_products():
    edit_id = request.args.get("edit", type=int)
    no_filters = {key: None for key in ("text", "like", "category", "size", "color", "min_price", "max_price", "sort")}
    return {
        "products": db.fetch_all(q.SEARCH_PRODUCTS, no_filters),
        "categories": db.fetch_all(q.ALL_CATEGORIES),
        "edit_product": db.fetch_one(q.PRODUCT_BY_ID, (edit_id,)) if edit_id else None,
    }


def load_inventory():
    no_filters = {key: None for key in ("text", "like", "category", "size", "color", "min_price", "max_price", "sort")}
    return {
        "low_stock": db.fetch_all(q.LOW_STOCK),
        "suppliers": db.fetch_all(q.ALL_SUPPLIERS),
        "purchases": db.fetch_all(q.SUPPLIER_PURCHASES),
        "products": db.fetch_all(q.SEARCH_PRODUCTS, no_filters),
    }


def load_employees():
    return {"employees": db.fetch_all(q.ALL_EMPLOYEES)}


def load_reports():
    report_key = request.args.get("report", "sales")
    if report_key not in q.REPORTS:
        report_key = "sales"
    title, sql, takeaway = q.REPORTS[report_key]
    return {
        "stats": db.fetch_one(q.DASHBOARD_STATS),
        "reports": q.REPORTS, "report_key": report_key,
        "report_title": title, "report_takeaway": takeaway,
        "report_rows": db.fetch_all(sql),
    }


def load_account():
    if is_customer():
        return {"profile": db.fetch_one(q.CUSTOMER_BY_ID, (current_user()["id"],))}
    if current_user() is None:
        return {"demo_customers": db.fetch_all(q.ALL_CUSTOMERS),
                "demo_employees": db.fetch_all(q.ALL_EMPLOYEES)}
    return {}


LOADERS = {
    "shop": load_shop, "cart": load_cart, "orders": load_orders,
    "alterations": load_alterations, "board": load_board, "products": load_products,
    "inventory": load_inventory, "employees": load_employees, "reports": load_reports,
    "account": load_account,
}


# =====================================================================
# THE ONE PAGE
# =====================================================================
@app.route("/")
def index():
    visible_tabs = [t for t in ui.TABS if can_see(t[4])]
    tab_ids = [t[0] for t in visible_tabs]
    tab = request.args.get("tab", "shop")
    if tab not in tab_ids:
        tab = "shop"
    active = next(t for t in visible_tabs if t[0] == tab)

    page = {
        "user": current_user(), "tab": tab, "tabs": visible_tabs,
        "page_title": active[1], "page_subtitle": active[2],
        "statuses": ALTERATION_STATUSES, "roles": EMPLOYEE_ROLES,
        "cart_count": 0,
    }
    if is_customer():
        page["cart_count"] = db.fetch_one(q.CART_COUNT, (current_user()["id"],))["Items"]
    page.update(LOADERS[tab]())
    return render_template("index.html", **page)


# =====================================================================
# ACCOUNT
# =====================================================================
@app.route("/account/register", methods=["POST"])
def register():
    first, last = form_text("first_name"), form_text("last_name")
    email, phone, password = form_text("email").lower(), form_text("phone"), form_text("password")
    if not (first and last and email and password):
        flash("First name, last name, email and password are required.", "error")
        return back_to("account")
    db.execute(q.INSERT_CUSTOMER, (first, last, email, phone or None, generate_password_hash(password)))
    flash("Account created -- sign in to start shopping.", "success")
    return back_to("account")


@app.route("/account/login", methods=["POST"])
def login():
    email, password = form_text("email").lower(), form_text("password")

    customer = db.fetch_one(q.CUSTOMER_BY_EMAIL, (email,))
    if customer and password_matches(customer["PasswordHash"], password):
        sign_in("customer", customer["CustID"], customer["FirstName"], "Customer")
        flash(f"Welcome back, {customer['FirstName']}!", "success")
        return back_to("shop")

    employee = db.fetch_one(q.EMPLOYEE_BY_EMAIL, (email,))
    if employee and password_matches(employee["PasswordHash"], password):
        sign_in("employee", employee["EmpID"], employee["FirstName"], employee["Role"])
        flash(f"Signed in as {employee['Role']} {employee['FirstName']}.", "success")
        return back_to("reports" if employee["Role"] == "Manager" else "board")

    flash("Email or password is incorrect.", "error")
    return back_to("account")


@app.route("/account/demo-login", methods=["POST"])
def demo_login():
    """Presentation helper: sample accounts have placeholder password hashes."""
    kind, _, raw_id = form_text("account").partition(":")
    if kind == "customer":
        row = db.fetch_one(q.CUSTOMER_BY_ID, (int(raw_id),))
        if row:
            sign_in("customer", row["CustID"], row["FirstName"], "Customer")
            return back_to("shop")
    elif kind == "employee":
        row = db.fetch_one(q.EMPLOYEE_BY_ID, (int(raw_id),))
        if row:
            sign_in("employee", row["EmpID"], row["FirstName"], row["Role"])
            return back_to("reports" if row["Role"] == "Manager" else "board")
    return back_to("account")


@app.route("/account/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You are signed out.", "success")
    return back_to("shop")


@app.route("/account/profile", methods=["POST"])
def update_profile():
    if not is_customer():
        return deny()
    first, last = form_text("first_name"), form_text("last_name")
    if not (first and last):
        flash("First and last name are required.", "error")
        return back_to("account")
    db.execute(q.UPDATE_CUSTOMER_PROFILE, (first, last, form_text("phone") or None, current_user()["id"]))
    session["user"] = {**current_user(), "name": first}
    flash("Profile updated.", "success")
    return back_to("account")


# =====================================================================
# SHOP & CART (customers)
# =====================================================================
@app.route("/shop/add-to-cart", methods=["POST"])
def add_to_cart():
    if not is_customer():
        return deny("Sign in as a customer to shop.")
    quantity = max(1, request.form.get("quantity", 1, type=int))
    db.execute(q.ADD_TO_CART, (current_user()["id"], request.form.get("product_id", type=int), quantity, quantity))
    flash(f"Added to your cart ({quantity}).", "success")
    return back_to_previous_page("shop")


@app.route("/cart/update", methods=["POST"])
def update_cart():
    if not is_customer():
        return deny()
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", 1, type=int)
    if quantity <= 0:
        db.execute(q.REMOVE_FROM_CART, (current_user()["id"], product_id))
    else:
        db.execute(q.UPDATE_CART_QUANTITY, (quantity, current_user()["id"], product_id))
    return back_to("cart")


@app.route("/cart/remove", methods=["POST"])
def remove_from_cart():
    if not is_customer():
        return deny()
    db.execute(q.REMOVE_FROM_CART, (current_user()["id"], request.form.get("product_id", type=int)))
    return back_to("cart")


@app.route("/cart/place-order", methods=["POST"])
def place_order():
    """The complete business transaction -- see db.place_order()."""
    if not is_customer():
        return deny()
    order_id, error = db.place_order(current_user()["id"],
                                     form_text("payment_method"), form_text("card_last_four"))
    if error:
        flash(error, "error")
        return back_to("cart")
    flash(f"Order #{order_id} confirmed! Thank you for shopping at StyleHub.", "success")
    return back_to("orders")


# =====================================================================
# ALTERATIONS (customers request / cancel)
# =====================================================================
@app.route("/alterations/request", methods=["POST"])
def request_alteration():
    if not is_customer():
        return deny("Sign in as a customer to request an alteration.")
    garment = form_text("garment")
    alteration_id = request.form.get("alteration_id", type=int)
    if not garment or not alteration_id:
        flash("Describe the garment and choose a service.", "error")
        return back_to("alterations")
    db.execute(q.INSERT_ALTERATION_ORDER, (current_user()["id"], garment, alteration_id))
    flash("Alteration order received -- track its progress below.", "success")
    return back_to("alterations")


@app.route("/alterations/cancel", methods=["POST"])
def cancel_alteration():
    if not is_customer():
        return deny()
    order_id = request.form.get("alteration_order_id", type=int)
    if db.execute(q.CANCEL_ALTERATION_ORDER, (order_id, current_user()["id"])):
        flash("Alteration order cancelled.", "success")
    else:
        flash("Only orders still marked 'Received' can be cancelled.", "error")
    return back_to("alterations")


# =====================================================================
# WORK BOARD (employees)
# =====================================================================
@app.route("/board/update", methods=["POST"])
def update_alteration():
    if not is_employee():
        return deny()
    status = form_text("status")
    if status not in ALTERATION_STATUSES:
        flash("Unknown status.", "error")
        return back_to("board")
    db.execute(q.UPDATE_ALTERATION_ORDER, {
        "id":     request.form.get("alteration_order_id", type=int),
        "emp_id": request.form.get("emp_id", type=int),        # blank -> None (unassigned)
        "status": status,
        "fee":    Decimal(form_text("fee")),
    })
    flash("Alteration order updated.", "success")
    return back_to("board")


# =====================================================================
# PRODUCTS (manager)
# =====================================================================
@app.route("/products/save", methods=["POST"])
def save_product():
    if not is_manager():
        return deny()
    values = (
        request.form.get("category_id", type=int),
        form_text("product_name"),
        form_text("brand"),
        Decimal(form_text("price")),
        int(form_text("quantity")),
        int(form_text("reorder_point")),
    )
    product_id = request.form.get("product_id", type=int)
    if product_id:
        db.execute(q.UPDATE_PRODUCT, values + (product_id,))
        flash("Product updated.", "success")
    else:
        db.execute(q.INSERT_PRODUCT, values)
        flash("Product added.", "success")
    return back_to("products")


@app.route("/products/delete", methods=["POST"])
def delete_product():
    if not is_manager():
        return deny()
    db.execute(q.DELETE_PRODUCT, (request.form.get("product_id", type=int),))
    flash("Product deleted.", "success")
    return back_to("products")


@app.route("/products/add-category", methods=["POST"])
def add_category():
    if not is_manager():
        return deny()
    db.execute(q.INSERT_CATEGORY, (form_text("category_name"), form_text("size"), form_text("color")))
    flash("Category added.", "success")
    return back_to("products")


# =====================================================================
# INVENTORY & SUPPLIERS (manager)
# =====================================================================
@app.route("/inventory/add-supplier", methods=["POST"])
def add_supplier():
    if not is_manager():
        return deny()
    db.execute(q.INSERT_SUPPLIER, (form_text("supplier_name"), form_text("contact_first"),
                                   form_text("contact_last"), form_text("contact_email")))
    flash("Supplier added.", "success")
    return back_to("inventory")


@app.route("/inventory/update-supplier", methods=["POST"])
def update_supplier():
    if not is_manager():
        return deny()
    db.execute(q.UPDATE_SUPPLIER, (form_text("supplier_name"), form_text("contact_first"),
                                   form_text("contact_last"), form_text("contact_email"),
                                   request.form.get("supplier_id", type=int)))
    flash("Supplier updated.", "success")
    return back_to("inventory")


@app.route("/inventory/add-purchase", methods=["POST"])
def add_purchase():
    if not is_manager():
        return deny()
    db.execute(q.INSERT_SUPPLIER_PURCHASE, (
        request.form.get("supplier_id", type=int),
        request.form.get("product_id", type=int),
        Decimal(form_text("unit_cost")),
        int(form_text("quantity")),
    ))
    flash("Purchase order recorded. Mark it received when the shipment arrives.", "success")
    return back_to("inventory")


@app.route("/inventory/receive", methods=["POST"])
def receive_purchase():
    if not is_manager():
        return deny()
    if db.receive_supplier_purchase(request.form.get("purchase_id", type=int)):
        flash("Shipment received -- inventory updated.", "success")
    else:
        flash("That shipment was already received.", "error")
    return back_to("inventory")


# =====================================================================
# EMPLOYEES (manager)
# =====================================================================
@app.route("/employees/add", methods=["POST"])
def add_employee():
    if not is_manager():
        return deny()
    role, password = form_text("role"), form_text("password")
    if role not in EMPLOYEE_ROLES or not password:
        flash("Choose a role and set a starting password.", "error")
        return back_to("employees")
    db.execute(q.INSERT_EMPLOYEE, (form_text("first_name"), form_text("last_name"),
                                   form_text("email").lower(), generate_password_hash(password), role))
    flash("Employee account created.", "success")
    return back_to("employees")


if __name__ == "__main__":
    # host="0.0.0.0": other computers on your network can open the site too
    # (teammates use http://<your-IP>:<port>). MySQL itself stays private on this PC.
    # Debug mode stays OFF unless STYLEHUB_DEBUG=1, because its error page can run
    # Python in the browser and read environment variables (your DB password).
    app.run(host="0.0.0.0", debug=os.environ.get("STYLEHUB_DEBUG") == "1")
