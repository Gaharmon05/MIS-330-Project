# StyleHub — Clothing Retail & Alteration Management System

MIS 330 Group Project 1 (Project #5). A one-page Python (Flask) web app on a MySQL database.

## What's here

```
Files/
  DATABASE/
    01_schema.sql          creates the StyleHub database (tables, keys, constraints)
    02_sample_data.sql     loads sample rows into every table
    03_reports.sql         the manager reports (6 views + 2 stored procedures)
  WEBAPP/
    Python_Version/        Flask builds each page on the server (Python + HTML templates + CSS)
```

| File (in `Python_Version/`) | What it does |
|---|---|
| `queries.py` | **Every SQL statement the app runs**, all parameterized (`%s`) |
| `db.py` | Connection → cursor → commit/rollback → close (the class pattern), plus the three multi-step transactions (place an order, create a supplier purchase order, receive a shipment) |

Also in the project root:
- `How_Python_Connects_to_SQL.md`: study guide on how the Python code talks to MySQL, with the order transaction explained line by line
- `StyleHub_Presentation.pptx`: the class presentation

## Getting the website running

You need **MySQL 8.0.16 or newer** (with MySQL Workbench) and **Python 3.10 or newer**.
The commands below are for a PowerShell terminal (VS Code: *Terminal → New Terminal*), starting from the project folder.

### 1. Create the database (once)
In MySQL Workbench, open and run these three scripts **in this order**:

1. `Files/DATABASE/01_schema.sql`
2. `Files/DATABASE/02_sample_data.sql`
3. `Files/DATABASE/03_reports.sql`

Running `01_schema.sql` again wipes the database and starts fresh, so run all three again after it.

### 2. Install the Python packages (once)
```powershell
python -m pip install -r Files\WEBAPP\Python_Version\requirements.txt
```
This installs `flask` and `mysql-connector-python`.

### 3. Give the app your MySQL password
The password is **never written in the code**. `db.py` reads it from an environment variable.

Set it for the current terminal only:
```powershell
$env:STYLEHUB_DB_PASSWORD = "your MySQL password"
```
Or set it permanently. Then close and reopen VS Code completely so new terminals can see it:
```powershell
setx STYLEHUB_DB_PASSWORD "your MySQL password"
```
The app logs in as `root` by default. To use a different MySQL user, also set `STYLEHUB_DB_USER`.

### 4. Start the website

```powershell
cd Files\WEBAPP\Python_Version
python app.py
```
Then open http://127.0.0.1:5000

Leave the terminal open while you use the site. Press **Ctrl+C** in it to stop the server.

> **Open the site from the address above.** Don't double-click the `.html` files.
> Opened as files, they show raw `{{ ... }}` template code.

### 5. Sign in
Click **Sign in → Demo sign-in** and pick an account, such as Ava Johnson (customer) or Grace Lee (manager).
The sample accounts have placeholder passwords, so the demo picker is the way in.
Accounts you register in the app get real, hashed passwords and use the normal login form.

### Letting teammates open your copy
The server accepts connections from other computers on the **same network**:

1. Run `ipconfig` and note your **IPv4 Address** (for example `192.168.1.42`).
2. When Windows asks whether to let Python through the firewall, allow **Private networks** only.
3. Teammates open `http://192.168.1.42:5000`.

Teammates only talk to Flask; your MySQL password and port 3306 stay on your computer.
Campus Wi-Fi often blocks device-to-device connections. If it does, each teammate can run their own copy using steps 1–4.

### Troubleshooting

| What you see | Fix |
|---|---|
| A page saying the database can't be reached | Make sure MySQL is running, the password from step 3 is right, and the three scripts were run |
| `ModuleNotFoundError: No module named 'flask'` | Run step 2 again |
| Page shows `{% ... %}` / `{{ ... }}` text | You opened the file directly. Use the address from step 4 |
| Need the detailed Flask error page while fixing a bug | Run `$env:STYLEHUB_DEBUG = "1"` before starting. **Never** do this while teammates are connected: that page can run code on your computer |

## Demo script

| Sign in as | Try this |
|---|---|
| Guest | Shop: search "Northline", filter by category/size/color/price, sort by price or popularity |
| Customer (Ava Johnson) | Add to cart → Cart → choose a payment method → **Pay & place order** (the complete business transaction) → order confirmation → Orders shows how it was paid. Alterations: request one for any garment and follow its progress stepper |
| Manager (Grace Lee) | Reports: KPI tiles and the 6 reports. Work board: assign a tailor and move a job between columns. Products: add/edit/delete. Inventory: low stock, create a supplier purchase order with several products, **Mark received** (stock goes up for every product on it). Employees: create accounts |

**Database business rule:** on the Work board, try moving an unassigned job to "In Progress".
MySQL's `CHECK (Status = 'Received' OR EmpID IS NOT NULL)` rejects it and the app explains why.
A second rule lives on `Payment`: a credit or debit card payment must store the card's last 4 digits.

## Requirements coverage

| Requirement (Project #5) | Where it is |
|---|---|
| Registration, login, customer profiles, employee accounts | Account tab; Employees tab (manager) |
| Add / edit / delete / view products, categories, size, color, brand, price | Shop tab; Products tab (manager) |
| Search by name or brand; filter by category, size, color, price; sort by price or popularity | Shop tab (`SEARCH_PRODUCTS`) |
| Shopping cart, order placement, confirmation, order history | Cart and Orders tabs (`db.place_order`) |
| Payment recording | Checkout asks how the customer pays; a `Payment` row is saved in the same transaction as the order |
| Track quantities, update after sales, record incoming stock, below-reorder list | Inventory tab; stock drops when an order is placed |
| Request alterations, type and fee, assign employee, status, pickup date | Alterations tab (customer); Work board (staff) |
| Supplier info, supplier purchases, stock rises when received | Inventory tab. One `SupplierPurchase` (the order) has many `SupplierPurchaseItem` rows (the products), like `Orders`/`OrderItem` |
| Five reports: 3+ JOINs, 3+ aggregates, GROUP BY + HAVING, a manager decision | `03_reports.sql`; Reports tab. There are six: Report 6 (Alteration Service Demand) matches the instructor's "alteration service performance" example |
| At least 4–5 sample rows in every table | `02_sample_data.sql` |
| ERD and relational schema | `Project Reference Materials (ERD)/ERD v2 (claude).png` and `Relational Schema v2(claude).png` (the originals are kept) |

## Path of one request (Place order)

| Step | What happens |
|---|---|
| Browser | form posts to `/cart/place-order` with the payment method |
| Python route | `app.py` `place_order()` |
| Transaction | `db.place_order()`: one connection, one commit |
| SQL (`queries.py`) | stock check, `INSERT_ORDER`, `COPY_CART_TO_ORDER`, `DECREASE_STOCK_FOR_ORDER`, `SET_ORDER_TOTAL`, `INSERT_PAYMENT`, `CLEAR_CART` |
| Back to browser | redirect to `/?tab=orders` with a confirmation message |

## Schema note: AlterationOrder

`AlterationOrder` models a **customer ordering an alteration to a piece of clothing**. The garment may
have been bought at StyleHub or anywhere else. It links to `Customer`, `Alteration` (the service) and
`Employee` (the tailor), and **not** to a sales order. `GarmentDescription` describes the item.

## Schema note: Payment

`Payment` records how each order was paid (credit card, debit card, cash or gift card), the amount
and the date. `OrderID` is `UNIQUE`, so each order has exactly one payment (one-to-one). Only the last
4 digits of a card are stored, never the full number.
