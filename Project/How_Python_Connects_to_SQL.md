# How StyleHub's Python Connects to MySQL

A study guide for presenting the StyleHub project (MIS 330, Project #5).
Part 1 explains the whole system at a high level. Part 2 walks through one piece of code line by line:
**placing an order**, the project's complete business transaction.

---

## Part 1: The big picture

### The one idea to remember

MySQL only understands SQL. Python cannot "reach into" the database. It has to **send a SQL
statement as text** over a connection, the same way you type one into MySQL Workbench, and then
read back what MySQL returns. That is why there are SQL statements inside our Python files: they
are the messages Python sends to MySQL.

### The four layers

```
 ┌──────────────┐   click / form    ┌──────────────┐   picks the SQL   ┌──────────────┐
 │   Browser    │ ────────────────▶ │  app.py      │ ────────────────▶ │  queries.py  │
 │  (the page)  │                   │  (routes)    │                   │  (all SQL)   │
 └──────────────┘                   └──────┬───────┘                   └──────────────┘
        ▲                                  │ SQL + values
        │ HTML page                        ▼
        │                           ┌──────────────┐   SQL over a      ┌──────────────┐
        └────────────────────────── │   db.py      │ ────────────────▶ │    MySQL     │
              rows become the page  │  (bridge)    │ ◀──────────────── │  (StyleHub)  │
                                    └──────────────┘   rows back       └──────────────┘
```

| Layer | File | Job | How to say it in the presentation |
|---|---|---|---|
| Page | `templates/` | Shows data and collects clicks and form input | "This is what the user sees." |
| Routes | `app.py` | Decides **which** SQL to run and **with what values** | "Each button maps to a route." |
| SQL | `queries.py` | Holds **every** SQL statement the app runs, in one place | "All of our SQL lives here." |
| Bridge | `db.py` | Opens the connection, runs the SQL, commits or rolls back, closes | "This is the only file that talks to MySQL." |

The database itself is built by the three scripts in `Files/DATABASE/`:

| Script | What it does | Deliverable it satisfies |
|---|---|---|
| `01_schema.sql` | Creates the 13 tables, primary keys, foreign keys and constraints | "SQL queries you use to create this database" |
| `02_sample_data.sql` | Loads sample rows into every table, parents before children | "SQL queries you use to load the data" |
| `03_reports.sql` | Creates the report views (the Task 2 business reports) | "SQL queries you use to conduct data analysis" |

### The path of one request

Every feature follows the same five steps. Example: a customer clicks **Add to cart**.

1. **Browser → route.** The form posts to `/shop/add-to-cart`, handled by `add_to_cart()` in `app.py`.
2. **Route → SQL.** The route picks `ADD_TO_CART` from `queries.py` and gathers the values: the
   signed-in customer's ID, the product ID and the quantity.
3. **SQL → MySQL.** `db.execute()` opens a connection, sends the SQL and the values, and commits.
4. **MySQL does the work.** It inserts the `CartItem` row and enforces every rule from
   `01_schema.sql`: the foreign keys must point at a real customer and product, and the quantity must
   pass `CHECK (Quantity > 0)`.
5. **Back to the page.** The route redirects to the shop with the message "Added to your cart."

Reading data works the same way. `db.fetch_all()` runs a SELECT and returns the rows as a list of
dictionaries (`row["ProductName"]`), and the page loops over that list to draw the product cards.

### Three ideas from MIS 330 that the code uses

**1. The connection-cursor-transaction pattern** (*Scripting Data Loads* deck). `db.py` uses it
for every statement:

| Class term | What it means | Where it is in `db.py` |
|---|---|---|
| Connection | The bridge between Python and the database | `conn = mysql.connector.connect(**DB_CONFIG)` |
| Cursor | The object that executes SQL statements | `cur = conn.cursor()` then `cur.execute(sql, params)` |
| Transaction | All changes are saved together or undone together | `conn.commit()` on success, `conn.rollback()` on failure |
| Always close | Close the connection whether the work succeeds or fails | `conn.close()` inside `finally:` |

The class examples use `sqlite3`. We use `mysql.connector` because our database is MySQL. The
pattern is identical; only the import and the connection line change.

**2. Parameterized queries.** The SQL in `queries.py` contains `%s` placeholders instead of
real values:

```python
ADD_TO_CART = """
    INSERT INTO CartItem (CustID, ProductID, Quantity)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE Quantity = Quantity + %s
"""
```

The values are passed **separately**: `cur.execute(sql, (cust_id, product_id, qty, qty))`. The
connector sends the values as data, never as SQL code, so text a user types into a form can never
change what the query does. This prevents **SQL injection**. (The class decks write `?`
placeholders because `sqlite3` uses `?`; `mysql.connector` uses `%s`.)

**3. Constraint violations are signals.** The class deck says load failures are "design
feedback." Our app relies on that: MySQL enforces the business rules, and Python just reports
them. For example, `AlterationOrder` has `CHECK (Status = 'Received' OR EmpID IS NOT NULL)`. If an
employee moves an unassigned alteration to "In Progress", MySQL rejects it, `db.py` rolls back, and
the page explains: "an alteration order needs a tailor before it can move past 'Received'." The rule
lives in the database, so no part of the app can break it.

### The reports (Task 2)

Each report in `03_reports.sql` is saved as a **view**. A view is a stored SELECT with all the
JOINs, aggregates, GROUP BY and HAVING inside it. Python only runs `SELECT * FROM vw_TailorWorkload`,
so the analysis happens in MySQL and the Reports tab just displays the result.

---

## Part 2: One example in detail: placing an order

The assignment asks us to "demonstrate at least one complete business transaction." Placing an
order is ours, and it is the best single example of Python driving SQL because it uses everything
from the *Scripting Data Loads* deck at once:

- the connection-cursor-transaction pattern,
- **one transaction across several related tables**,
- writing **parent rows before child rows** (`Orders` before `OrderItem` and `Payment`),
- `commit()` on success and `rollback()` on failure.

### What the customer does

On the **Cart** page the customer picks a payment method and clicks **Pay & place order**. The
form posts to `/cart/place-order`. The route (`app.py`, `place_order()`) reads the payment choice
and calls one function: `db.place_order(cust_id, payment_method, card_last_four)`.

### The code (`db.py`, lines 82–128)

```python
def place_order(cust_id, payment_method, card_last_four=None):
    # (payment details are checked first; no database work yet)

    conn = get_connection()                                   # CONNECTION
    try:
        cur = conn.cursor(dictionary=True)                    # CURSOR

        # 1. Make sure there is enough stock for everything in the cart
        cur.execute(q.CART_ITEMS_SHORT_ON_STOCK, (cust_id,))
        short = cur.fetchall()
        if short:
            return None, "Not enough stock: ..."

        # 2. Create the order header (the PARENT row)
        cur.execute(q.INSERT_ORDER, (cust_id,))
        order_id = cur.lastrowid                              # MySQL's new OrderID

        # 3. Copy cart rows into OrderItem (CHILD rows that point at the order)
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

        conn.commit()                                         # TRANSACTION: save all 7
        return order_id, None
    except mysql.connector.Error as err:
        conn.rollback()                                       # TRANSACTION: undo all
        return None, f"Order failed and was rolled back: {err.msg}"
    finally:
        conn.close()                                          # ALWAYS close
```

### What each step sends to MySQL

| Step | SQL (from `queries.py`) | Table(s) touched | Why |
|---|---|---|---|
| 1 | `CART_ITEMS_SHORT_ON_STOCK` | `CartItem` JOIN `Product` (read) | Stop before writing anything if stock is too low |
| 2 | `INSERT_ORDER` | `Orders` (insert) | The parent row. `cur.lastrowid` returns its new `OrderID` |
| 3 | `COPY_CART_TO_ORDER` | `OrderItem` (insert, using `INSERT ... SELECT`) | Child rows. Each stores `UnitPrice` so later price changes don't rewrite history |
| 4 | `DECREASE_STOCK_FOR_ORDER` | `Product` (update, joined to `OrderItem`) | Requirement: "update inventory after each sale" |
| 5 | `SET_ORDER_TOTAL` | `Orders` (update, using `SUM()`) | The total comes from the items, so it is always consistent |
| 6 | `INSERT_PAYMENT` | `Payment` (insert) | Requirement: "payment recording". One payment per order (`OrderID` is `UNIQUE`) |
| 7 | `CLEAR_CART` | `CartItem` (delete) | The cart becomes the order |

Five tables change in one request: `Orders`, `OrderItem`, `Product`, `Payment` and `CartItem`.

### Why the order of steps matters

`OrderItem.OrderID` and `Payment.OrderID` are **foreign keys** to `Orders`. MySQL will not accept a
child row whose parent doesn't exist yet, so the order must be inserted first (step 2) and its new ID
passed to the child inserts (steps 3 and 6). This is the same rule the class deck teaches for loading
data: **parent tables before child tables**.

### Why it is one transaction

All seven statements run on **one connection** and are saved by **one** `commit()`. If anything
fails partway, `rollback()` undoes every earlier step. Examples of failures:

- stock goes negative and breaks `CHECK (QuantityInStock >= 0)`,
- a card payment arrives without its last 4 digits and breaks the Payment table's CHECK,
- the connection drops.

Without a single transaction, a failure at step 6 would leave an order with items and reduced
inventory but no payment, and the customer's cart would still be full. With it, the database is
either fully updated or untouched. The class deck's "Think About It" question makes the same point:
committing inside a loop leaves a half-loaded database, while one commit at the end makes the work
**atomic**.

### What the customer sees

- **Success:** the route shows "Order #13 confirmed!" and opens the Orders page. That page reads the
  new order back with a JOIN across `Orders`, `OrderItem`, `Product` and `Payment`.
- **Failure:** the customer stays on the Cart page with the error message. Nothing was saved.

### How to verify it in MySQL Workbench (the class's "post-load verification" step)

After placing an order in the app, run:

```sql
SELECT o.OrderID, o.OrderAmount, p.PaymentMethod, p.Amount,
       COUNT(oi.ProductID) AS ItemLines
FROM Orders o
JOIN Payment   p  ON p.OrderID  = o.OrderID
JOIN OrderItem oi ON oi.OrderID = o.OrderID
GROUP BY o.OrderID, o.OrderAmount, p.PaymentMethod, p.Amount
ORDER BY o.OrderID DESC
LIMIT 1;
```

The newest order should show matching `OrderAmount` and `Amount`, and its item lines. This is a good
live demo: place an order in the browser, then show the rows in Workbench.

---

## Quick answers for likely questions

**Why is there SQL inside the Python files?**
MySQL only understands SQL. Python sends each statement as text through the connection. We keep
every statement in `queries.py` so the SQL is in one labeled place.

**What is a cursor?**
The object that executes SQL statements and holds the results until Python reads them
(`fetchall()`). The connection is the link to the database; the cursor does the work over it.

**Why `%s` instead of putting values into the SQL string?**
The values travel separately from the SQL, so user input can't change the query. That prevents
SQL injection. It is called a parameterized query.

**What happens if MySQL rejects a statement?**
`db.py` calls `rollback()` so nothing is half-saved, and the route shows a readable message. For
example, a foreign key error (errno 1452) or a CHECK failure (errno 3819) becomes a sentence instead
of a crash.

**Why not use Polars?**
In class, Polars reads and cleans CSV files *before* they are loaded into a database. Our sample
data is loaded by `02_sample_data.sql`, a SQL script, because the deliverable asks for the
data-loading queries as a SQL script. The web app itself only moves a few rows per click, so plain
lists of rows are all it needs. All aggregation is done in SQL, which is the part being graded.
