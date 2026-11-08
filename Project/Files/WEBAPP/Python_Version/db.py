"""
db.py -- the bridge between Python and MySQL.

Follows the class "Connection - Cursor - Transaction" pattern:
  Connection  = the link to the StyleHub database
  Cursor      = runs one SQL statement and hands back the rows
  Transaction = commit() saves the changes, rollback() undoes them
  ...and the connection is ALWAYS closed in a finally block.
"""
import os

import mysql.connector

import queries as q

# Connection settings. Change them here, or set the environment variables
# STYLEHUB_DB_HOST / _USER / _PASSWORD / _NAME before running the app.
DB_CONFIG = {
    "host":     os.environ.get("STYLEHUB_DB_HOST", "localhost"),
    "user":     os.environ.get("STYLEHUB_DB_USER", "root"),
    "password": os.environ.get("STYLEHUB_DB_PASSWORD", ""),
    "database": os.environ.get("STYLEHUB_DB_NAME", "StyleHub"),
}

# Error type the routes catch to show a friendly message
DatabaseError = mysql.connector.Error

# Payment choices at checkout (must match the ENUM in the Payment table)
PAYMENT_METHODS = ["Credit Card", "Debit Card", "Cash", "Gift Card"]
CARD_METHODS = ["Credit Card", "Debit Card"]


def get_connection():
    """Open a new connection to the StyleHub database."""
    return mysql.connector.connect(**DB_CONFIG)


# ---------------------------------------------------------------------
# Reading data (SELECT)
# ---------------------------------------------------------------------
def fetch_all(sql, params=()):
    """Run a SELECT and return every row as a dict, e.g. row['ProductName']."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)          # values are sent separately -> safe
        return cur.fetchall()
    finally:
        conn.close()


def fetch_one(sql, params=()):
    """Run a SELECT and return the first row (or None)."""
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


# ---------------------------------------------------------------------
# Changing data (INSERT / UPDATE / DELETE)
# ---------------------------------------------------------------------
def execute(sql, params=()):
    """Run one INSERT/UPDATE/DELETE. Commit on success, roll back on failure.
    Returns the number of rows affected."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount
    except mysql.connector.Error:
        conn.rollback()
        raise                              # let the route show the error
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Multi-step business transactions
# Several statements share ONE connection and ONE commit, so the
# database never ends up half-updated.
# ---------------------------------------------------------------------
def place_order(cust_id, payment_method, card_last_four=None):
    """Turn a customer's cart into a paid order.
    Returns (order_id, None) on success or (None, error_message)."""
    # Check the payment details before touching the database
    if payment_method not in PAYMENT_METHODS:
        return None, "Choose a payment method."
    if payment_method in CARD_METHODS:
        if not (card_last_four and len(card_last_four) == 4 and card_last_four.isdigit()):
            return None, "Enter the last 4 digits of the card."
    else:
        card_last_four = None              # only cards have card digits

    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)

        # 1. Make sure there is enough stock for everything in the cart
        cur.execute(q.CART_ITEMS_SHORT_ON_STOCK, (cust_id,))
        short = cur.fetchall()
        if short:
            names = ", ".join(f"{r['ProductName']} (only {r['QuantityInStock']} left)" for r in short)
            return None, f"Not enough stock: {names}"

        # 2. Create the order header
        cur.execute(q.INSERT_ORDER, (cust_id,))
        order_id = cur.lastrowid

        # 3. Copy cart rows into OrderItem (price captured at time of sale)
        cur.execute(q.COPY_CART_TO_ORDER, (order_id, cust_id))
        if cur.rowcount == 0:
            conn.rollback()
            return None, "Your cart is empty."

        # 4. Update inventory, 5. set the order total,
        # 6. record the payment, 7. empty the cart
        cur.execute(q.DECREASE_STOCK_FOR_ORDER, (order_id,))
        cur.execute(q.SET_ORDER_TOTAL, (order_id, order_id))
        cur.execute(q.INSERT_PAYMENT, (payment_method, card_last_four, order_id))
        cur.execute(q.CLEAR_CART, (cust_id,))

        conn.commit()                      # all seven steps saved together
        return order_id, None
    except mysql.connector.Error as err:
        conn.rollback()                    # undo every step
        return None, f"Order failed and was rolled back: {err.msg}"
    finally:
        conn.close()


def create_supplier_purchase(supplier_id, items):
    """Create one purchase order with its products. Returns the new PurchaseID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(q.INSERT_SUPPLIER_PURCHASE, (supplier_id,))
        purchase_id = cur.lastrowid
        for product_id, unit_cost, quantity in items:
            cur.execute(q.INSERT_SUPPLIER_PURCHASE_ITEM, (purchase_id, product_id, unit_cost, quantity))

        conn.commit()
        return purchase_id
    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def receive_supplier_purchase(purchase_id):
    """Mark a supplier shipment as received AND add it to inventory.
    Returns True if it was received, False if it already had been."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(q.MARK_PURCHASE_RECEIVED, (purchase_id,))
        if cur.rowcount == 0:              # already received (or bad id)
            conn.rollback()
            return False
        cur.execute(q.ADD_RECEIVED_STOCK, (purchase_id,))
        conn.commit()
        return True
    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        conn.close()
