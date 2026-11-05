-- =====================================================================
-- StyleHub Database - Task 2: Business Report Queries (MySQL 8.0+)
-- Run after 01_schema.sql and 02_sample_data.sql
--
-- Each report is saved as a VIEW so the web app can pull it with a
-- plain  SELECT * FROM <view>;  from C# or Python.
-- Reports 3 and 5 also have a stored procedure for app-supplied filters.
--
-- Requirement checklist (the assignment asks for five; Report 6 is an
-- extra that matches the instructor's "alteration service performance"
-- example report)
--   JOINs (need 3+) ............ Reports 1, 2, 3, 4, 5, 6
--   Aggregates (need 3+) ....... Reports 1, 2, 3, 4, 5, 6
--   GROUP BY + HAVING (need 1+)  Reports 3, 4
--   Manager decision (need 1+) . Report 2 (reorder) - all six support one
-- =====================================================================
USE StyleHub;

-- ---------------------------------------------------------------------
-- REPORT 1: Product Sales Performance
-- Question: Which products earn the most, and which are not selling?
-- Uses: JOIN (Product, Category, OrderItem, SupplierPurchase),
--       SUM, COUNT, AVG, GROUP BY
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_ProductSalesPerformance AS
SELECT
    p.ProductID,
    p.ProductName,
    p.Brand,
    c.CategoryName,
    p.PricePerUnit,
    COALESCE(SUM(oi.Quantity), 0)                    AS UnitsSold,
    COUNT(DISTINCT oi.OrderID)                       AS OrdersContaining,
    COALESCE(SUM(oi.Quantity * oi.UnitPrice), 0)     AS Revenue,
    cost.AvgUnitCost,
    COALESCE(SUM(oi.Quantity * (oi.UnitPrice - cost.AvgUnitCost)), 0)
                                                     AS GrossProfit,
    p.QuantityInStock
FROM Product p
JOIN Category c
    ON c.CategoryID = p.CategoryID
LEFT JOIN OrderItem oi                       -- LEFT keeps never-sold products
    ON oi.ProductID = p.ProductID
LEFT JOIN (                                  -- weighted avg cost from suppliers
    SELECT ProductID,
           ROUND(SUM(TotalCost) / SUM(Quantity), 2) AS AvgUnitCost
    FROM SupplierPurchase
    GROUP BY ProductID
) cost
    ON cost.ProductID = p.ProductID
GROUP BY p.ProductID, p.ProductName, p.Brand, c.CategoryName,
         p.PricePerUnit, cost.AvgUnitCost, p.QuantityInStock
ORDER BY Revenue DESC;

-- Manager takeaway: Top rows are the products driving revenue and profit
-- (keep them stocked, feature them on the home page). Rows with
-- UnitsSold = 0 or very low but high QuantityInStock are tying up cash;
-- consider a markdown/promotion or stop reordering them.


-- ---------------------------------------------------------------------
-- REPORT 2: Low-Stock Reorder Report   << MANAGER DECISION REPORT >>
-- Question: What do I need to reorder today, from whom, how many,
--           and what will it cost?
-- Uses: JOIN (Product, Category, SupplierPurchase, Supplier),
--       SUM, MAX, GROUP BY
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_LowStockReorder AS
SELECT
    p.ProductID,
    p.ProductName,
    p.Brand,
    c.CategoryName,
    c.Size,
    c.Color,
    p.QuantityInStock,
    p.ReorderPoint,
    COALESCE(onord.QtyOnOrder, 0)                         AS QtyOnOrder,
    s.SupplierName                                        AS LastSupplier,
    s.ContactEmail                                        AS SupplierEmail,
    lastp.PricePerUnit                                    AS LastUnitCost,
    -- Restock to 2x the reorder point, minus stock already on hand/on order
    GREATEST(p.ReorderPoint * 2 - p.QuantityInStock
             - COALESCE(onord.QtyOnOrder, 0), 0)          AS SuggestedOrderQty,
    GREATEST(p.ReorderPoint * 2 - p.QuantityInStock
             - COALESCE(onord.QtyOnOrder, 0), 0)
        * lastp.PricePerUnit                              AS EstimatedCost
FROM Product p
JOIN Category c
    ON c.CategoryID = p.CategoryID
LEFT JOIN (                                  -- most recent purchase per product
    SELECT sp.*
    FROM SupplierPurchase sp
    JOIN (SELECT ProductID, MAX(PurchaseDate) AS LastDate
          FROM SupplierPurchase
          WHERE ReceivedDate IS NOT NULL
          GROUP BY ProductID) m
      ON m.ProductID = sp.ProductID AND m.LastDate = sp.PurchaseDate
    WHERE sp.ReceivedDate IS NOT NULL
) lastp
    ON lastp.ProductID = p.ProductID
LEFT JOIN Supplier s
    ON s.SupplierID = lastp.SupplierID
LEFT JOIN (                                  -- open purchase orders
    SELECT ProductID, SUM(Quantity) AS QtyOnOrder
    FROM SupplierPurchase
    WHERE ReceivedDate IS NULL
    GROUP BY ProductID
) onord
    ON onord.ProductID = p.ProductID
WHERE p.QuantityInStock <= p.ReorderPoint
ORDER BY (p.QuantityInStock - p.ReorderPoint), p.ProductName;

-- Manager takeaway: Every row is at or below its reorder point. The
-- manager can place purchase orders with LastSupplier for
-- SuggestedOrderQty, and the EstimatedCost total shows how much budget
-- is needed. QtyOnOrder prevents double-ordering items already on the way.


-- ---------------------------------------------------------------------
-- REPORT 3: Repeat Customer Value
-- Question: Who are our repeat customers, how much do they spend, and
--           who hasn't been back in a while?
-- Uses: JOIN (Customer, Orders), COUNT, SUM, AVG, MIN, MAX,
--       GROUP BY + HAVING
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_RepeatCustomers AS
SELECT
    cu.CustID,
    CONCAT(cu.FirstName, ' ', cu.LastName)        AS CustomerName,
    cu.Email,
    COUNT(o.OrderID)                              AS TotalOrders,
    SUM(o.OrderAmount)                            AS TotalSpent,
    ROUND(AVG(o.OrderAmount), 2)                  AS AvgOrderValue,
    MIN(o.OrderDate)                              AS FirstOrder,
    MAX(o.OrderDate)                              AS LastOrder,
    DATEDIFF(CURDATE(), MAX(o.OrderDate))         AS DaysSinceLastOrder
FROM Customer cu
JOIN Orders o
    ON o.CustID = cu.CustID
GROUP BY cu.CustID, cu.FirstName, cu.LastName, cu.Email
HAVING COUNT(o.OrderID) >= 2
ORDER BY TotalSpent DESC;

-- Manager takeaway: These customers come back and spend the most; they
-- are candidates for a loyalty discount or early access to new arrivals.
-- A repeat customer with a high DaysSinceLastOrder is at risk of being
-- lost and could be sent a "we miss you" coupon.

-- Parameterized version for the app (e.g. manager picks min order count)
DROP PROCEDURE IF EXISTS sp_RepeatCustomers;
DELIMITER //
CREATE PROCEDURE sp_RepeatCustomers(IN pMinOrders INT)
BEGIN
    SELECT cu.CustID,
           CONCAT(cu.FirstName, ' ', cu.LastName) AS CustomerName,
           cu.Email,
           COUNT(o.OrderID)                       AS TotalOrders,
           SUM(o.OrderAmount)                     AS TotalSpent,
           ROUND(AVG(o.OrderAmount), 2)           AS AvgOrderValue,
           MIN(o.OrderDate)                       AS FirstOrder,
           MAX(o.OrderDate)                       AS LastOrder,
           DATEDIFF(CURDATE(), MAX(o.OrderDate))  AS DaysSinceLastOrder
    FROM Customer cu
    JOIN Orders o ON o.CustID = cu.CustID
    GROUP BY cu.CustID, cu.FirstName, cu.LastName, cu.Email
    HAVING COUNT(o.OrderID) >= pMinOrders
    ORDER BY TotalSpent DESC;
END //
DELIMITER ;


-- ---------------------------------------------------------------------
-- REPORT 4: Tailor Workload & Alteration Revenue
-- Question: How is alteration work spread across tailors, how fast is
--           it completed, and how much revenue does each bring in?
-- Uses: JOIN (Employee, AlterationOrder, Alteration), COUNT, SUM, AVG,
--       GROUP BY + HAVING
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_TailorWorkload AS
SELECT
    e.EmpID,
    CONCAT(e.FirstName, ' ', e.LastName)                         AS Tailor,
    COUNT(ao.AlterationOrderID)                                  AS TotalJobs,
    SUM(CASE WHEN ao.Status = 'Completed' THEN 1 ELSE 0 END)     AS CompletedJobs,
    SUM(CASE WHEN ao.Status <> 'Completed' THEN 1 ELSE 0 END)    AS OpenJobs,
    COALESCE(SUM(ao.ServiceFee), 0)                              AS FeeRevenue,
    COALESCE(SUM(a.AlterationPrice - ao.ServiceFee), 0)          AS DiscountsGiven,
    ROUND(AVG(CASE WHEN ao.Status = 'Completed'
                   THEN DATEDIFF(ao.PickupDate, ao.RequestDate) END), 1)
                                                                 AS AvgDaysToComplete
FROM Employee e
JOIN AlterationOrder ao
    ON ao.EmpID = e.EmpID
JOIN Alteration a
    ON a.AlterationID = ao.AlterationID
WHERE e.Role = 'Tailor'
GROUP BY e.EmpID, e.FirstName, e.LastName
HAVING COUNT(ao.AlterationOrderID) > 0
ORDER BY OpenJobs DESC, FeeRevenue DESC;

-- Manager takeaway: A tailor with many OpenJobs is overloaded; new
-- requests (including unassigned 'Received' jobs) should go to the tailor
-- with the fewest. A high AvgDaysToComplete may call for training or
-- extra staff, and DiscountsGiven shows how much revenue is lost to
-- price reductions below the listed AlterationPrice.


-- ---------------------------------------------------------------------
-- REPORT 5: Monthly Revenue Summary (Products vs. Alterations)
-- Question: How is revenue trending month to month, and how much comes
--           from alterations vs. merchandise?
-- Product sales come from Orders/OrderItem (by OrderDate). Alteration
-- revenue comes from AlterationOrder (by RequestDate) because an
-- alteration order is its own transaction, not part of a sales order.
-- Uses: JOIN (Orders, OrderItem, and the two monthly summaries),
--       COUNT, SUM, AVG, GROUP BY, UNION
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_MonthlyRevenue AS
SELECT
    m.SalesMonth,
    COALESCE(p.OrderCount, 0)                              AS OrderCount,
    COALESCE(alt.AlterationCount, 0)                       AS AlterationCount,
    COALESCE(p.ProductRevenue, 0)                          AS ProductRevenue,
    COALESCE(alt.AlterationRevenue, 0)                     AS AlterationRevenue,
    COALESCE(p.ProductRevenue, 0)
        + COALESCE(alt.AlterationRevenue, 0)               AS TotalRevenue,
    p.AvgOrderValue,
    ROUND(100 * COALESCE(alt.AlterationRevenue, 0)
              / NULLIF(COALESCE(p.ProductRevenue, 0)
                       + COALESCE(alt.AlterationRevenue, 0), 0), 1)
                                                           AS AlterationPct
FROM (                                       -- every month with any activity
    SELECT DATE_FORMAT(OrderDate, '%Y-%m')   AS SalesMonth FROM Orders
    UNION
    SELECT DATE_FORMAT(RequestDate, '%Y-%m') AS SalesMonth FROM AlterationOrder
) m
LEFT JOIN (                                  -- merchandise sales per month
    SELECT DATE_FORMAT(o.OrderDate, '%Y-%m')          AS SalesMonth,
           COUNT(DISTINCT o.OrderID)                  AS OrderCount,
           SUM(oi.Quantity * oi.UnitPrice)            AS ProductRevenue,
           ROUND(SUM(oi.Quantity * oi.UnitPrice)
                 / COUNT(DISTINCT o.OrderID), 2)      AS AvgOrderValue
    FROM Orders o
    JOIN OrderItem oi
        ON oi.OrderID = o.OrderID
    GROUP BY DATE_FORMAT(o.OrderDate, '%Y-%m')
) p
    ON p.SalesMonth = m.SalesMonth
LEFT JOIN (                                  -- alteration orders per month
    SELECT DATE_FORMAT(RequestDate, '%Y-%m')          AS SalesMonth,
           COUNT(*)                                   AS AlterationCount,
           SUM(ServiceFee)                            AS AlterationRevenue
    FROM AlterationOrder
    GROUP BY DATE_FORMAT(RequestDate, '%Y-%m')
) alt
    ON alt.SalesMonth = m.SalesMonth
ORDER BY m.SalesMonth;

-- Manager takeaway: Shows which months are strong or weak so staffing
-- and inventory buys can be planned around busy periods. AlterationPct
-- shows how much the alteration service contributes; a rising share
-- could justify hiring another tailor or promoting the service.

-- Parameterized version for the app (date-range picker on a dashboard)
DROP PROCEDURE IF EXISTS sp_MonthlyRevenue;
DELIMITER //
CREATE PROCEDURE sp_MonthlyRevenue(IN pStart DATE, IN pEnd DATE)
BEGIN
    SELECT * FROM vw_MonthlyRevenue
    WHERE SalesMonth BETWEEN DATE_FORMAT(pStart, '%Y-%m')
                         AND DATE_FORMAT(pEnd,   '%Y-%m');
END //
DELIMITER ;


-- ---------------------------------------------------------------------
-- REPORT 6: Alteration Service Demand
-- Question: Which alteration services are requested most often, how much
--           do they earn, and how long do they take?
-- Uses: JOIN (Alteration, AlterationOrder), COUNT, SUM, AVG, GROUP BY
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_AlterationServiceDemand AS
SELECT
    a.AlterationID,
    a.AlterationName,
    a.AlterationPrice                                            AS ListPrice,
    COUNT(ao.AlterationOrderID)                                  AS TimesRequested,
    SUM(CASE WHEN ao.Status = 'Completed' THEN 1 ELSE 0 END)     AS CompletedJobs,
    COALESCE(SUM(ao.ServiceFee), 0)                              AS FeeRevenue,
    ROUND(AVG(ao.ServiceFee), 2)                                 AS AvgFeeCharged,
    ROUND(AVG(CASE WHEN ao.Status = 'Completed'
                   THEN DATEDIFF(ao.PickupDate, ao.RequestDate) END), 1)
                                                                 AS AvgDaysToComplete
FROM Alteration a
LEFT JOIN AlterationOrder ao                 -- LEFT keeps services nobody ordered
    ON ao.AlterationID = a.AlterationID
GROUP BY a.AlterationID, a.AlterationName, a.AlterationPrice
ORDER BY TimesRequested DESC, FeeRevenue DESC;

-- Manager takeaway: The most-requested services decide what tailors
-- should be trained on and which services to advertise. A popular service
-- with a high AvgDaysToComplete is a bottleneck. A service with
-- TimesRequested = 0 could be promoted or dropped from the menu.


-- ---------------------------------------------------------------------
-- Quick test: run each report
-- ---------------------------------------------------------------------
-- SELECT * FROM vw_ProductSalesPerformance;
-- SELECT * FROM vw_LowStockReorder;
-- SELECT * FROM vw_RepeatCustomers;
-- CALL sp_RepeatCustomers(3);
-- SELECT * FROM vw_TailorWorkload;
-- SELECT * FROM vw_MonthlyRevenue;
-- CALL sp_MonthlyRevenue('2026-01-01', '2026-06-30');
-- SELECT * FROM vw_AlterationServiceDemand;
