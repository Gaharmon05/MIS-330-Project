"""
queries.py -- EVERY SQL statement the StyleHub web app runs lives in this file.

How the parameters work (this is what keeps us safe from SQL injection):
  * %s or %(name)s are PLACEHOLDERS. We never paste user input into SQL text.
  * The values are passed separately to cursor.execute(sql, values) and the
    MySQL driver sends them to the database as data, not as SQL code.
  * (In class the sqlite3 examples used ? -- mysql-connector uses %s instead.)
"""

# =====================================================================
# USERS -- login, registration, profiles, employee accounts
# =====================================================================
CUSTOMER_BY_EMAIL = """
    SELECT CustID, FirstName, LastName, Email, PasswordHash
    FROM Customer
    WHERE Email = %s
"""

EMPLOYEE_BY_EMAIL = """
    SELECT EmpID, FirstName, LastName, Email, Role, PasswordHash
    FROM Employee
    WHERE Email = %s
"""

CUSTOMER_BY_ID = """
    SELECT CustID, FirstName, LastName, Email, Phone, CreatedAt
    FROM Customer
    WHERE CustID = %s
"""

EMPLOYEE_BY_ID = """
    SELECT EmpID, FirstName, LastName, Email, Role, CreatedAt
    FROM Employee
    WHERE EmpID = %s
"""

ALL_CUSTOMERS = """
    SELECT CustID, FirstName, LastName, Email
    FROM Customer
    ORDER BY LastName, FirstName
"""

ALL_EMPLOYEES = """
    SELECT EmpID, FirstName, LastName, Email, Role, CreatedAt
    FROM Employee
    ORDER BY Role, LastName
"""

TAILORS = """
    SELECT EmpID, FirstName, LastName
    FROM Employee
    WHERE Role = 'Tailor'
    ORDER BY FirstName
"""

INSERT_CUSTOMER = """
    INSERT INTO Customer (FirstName, LastName, Email, Phone, PasswordHash)
    VALUES (%s, %s, %s, %s, %s)
"""

UPDATE_CUSTOMER_PROFILE = """
    UPDATE Customer
    SET FirstName = %s, LastName = %s, Phone = %s
    WHERE CustID = %s
"""

INSERT_EMPLOYEE = """
    INSERT INTO Employee (FirstName, LastName, Email, PasswordHash, Role)
    VALUES (%s, %s, %s, %s, %s)
"""


# =====================================================================
# PRODUCTS -- search / filter / sort, and manager CRUD
# =====================================================================

# One fixed query handles every search combination.
# A filter that is left blank is sent as NULL, and "%(x)s IS NULL OR ..."
# makes that filter switch itself off. ORDER BY uses CASE so the sort
# choice is also just a parameter (no SQL is built by gluing strings).
SEARCH_PRODUCTS = """
    SELECT p.ProductID, p.ProductName, p.Brand, p.PricePerUnit,
           p.QuantityInStock, p.ReorderPoint,
           c.CategoryID, c.CategoryName, c.Size, c.Color,
           COALESCE(SUM(oi.Quantity), 0) AS UnitsSold
    FROM Product p
    JOIN Category c       ON c.CategoryID = p.CategoryID
    LEFT JOIN OrderItem oi ON oi.ProductID = p.ProductID
    WHERE (%(text)s      IS NULL OR p.ProductName LIKE %(like)s OR p.Brand LIKE %(like)s)
      AND (%(category)s  IS NULL OR c.CategoryName = %(category)s)
      AND (%(size)s      IS NULL OR c.Size         = %(size)s)
      AND (%(color)s     IS NULL OR c.Color        = %(color)s)
      AND (%(min_price)s IS NULL OR p.PricePerUnit >= %(min_price)s)
      AND (%(max_price)s IS NULL OR p.PricePerUnit <= %(max_price)s)
    GROUP BY p.ProductID, c.CategoryID
    ORDER BY
      CASE WHEN %(sort)s = 'price_asc'  THEN p.PricePerUnit END ASC,
      CASE WHEN %(sort)s = 'price_desc' THEN p.PricePerUnit END DESC,
      CASE WHEN %(sort)s = 'popular'    THEN COALESCE(SUM(oi.Quantity), 0) END DESC,
      p.ProductName
"""

# Values for the filter drop-downs
FILTER_CATEGORIES = "SELECT DISTINCT CategoryName FROM Category ORDER BY CategoryName"
FILTER_SIZES      = "SELECT DISTINCT Size  FROM Category ORDER BY Size"
FILTER_COLORS     = "SELECT DISTINCT Color FROM Category ORDER BY Color"

ALL_CATEGORIES = """
    SELECT CategoryID, CategoryName, Size, Color
    FROM Category
    ORDER BY CategoryName, Size, Color
"""

INSERT_CATEGORY = """
    INSERT INTO Category (CategoryName, Size, Color)
    VALUES (%s, %s, %s)
"""

PRODUCT_BY_ID = """
    SELECT ProductID, CategoryID, ProductName, Brand, PricePerUnit,
           QuantityInStock, ReorderPoint
    FROM Product
    WHERE ProductID = %s
"""

INSERT_PRODUCT = """
    INSERT INTO Product (CategoryID, ProductName, Brand, PricePerUnit,
                         QuantityInStock, ReorderPoint)
    VALUES (%s, %s, %s, %s, %s, %s)
"""

UPDATE_PRODUCT = """
    UPDATE Product
    SET CategoryID = %s, ProductName = %s, Brand = %s, PricePerUnit = %s,
        QuantityInStock = %s, ReorderPoint = %s
    WHERE ProductID = %s
"""

# Fails with a foreign-key error if the product has sales or supplier
# history -- the app catches that and explains it to the user.
DELETE_PRODUCT = "DELETE FROM Product WHERE ProductID = %s"


# =====================================================================
# SHOPPING CART  (CartItem: PK = CustID + ProductID)
# =====================================================================
CART_FOR_CUSTOMER = """
    SELECT ci.ProductID, p.ProductName, p.Brand, c.Size, c.Color,
           p.PricePerUnit, ci.Quantity, p.QuantityInStock,
           ci.Quantity * p.PricePerUnit AS LineTotal
    FROM CartItem ci
    JOIN Product p  ON p.ProductID  = ci.ProductID
    JOIN Category c ON c.CategoryID = p.CategoryID
    WHERE ci.CustID = %s
    ORDER BY ci.AddedAt
"""

# Adding the same product again just increases the quantity.
ADD_TO_CART = """
    INSERT INTO CartItem (CustID, ProductID, Quantity)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE Quantity = Quantity + %s
"""

UPDATE_CART_QUANTITY = """
    UPDATE CartItem SET Quantity = %s
    WHERE CustID = %s AND ProductID = %s
"""

REMOVE_FROM_CART = "DELETE FROM CartItem WHERE CustID = %s AND ProductID = %s"


# =====================================================================
# PLACE ORDER -- the complete business transaction (see db.place_order)
# These run together inside ONE transaction: all succeed or none do.
# =====================================================================
CART_ITEMS_SHORT_ON_STOCK = """
    SELECT p.ProductName, ci.Quantity, p.QuantityInStock
    FROM CartItem ci
    JOIN Product p ON p.ProductID = ci.ProductID
    WHERE ci.CustID = %s AND ci.Quantity > p.QuantityInStock
"""

INSERT_ORDER = "INSERT INTO Orders (CustID, OrderAmount) VALUES (%s, 0)"

# Copy the cart into OrderItem, capturing today's price as UnitPrice
COPY_CART_TO_ORDER = """
    INSERT INTO OrderItem (OrderID, ProductID, Quantity, UnitPrice)
    SELECT %s, ci.ProductID, ci.Quantity, p.PricePerUnit
    FROM CartItem ci
    JOIN Product p ON p.ProductID = ci.ProductID
    WHERE ci.CustID = %s
"""

# Update inventory after the sale
DECREASE_STOCK_FOR_ORDER = """
    UPDATE Product p
    JOIN OrderItem oi ON oi.ProductID = p.ProductID
    SET p.QuantityInStock = p.QuantityInStock - oi.Quantity
    WHERE oi.OrderID = %s
"""

SET_ORDER_TOTAL = """
    UPDATE Orders
    SET OrderAmount = (SELECT SUM(Quantity * UnitPrice)
                       FROM OrderItem WHERE OrderID = %s),
        CompletionDate = NOW()
    WHERE OrderID = %s
"""

# Record how the customer paid. The amount is the order total just set above.
INSERT_PAYMENT = """
    INSERT INTO Payment (OrderID, PaymentMethod, CardLastFour, Amount)
    SELECT OrderID, %s, %s, OrderAmount
    FROM Orders
    WHERE OrderID = %s
"""

CLEAR_CART = "DELETE FROM CartItem WHERE CustID = %s"


# =====================================================================
# ORDER HISTORY
# =====================================================================
ORDERS_FOR_CUSTOMER = """
    SELECT o.OrderID, o.OrderDate, o.CompletionDate, o.OrderAmount,
           pay.PaymentMethod, pay.CardLastFour, pay.PaymentDate
    FROM Orders o
    LEFT JOIN Payment pay ON pay.OrderID = o.OrderID   -- LEFT: show the order even if unpaid
    WHERE o.CustID = %s
    ORDER BY o.OrderDate DESC
"""

ORDER_ITEMS_FOR_CUSTOMER = """
    SELECT oi.OrderID, p.ProductName, oi.Quantity, oi.UnitPrice,
           oi.Quantity * oi.UnitPrice AS LineTotal
    FROM OrderItem oi
    JOIN Orders o  ON o.OrderID  = oi.OrderID
    JOIN Product p ON p.ProductID = oi.ProductID
    WHERE o.CustID = %s
"""


# =====================================================================
# ALTERATION ORDERS -- a customer orders an alteration to a garment
# =====================================================================
ALTERATION_SERVICES = """
    SELECT AlterationID, AlterationName, Description, AlterationPrice
    FROM Alteration
    ORDER BY AlterationName
"""

# The service fee starts at the catalog price for that alteration.
INSERT_ALTERATION_ORDER = """
    INSERT INTO AlterationOrder (CustID, AlterationID, GarmentDescription, ServiceFee)
    SELECT %s, AlterationID, %s, AlterationPrice
    FROM Alteration
    WHERE AlterationID = %s
"""

ALTERATION_ORDERS_FOR_CUSTOMER = """
    SELECT ao.AlterationOrderID, ao.GarmentDescription, a.AlterationName,
           ao.ServiceFee, ao.Status, ao.RequestDate, ao.PickupDate,
           CONCAT(e.FirstName, ' ', e.LastName) AS Tailor
    FROM AlterationOrder ao
    JOIN Alteration a     ON a.AlterationID = ao.AlterationID
    LEFT JOIN Employee e  ON e.EmpID = ao.EmpID      -- LEFT: may be unassigned
    WHERE ao.CustID = %s
    ORDER BY ao.RequestDate DESC
"""

# Employee work board. Blank status filter = show all.
ALL_ALTERATION_ORDERS = """
    SELECT ao.AlterationOrderID, ao.GarmentDescription, ao.ServiceFee,
           ao.Status, ao.RequestDate, ao.PickupDate, ao.EmpID,
           a.AlterationName,
           CONCAT(cu.FirstName, ' ', cu.LastName) AS CustomerName,
           cu.Phone
    FROM AlterationOrder ao
    JOIN Customer cu   ON cu.CustID = ao.CustID
    JOIN Alteration a  ON a.AlterationID = ao.AlterationID
    WHERE (%(status)s IS NULL OR ao.Status = %(status)s)
    ORDER BY FIELD(ao.Status, 'Received', 'In Progress', 'Ready for Pickup', 'Completed'),
             ao.RequestDate
"""

# PickupDate is stamped the first time an order is marked Completed.
# The CHECK constraint in the table rejects a status past 'Received'
# when no tailor (EmpID) is assigned.
UPDATE_ALTERATION_ORDER = """
    UPDATE AlterationOrder
    SET EmpID = %(emp_id)s,
        Status = %(status)s,
        ServiceFee = %(fee)s,
        PickupDate = CASE WHEN %(status)s = 'Completed'
                          THEN COALESCE(PickupDate, NOW())
                          ELSE NULL END
    WHERE AlterationOrderID = %(id)s
"""

# Customers may cancel only while the order is still 'Received'
CANCEL_ALTERATION_ORDER = """
    DELETE FROM AlterationOrder
    WHERE AlterationOrderID = %s AND CustID = %s AND Status = 'Received'
"""


# =====================================================================
# INVENTORY & SUPPLIERS
# =====================================================================
LOW_STOCK = "SELECT * FROM vw_LowStockReorder"

ALL_SUPPLIERS = """
    SELECT SupplierID, SupplierName, ContactFirstName, ContactLastName, ContactEmail
    FROM Supplier
    ORDER BY SupplierName
"""

INSERT_SUPPLIER = """
    INSERT INTO Supplier (SupplierName, ContactFirstName, ContactLastName, ContactEmail)
    VALUES (%s, %s, %s, %s)
"""

UPDATE_SUPPLIER = """
    UPDATE Supplier
    SET SupplierName = %s, ContactFirstName = %s, ContactLastName = %s, ContactEmail = %s
    WHERE SupplierID = %s
"""

SUPPLIER_PURCHASES = """
    SELECT sp.PurchaseID, s.SupplierName, sp.PurchaseDate, sp.ReceivedDate,
           SUM(spi.Quantity)  AS TotalUnits,
           SUM(spi.LineTotal) AS TotalCost
    FROM SupplierPurchase sp
    JOIN Supplier s               ON s.SupplierID  = sp.SupplierID
    JOIN SupplierPurchaseItem spi ON spi.PurchaseID = sp.PurchaseID
    GROUP BY sp.PurchaseID, s.SupplierName, sp.PurchaseDate, sp.ReceivedDate
    ORDER BY sp.ReceivedDate IS NOT NULL, sp.PurchaseDate DESC, sp.PurchaseID DESC
"""

SUPPLIER_PURCHASE_ITEMS = """
    SELECT spi.PurchaseID, p.ProductName, c.Size, c.Color,
           spi.Quantity, spi.PricePerUnit, spi.LineTotal
    FROM SupplierPurchaseItem spi
    JOIN Product p  ON p.ProductID  = spi.ProductID
    JOIN Category c ON c.CategoryID = p.CategoryID
    ORDER BY spi.PurchaseID, p.ProductName
"""

INSERT_SUPPLIER_PURCHASE = """
    INSERT INTO SupplierPurchase (SupplierID, PurchaseDate)
    VALUES (%s, CURDATE())
"""

INSERT_SUPPLIER_PURCHASE_ITEM = """
    INSERT INTO SupplierPurchaseItem (PurchaseID, ProductID, PricePerUnit, Quantity)
    VALUES (%s, %s, %s, %s)
"""

# Receiving a shipment (see db.receive_supplier_purchase) -- one transaction.
# "ReceivedDate IS NULL" stops the same shipment being received twice.
MARK_PURCHASE_RECEIVED = """
    UPDATE SupplierPurchase
    SET ReceivedDate = CURDATE()
    WHERE PurchaseID = %s AND ReceivedDate IS NULL
"""

ADD_RECEIVED_STOCK = """
    UPDATE Product p
    JOIN SupplierPurchaseItem spi ON spi.ProductID = p.ProductID
    SET p.QuantityInStock = p.QuantityInStock + spi.Quantity
    WHERE spi.PurchaseID = %s
"""


# =====================================================================
# MANAGER DASHBOARD -- four headline numbers (scalar subqueries)
# =====================================================================
DASHBOARD_STATS = """
    SELECT
      (SELECT COALESCE(SUM(OrderAmount), 0) FROM Orders)            AS SalesRevenue,
      (SELECT COALESCE(SUM(ServiceFee), 0)  FROM AlterationOrder)   AS AlterationRevenue,
      (SELECT COUNT(*) FROM AlterationOrder WHERE Status <> 'Completed') AS OpenAlterations,
      (SELECT COUNT(*) FROM Product WHERE QuantityInStock <= ReorderPoint) AS LowStockCount
"""

CART_COUNT = "SELECT COALESCE(SUM(Quantity), 0) AS Items FROM CartItem WHERE CustID = %s"


# =====================================================================
# MANAGER REPORTS -- the six views from 03_reports.sql
# key: (title, SQL, what it tells the manager)
# =====================================================================
REPORTS = {
    "sales": (
        "Product Sales Performance",
        "SELECT * FROM vw_ProductSalesPerformance",
        "Top rows drive revenue and profit -- keep them stocked. Products with "
        "few or zero sales but high stock are tying up cash; consider a markdown.",
    ),
    "reorder": (
        "Low-Stock Reorder Report",
        "SELECT * FROM vw_LowStockReorder",
        "Every row is at or below its reorder point. Order SuggestedOrderQty from "
        "LastSupplier; QtyOnOrder prevents double-ordering.",
    ),
    "repeat": (
        "Repeat Customer Value",
        "SELECT * FROM vw_RepeatCustomers",
        "Best repeat customers are loyalty-discount candidates. A high "
        "DaysSinceLastOrder means the customer may be slipping away.",
    ),
    "tailors": (
        "Tailor Workload & Alteration Revenue",
        "SELECT * FROM vw_TailorWorkload",
        "Assign new alteration orders to the tailor with the fewest OpenJobs. "
        "DiscountsGiven shows revenue lost below list price.",
    ),
    "monthly": (
        "Monthly Revenue (Products vs. Alterations)",
        "SELECT * FROM vw_MonthlyRevenue",
        "Spot strong and weak months for staffing and buying. A rising "
        "AlterationPct could justify another tailor.",
    ),
    "services": (
        "Alteration Service Demand",
        "SELECT * FROM vw_AlterationServiceDemand",
        "The most-requested services show what to train tailors on and advertise. "
        "A popular service with high AvgDaysToComplete is a bottleneck.",
    ),
}
